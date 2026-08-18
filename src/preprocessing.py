"""Conservative preprocessing that preserves questionable observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    "TSP",
    "PM2.5",
    "O3",
    "CO",
    "NO2",
    "SO2",
    "Temperature",
    "Humidity",
)
SOURCE_TIMESTAMP_FORMAT: Final[str] = "%d-%m-%Y %H:%M"


@dataclass(frozen=True)
class ParseIssue:
    """Summary of source values that could not be parsed."""

    column: str
    count: int
    examples: tuple[str, ...]


def _parse_issue(
    original: pd.Series, parsed: pd.Series, column: str
) -> ParseIssue:
    nonempty = original.notna() & original.astype("string").str.strip().ne("")
    invalid = nonempty & parsed.isna()
    examples = tuple(original.loc[invalid].astype(str).drop_duplicates().head(10))
    return ParseIssue(column=column, count=int(invalid.sum()), examples=examples)


def parse_and_flag(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[ParseIssue]]:
    """Parse timestamps/numerics and add flags; never remove source rows.

    Invalid non-empty values become missing only after being counted and sampled
    in the returned issue list.
    """
    clean = df.copy()
    issues: list[ParseIssue] = []

    if "date" in clean:
        parsed_date = pd.to_datetime(
            clean["date"], format=SOURCE_TIMESTAMP_FORMAT, errors="coerce"
        )
        issues.append(_parse_issue(clean["date"], parsed_date, "date"))
        clean["date"] = parsed_date

    for column in NUMERIC_COLUMNS:
        if column not in clean:
            continue
        parsed = pd.to_numeric(clean[column], errors="coerce")
        issues.append(_parse_issue(clean[column], parsed, column))
        clean[column] = parsed

    if "PM2.5" in clean:
        pm25 = clean["PM2.5"]
        q1, q3 = pm25.quantile([0.25, 0.75])
        iqr = q3 - q1
        if pd.notna(iqr):
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            clean["pm25_iqr_flag"] = pm25.notna() & (
                (pm25 < lower) | (pm25 > upper)
            )
        else:
            clean["pm25_iqr_flag"] = False
        clean["pm25_station_iqr_flag"] = False
        if "Station_No" in clean:
            for _, index in clean.groupby("Station_No", dropna=False).groups.items():
                station_pm25 = pm25.loc[index]
                station_q1, station_q3 = station_pm25.quantile([0.25, 0.75])
                station_iqr = station_q3 - station_q1
                if pd.notna(station_iqr):
                    station_lower = station_q1 - 1.5 * station_iqr
                    station_upper = station_q3 + 1.5 * station_iqr
                    clean.loc[index, "pm25_station_iqr_flag"] = (
                        station_pm25.notna()
                        & (
                            (station_pm25 < station_lower)
                            | (station_pm25 > station_upper)
                        )
                    )
        clean["pm25_negative_flag"] = pm25.lt(0).fillna(False)
        clean["pm25_zero_flag"] = pm25.eq(0).fillna(False)

    return clean, [issue for issue in issues if issue.count]


def chronological_split_labels(
    timestamps: pd.Series,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> pd.Series:
    """Label unique timestamps chronologically without splitting equal times."""
    if train_fraction <= 0 or validation_fraction <= 0:
        raise ValueError("Split fractions must be positive.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must sum to less than 1.")

    valid_times = pd.Series(timestamps.dropna().unique()).sort_values()
    labels = pd.Series(pd.NA, index=timestamps.index, dtype="string")
    if valid_times.empty:
        return labels

    train_index = max(0, min(len(valid_times) - 1, int(np.floor(
        len(valid_times) * train_fraction
    )) - 1))
    validation_index = max(train_index + 1, min(
        len(valid_times) - 1,
        int(np.floor(len(valid_times) * (train_fraction + validation_fraction))) - 1,
    ))
    train_end = valid_times.iloc[train_index]
    validation_end = valid_times.iloc[validation_index]

    labels.loc[timestamps.notna() & timestamps.le(train_end)] = "train"
    labels.loc[
        timestamps.notna()
        & timestamps.gt(train_end)
        & timestamps.le(validation_end)
    ] = "validation"
    labels.loc[timestamps.notna() & timestamps.gt(validation_end)] = "test"
    return labels
