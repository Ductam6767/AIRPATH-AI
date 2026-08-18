"""Leakage-safe station-level forecasting sample construction."""

from __future__ import annotations

from typing import Final

import pandas as pd

from .preprocessing import chronological_split_labels

HORIZONS: Final[tuple[int, ...]] = (1, 2, 3)
LAGS: Final[tuple[int, ...]] = (1, 2, 3)
REQUIRED_COLUMNS: Final[set[str]] = {"date", "Station_No", "PM2.5"}


def _exact_lookup(
    lookup: pd.Series,
    stations: pd.Series,
    timestamps: pd.Series,
) -> pd.Series:
    keys = pd.MultiIndex.from_arrays(
        [stations.to_numpy(), timestamps.to_numpy()],
        names=["Station_No", "date"],
    )
    return pd.Series(lookup.reindex(keys).to_numpy(), index=stations.index)


def _prepare_clean_data(clean: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(clean.columns)
    if missing:
        raise ValueError(
            "Forecast construction requires columns: " + ", ".join(sorted(missing))
        )

    prepared = clean.copy()
    if not pd.api.types.is_datetime64_any_dtype(prepared["date"]):
        raise TypeError("The date column must be parsed before forecast construction.")
    if prepared.duplicated(["Station_No", "date"]).any():
        raise ValueError(
            "Duplicate station-timestamp pairs must be resolved or documented "
            "before forecast construction."
        )
    if "temporal_split" not in prepared:
        prepared["temporal_split"] = chronological_split_labels(prepared["date"])
    return prepared.sort_values(["Station_No", "date"]).reset_index(drop=True)


def split_boundaries(clean: pd.DataFrame) -> pd.DataFrame:
    """Return exact chronological boundaries already assigned by Milestone 1."""
    prepared = _prepare_clean_data(clean)
    rows = []
    for split in ("train", "validation", "test"):
        timestamps = prepared.loc[
            prepared["temporal_split"].eq(split), "date"
        ].dropna()
        rows.append(
            {
                "split": split,
                "start": timestamps.min(),
                "end": timestamps.max(),
                "unique_timestamps": int(timestamps.nunique()),
            }
        )
    return pd.DataFrame(rows)


def build_forecasting_samples(
    clean: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build samples using exact timestamp joins, never positional gap crossing.

    The returned experiment dataset contains only rows for which:
    - PM2.5 exists at the origin and exact t-1h, t-2h, and t-3h timestamps;
    - a non-missing PM2.5 target exists at the exact requested future timestamp;
    - origin and target belong to the same chronological partition.

    Excluding cross-boundary rows ensures training labels do not reach into the
    validation period and validation labels do not reach into the test period.
    """
    prepared = _prepare_clean_data(clean)
    indexed = prepared.set_index(["Station_No", "date"])
    pm25_lookup = indexed["PM2.5"]
    split_lookup = indexed["temporal_split"]

    base_columns = ["Station_No", "date", "PM2.5"]
    for flag in (
        "pm25_iqr_flag",
        "pm25_station_iqr_flag",
        "pm25_negative_flag",
        "pm25_zero_flag",
    ):
        if flag in prepared:
            base_columns.append(flag)

    base = prepared[base_columns].rename(
        columns={"date": "origin_time", "PM2.5": "pm25_current"}
    )
    base["origin_split"] = prepared["temporal_split"].astype("string")
    base["hour"] = base["origin_time"].dt.hour
    base["day_of_week"] = base["origin_time"].dt.dayofweek
    base["month"] = base["origin_time"].dt.month

    for lag in LAGS:
        lag_time = base["origin_time"] - pd.Timedelta(hours=lag)
        base[f"pm25_lag_{lag}h"] = _exact_lookup(
            pm25_lookup, base["Station_No"], lag_time
        )

    lag_columns = [f"pm25_lag_{lag}h" for lag in LAGS]
    base["complete_lag_history"] = base[
        ["pm25_current", *lag_columns]
    ].notna().all(axis=1)

    samples: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    for horizon in HORIZONS:
        candidate = base.copy()
        candidate["horizon_hours"] = horizon
        candidate["target_time"] = candidate["origin_time"] + pd.Timedelta(
            hours=horizon
        )
        candidate["target_pm25"] = _exact_lookup(
            pm25_lookup, candidate["Station_No"], candidate["target_time"]
        )
        candidate["target_split"] = _exact_lookup(
            split_lookup, candidate["Station_No"], candidate["target_time"]
        ).astype("string")
        candidate["same_partition"] = (
            candidate["origin_split"].notna()
            & candidate["origin_split"].eq(candidate["target_split"])
        )
        candidate["valid_sample"] = (
            candidate["complete_lag_history"]
            & candidate["target_pm25"].notna()
            & candidate["same_partition"]
        )

        for station, station_rows in candidate.groupby("Station_No", sort=True):
            summaries.append(
                {
                    "Station_No": station,
                    "horizon_hours": horizon,
                    "origin_observations": len(station_rows),
                    "complete_lag_origins": int(
                        station_rows["complete_lag_history"].sum()
                    ),
                    "exact_nonmissing_targets": int(
                        station_rows["target_pm25"].notna().sum()
                    ),
                    "cross_partition_candidates": int(
                        (
                            station_rows["target_pm25"].notna()
                            & ~station_rows["same_partition"]
                        ).sum()
                    ),
                    "valid_samples": int(station_rows["valid_sample"].sum()),
                }
            )
        samples.append(candidate.loc[candidate["valid_sample"]].copy())

    result = pd.concat(samples, ignore_index=True)
    result["split"] = result["origin_split"]
    result = result.drop(
        columns=[
            "origin_split",
            "target_split",
            "complete_lag_history",
            "same_partition",
            "valid_sample",
        ]
    ).sort_values(["horizon_hours", "Station_No", "origin_time"])
    return result.reset_index(drop=True), pd.DataFrame(summaries)
