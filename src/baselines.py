"""Persistence and training-only historical PM2.5 baselines."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from .data_loading import load_air_quality_csv
from .data_validation import audit_dataset
from .forecasting_data import build_forecasting_samples, split_boundaries

EVALUATION_SPLITS: Final[tuple[str, ...]] = ("validation", "test")


@dataclass(frozen=True)
class HistoricalTimeBaseline:
    """Training-only station/hour/day-of-week averages with safe fallback."""

    group_means: pd.Series
    station_means: pd.Series
    global_mean: float

    @classmethod
    def fit(cls, clean: pd.DataFrame) -> "HistoricalTimeBaseline":
        train = clean.loc[
            clean["temporal_split"].eq("train") & clean["PM2.5"].notna(),
            ["Station_No", "date", "PM2.5"],
        ].copy()
        if train.empty:
            raise ValueError("Historical baseline has no training observations.")
        train["hour"] = train["date"].dt.hour
        train["day_of_week"] = train["date"].dt.dayofweek
        return cls(
            group_means=train.groupby(
                ["Station_No", "hour", "day_of_week"], sort=True
            )["PM2.5"].mean(),
            station_means=train.groupby("Station_No", sort=True)["PM2.5"].mean(),
            global_mean=float(train["PM2.5"].mean()),
        )

    def predict(self, samples: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        target_hour = samples["target_time"].dt.hour
        target_day = samples["target_time"].dt.dayofweek
        keys = pd.MultiIndex.from_arrays(
            [
                samples["Station_No"].to_numpy(),
                target_hour.to_numpy(),
                target_day.to_numpy(),
            ],
            names=["Station_No", "hour", "day_of_week"],
        )
        predictions = pd.Series(
            self.group_means.reindex(keys).to_numpy(),
            index=samples.index,
            dtype=float,
        )
        fallback = predictions.isna()
        if fallback.any():
            station_fallback = samples.loc[fallback, "Station_No"].map(
                self.station_means
            )
            predictions.loc[fallback] = station_fallback.fillna(self.global_mean)
        return predictions, fallback


def regression_metrics(
    actual: pd.Series, predicted: pd.Series
) -> dict[str, float | int]:
    """Calculate deterministic regression metrics without dropping values."""
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted lengths differ.")
    if actual.isna().any() or predicted.isna().any():
        raise ValueError("Metrics require complete actual and predicted values.")
    errors = predicted.to_numpy(dtype=float) - actual.to_numpy(dtype=float)
    actual_values = actual.to_numpy(dtype=float)
    denominator = float(np.sum((actual_values - actual_values.mean()) ** 2))
    r_squared = (
        float(1 - np.sum(errors**2) / denominator)
        if denominator > 0
        else float("nan")
    )
    return {
        "n": len(actual),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "r2": r_squared,
    }


def _metric_rows(
    predictions: pd.DataFrame,
    model: str,
    prediction_column: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for split in EVALUATION_SPLITS:
        split_rows = predictions.loc[predictions["split"].eq(split)]
        aggregations: list[tuple[object, object, pd.DataFrame]] = [
            ("ALL", "ALL", split_rows)
        ]
        aggregations.extend(
            ("ALL", horizon, group)
            for horizon, group in split_rows.groupby("horizon_hours", sort=True)
        )
        aggregations.extend(
            (station, "ALL", group)
            for station, group in split_rows.groupby("Station_No", sort=True)
        )
        aggregations.extend(
            (station, horizon, group)
            for (station, horizon), group in split_rows.groupby(
                ["Station_No", "horizon_hours"], sort=True
            )
        )
        for station, horizon, group in aggregations:
            if group.empty:
                continue
            rows.append(
                {
                    "model": model,
                    "split": split,
                    "Station_No": station,
                    "horizon_hours": horizon,
                    **regression_metrics(
                        group["target_pm25"], group[prediction_column]
                    ),
                }
            )
    return rows


def evaluate_baselines(
    samples: pd.DataFrame,
    clean: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Predict and evaluate both baselines on validation and test samples."""
    predictions = samples.copy()
    predictions["persistence_prediction"] = predictions["pm25_current"]

    historical = HistoricalTimeBaseline.fit(clean)
    (
        predictions["historical_time_prediction"],
        predictions["historical_fallback_used"],
    ) = historical.predict(predictions)

    rows = _metric_rows(
        predictions, "persistence", "persistence_prediction"
    )
    rows.extend(
        _metric_rows(
            predictions, "historical_time", "historical_time_prediction"
        )
    )
    metrics = pd.DataFrame(rows)
    return predictions, metrics


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No observations._"
    return frame.to_markdown(index=False, floatfmt=".4f")


def render_baseline_report(
    samples: pd.DataFrame,
    counts: pd.DataFrame,
    boundaries: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
) -> str:
    """Render the reproducible Milestone 2A protocol and observed results."""
    count_view = counts[
        [
            "Station_No",
            "horizon_hours",
            "complete_lag_origins",
            "exact_nonmissing_targets",
            "cross_partition_candidates",
            "valid_samples",
        ]
    ]
    aggregate_metrics = metrics.loc[
        metrics["Station_No"].eq("ALL")
        & (
            metrics["horizon_hours"].eq("ALL")
            | metrics["horizon_hours"].isin((1, 2, 3))
        )
    ]
    station_horizon_test = metrics.loc[
        metrics["split"].eq("test")
        & ~metrics["Station_No"].eq("ALL")
        & ~metrics["horizon_hours"].eq("ALL")
    ]
    station_test = metrics.loc[
        metrics["split"].eq("test")
        & ~metrics["Station_No"].eq("ALL")
        & metrics["horizon_hours"].eq("ALL")
    ]
    target_quality = (
        predictions.groupby(["split", "horizon_hours"], sort=True)
        .agg(
            samples=("target_pm25", "size"),
            zero_targets=("target_pm25", lambda values: int(values.eq(0).sum())),
            global_iqr_target_flags=(
                "target_pm25_iqr_flag",
                lambda values: int(values.sum()),
            ),
            station_iqr_target_flags=(
                "target_pm25_station_iqr_flag",
                lambda values: int(values.sum()),
            ),
        )
        .reset_index()
    )
    fallback_count = int(predictions["historical_fallback_used"].sum())

    return f"""# AIRPATH-AI forecasting baseline evaluation

## Scope and leakage controls

Milestone 2A constructs station-level targets at exact t+1h, t+2h, and t+3h
timestamps. It uses only current/past PM2.5 and deterministic calendar features.
No interpolation, secondary pollutants, temperature, humidity, spatial features,
random splitting, or learned forecasting model is used.

- `pm25_current` is PM2.5 observed at prediction origin t.
- `pm25_lag_1h`, `pm25_lag_2h`, and `pm25_lag_3h` are exact timestamp lookups.
- `hour`, `day_of_week`, and `month` describe the prediction origin.
- A sample requires complete exact t through t-3h history.
- A target requires a non-missing observation at the exact future timestamp.
- Origin and target must lie in the same chronological partition.
- Zero and IQR-flagged observations are retained.

## Chronological boundaries

{_markdown_table(boundaries)}

Split boundaries are inherited from Milestone 1. Cross-boundary target candidates
are excluded so training labels cannot enter validation and validation labels
cannot enter test.

## Valid sample construction

{_markdown_table(count_view)}

`valid_samples` is the common comparison set used by both baselines and any later
model: exact target, complete exact lag history, and no split-boundary crossing.

## Baselines

**Persistence:** predicts PM2.5(t) for every horizon.

**Historical time baseline:** predicts the training-only station-specific mean
for the target timestamp's hour-of-day and day-of-week. An unseen combination
falls back to that station's training mean, then the global training mean.
Fallback predictions used across all partitions/horizons: **{fallback_count}**.

## Overall and per-horizon metrics

{_markdown_table(aggregate_metrics)}

Metrics marked `split=validation` support model development; `split=test` is the
held-out baseline result. Aggregation pools prediction rows, so stations with
more valid samples contribute more observations.

## Test metrics by station

{_markdown_table(station_test)}

## Test metrics by station and horizon

{_markdown_table(station_horizon_test)}

R² can be negative when a baseline is worse than predicting the evaluation-set
mean. It is undefined if the observed target is constant.

## Retained target-quality flags

{_markdown_table(target_quality)}

No zero or IQR-flagged source observation was removed. Origin and target flags
remain in the saved sample data for later sensitivity analysis; they are
metadata, not model features. Because the Milestone 1 IQR flags were descriptive
full-dataset audit flags, any future model-based filtering threshold must instead
be estimated from training data only.

## Methodological limitations

- Baselines use no meteorological or secondary-pollutant predictors.
- Missing timestamps reduce samples non-uniformly by station and horizon.
- Historical means are descriptive seasonal averages and do not establish
  causal relationships.
- Hyperparameter tuning and model selection are outside this milestone.
- Test metrics should not guide repeated model-development decisions.
"""


def write_baseline_outputs(
    root: Path,
    samples: pd.DataFrame,
    counts: pd.DataFrame,
    boundaries: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
) -> None:
    processed = root / "data" / "processed"
    reports = root / "reports"
    tables = reports / "tables"
    for directory in (processed, reports, tables):
        directory.mkdir(parents=True, exist_ok=True)

    samples.to_csv(processed / "forecasting_samples.csv", index=False)
    predictions.to_csv(
        processed / "forecasting_baseline_predictions.csv", index=False
    )
    counts.to_csv(tables / "forecasting_sample_counts.csv", index=False)
    metrics.to_csv(tables / "forecasting_baseline_metrics.csv", index=False)
    (reports / "forecasting_baseline.md").write_text(
        render_baseline_report(
            samples, counts, boundaries, predictions, metrics
        ),
        encoding="utf-8",
    )


def run_baseline_experiment(
    input_path: Path,
    root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = load_air_quality_csv(input_path)
    clean, _ = audit_dataset(raw)
    samples, counts = build_forecasting_samples(clean)
    boundaries = split_boundaries(clean)
    predictions, metrics = evaluate_baselines(samples, clean)
    write_baseline_outputs(
        root, samples, counts, boundaries, predictions, metrics
    )
    return samples, counts, predictions, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/Air Quality Ho Chi Minh City.csv"),
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    run_baseline_experiment(args.input, args.root)


if __name__ == "__main__":
    main()
