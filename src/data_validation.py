"""Dataset validation and research audit orchestration."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from .data_loading import EXPECTED_COLUMNS, column_schema, load_air_quality_csv
from .preprocessing import chronological_split_labels, parse_and_flag
from .visualization import create_audit_figures


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.where(pd.notna(df), None).to_dict(orient="records")


def pm25_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Return global and per-station PM2.5 statistics."""
    required = {"Station_No", "PM2.5"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    def summarize(values: pd.Series) -> pd.Series:
        numeric = values.dropna()
        return pd.Series(
            {
                "observations": len(values),
                "non_missing": numeric.size,
                "missing": values.isna().sum(),
                "negative": numeric.lt(0).sum(),
                "zero": numeric.eq(0).sum(),
                "min": numeric.min(),
                "q1": numeric.quantile(0.25),
                "median": numeric.median(),
                "q3": numeric.quantile(0.75),
                "max": numeric.max(),
                "mean": numeric.mean(),
                "std": numeric.std(),
                "global_iqr_flags": df.loc[values.index, "pm25_iqr_flag"].sum(),
                "station_iqr_flags": df.loc[
                    values.index, "pm25_station_iqr_flag"
                ].sum(),
            }
        )

    rows = [summarize(df["PM2.5"]).rename("GLOBAL")]
    rows.extend(
        summarize(group["PM2.5"]).rename(str(station))
        for station, group in df.groupby("Station_No", dropna=False, sort=True)
    )
    result = pd.DataFrame(rows)
    result.index.name = "station"
    return result


def temporal_quality(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize station coverage and all gaps greater than one hour."""
    if not {"Station_No", "date"}.issubset(df.columns):
        return pd.DataFrame(), pd.DataFrame()

    coverage_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    for station, group in df.groupby("Station_No", dropna=False, sort=True):
        valid = (
            group.loc[group["date"].notna()].sort_values("date").reset_index(drop=True)
        )
        differences = valid["date"].diff()
        duplicate_count = int(valid["date"].duplicated(keep=False).sum())
        positive_differences = differences[differences.gt(pd.Timedelta(0))]
        mode = positive_differences.mode()
        coverage_rows.append(
            {
                "Station_No": station,
                "observations": len(group),
                "valid_timestamps": len(valid),
                "start": valid["date"].min(),
                "end": valid["date"].max(),
                "duplicate_timestamp_rows": duplicate_count,
                "modal_positive_interval": mode.iloc[0] if not mode.empty else pd.NaT,
                "largest_gap": positive_differences.max(),
                "gaps_gt_1h": int(differences.gt(pd.Timedelta(hours=1)).sum()),
            }
        )
        for position in differences[differences.gt(pd.Timedelta(hours=1))].index:
            gap_rows.append(
                {
                    "Station_No": station,
                    "gap_start": valid.iloc[position - 1]["date"],
                    "gap_end": valid.loc[position, "date"],
                    "gap": differences.loc[position],
                    "gap_hours": differences.loc[position].total_seconds() / 3600,
                }
            )

    gaps = pd.DataFrame(gap_rows)
    if not gaps.empty:
        gaps = gaps.sort_values("gap", ascending=False)
    return pd.DataFrame(coverage_rows), gaps


def missingness_tables(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return variable-level and station-by-variable missingness."""
    variable = pd.DataFrame(
        {
            "missing_count": df.isna().sum(),
            "missing_percent": df.isna().mean().mul(100),
        }
    )
    if "Station_No" not in df:
        return variable, pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for station_name, group in df.groupby("Station_No", dropna=False):
        row: dict[str, Any] = {"Station_No": station_name}
        for column in df.columns:
            row[f"{column}_missing_count"] = int(group[column].isna().sum())
            row[f"{column}_missing_percent"] = float(
                group[column].isna().mean() * 100
            )
        rows.append(row)
    station = pd.DataFrame(rows)
    return variable, station


def pairwise_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pairwise-complete Pearson correlations with sample sizes."""
    candidates = [
        "TSP", "O3", "CO", "NO2", "SO2", "Temperature", "Humidity"
    ]
    rows = []
    if "PM2.5" not in df:
        return pd.DataFrame()
    for variable in candidates:
        if variable not in df:
            continue
        pairs = df[["PM2.5", variable]].dropna()
        rows.append(
            {
                "variable": variable,
                "paired_observations": len(pairs),
                "pearson_correlation": (
                    pairs["PM2.5"].corr(pairs[variable])
                    if (
                        len(pairs) >= 2
                        and pairs["PM2.5"].nunique() > 1
                        and pairs[variable].nunique() > 1
                    )
                    else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows)


def audit_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Parse, flag, and audit a loaded source dataframe."""
    schema = column_schema(df)
    clean, parse_issues = parse_and_flag(df)
    coverage, gaps = temporal_quality(clean)
    source_columns = [column for column in schema["observed"] if column in clean]
    variable_missing, station_missing = missingness_tables(clean[source_columns])
    stats = pm25_statistics(clean)
    correlations = pairwise_correlations(clean)

    duplicate_key_rows = (
        int(clean.duplicated(["Station_No", "date"], keep=False).sum())
        if {"Station_No", "date"}.issubset(clean.columns)
        else None
    )
    duplicate_key_additional = (
        int(clean.duplicated(["Station_No", "date"]).sum())
        if {"Station_No", "date"}.issubset(clean.columns)
        else None
    )
    split = {}
    valid_unique_times = pd.Series(dtype="datetime64[ns]")
    overall_interval = pd.NaT
    overall_gaps_gt_1h = None
    if "date" in clean and clean["date"].notna().any():
        valid_unique_times = pd.Series(clean["date"].dropna().unique()).sort_values()
        unique_differences = valid_unique_times.diff()
        positive_unique_differences = unique_differences[
            unique_differences.gt(pd.Timedelta(0))
        ]
        interval_modes = positive_unique_differences.mode()
        overall_interval = (
            interval_modes.iloc[0] if not interval_modes.empty else pd.NaT
        )
        overall_gaps_gt_1h = int(
            unique_differences.gt(pd.Timedelta(hours=1)).sum()
        )
        labels = chronological_split_labels(clean["date"])
        clean["temporal_split"] = labels
        split = {
            label: {
                "rows": int(labels.eq(label).sum()),
                "unique_timestamps": int(
                    clean.loc[labels.eq(label), "date"].nunique()
                ),
                "start": clean.loc[labels.eq(label), "date"].min(),
                "end": clean.loc[labels.eq(label), "date"].max(),
            }
            for label in ("train", "validation", "test")
        }

    audit = {
        "dimensions": {"rows": len(df), "columns": len(df.columns)},
        "schema": schema,
        "source_dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "parse_issues": [asdict(issue) for issue in parse_issues],
        "complete_duplicate_additional_rows": int(df.duplicated().sum()),
        "complete_duplicate_group_rows": int(df.duplicated(keep=False).sum()),
        "duplicate_station_timestamp_additional_rows": duplicate_key_additional,
        "duplicate_station_timestamp_group_rows": duplicate_key_rows,
        "invalid_timestamps": next(
            (issue.count for issue in parse_issues if issue.column == "date"), 0
        ),
        "timestamp_min": clean["date"].min() if "date" in clean else None,
        "timestamp_max": clean["date"].max() if "date" in clean else None,
        "unique_timestamps": int(len(valid_unique_times)),
        "modal_positive_timestamp_interval": overall_interval,
        "overall_gaps_gt_1h": overall_gaps_gt_1h,
        "coverage": _records(coverage),
        "gaps": _records(gaps),
        "missingness_by_variable": _records(variable_missing.reset_index(names="variable")),
        "missingness_by_station": _records(station_missing),
        "pm25_statistics": _records(stats.reset_index()),
        "correlations": _records(correlations),
        "pm25_flags": _records(
            clean.loc[
                clean[
                    [
                        "pm25_iqr_flag",
                        "pm25_station_iqr_flag",
                        "pm25_negative_flag",
                        "pm25_zero_flag",
                    ]
                ].any(axis=1),
                [
                    "date",
                    "Station_No",
                    "PM2.5",
                    "pm25_iqr_flag",
                    "pm25_station_iqr_flag",
                    "pm25_negative_flag",
                    "pm25_zero_flag",
                ],
            ]
        ),
        "split": split,
    }
    return clean, audit


def _markdown_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return "_Not available._"
    return pd.DataFrame(records).to_markdown(index=False)


def render_report(audit: dict[str, Any]) -> str:
    """Render the required concise scientific audit report."""
    schema = audit["schema"]
    unexpected = ", ".join(schema["unexpected"]) or "None"
    missing_expected = ", ".join(schema["missing_expected"]) or "None"
    issues = _markdown_table(audit["parse_issues"])
    gap_records = audit["gaps"][:20]
    split_rows = [
        {"partition": name, **values} for name, values in audit["split"].items()
    ]
    return f"""# AIRPATH-AI data audit

## 1. Dataset dimensions

- Rows: {audit["dimensions"]["rows"]}
- Columns: {audit["dimensions"]["columns"]}
- Observed columns: {", ".join(schema["observed"])}
- Missing expected columns: {missing_expected}
- Unexpected columns: {unexpected}
- Source data types: {audit["source_dtypes"]}
- Additional complete duplicate rows beyond the first copy: {audit["complete_duplicate_additional_rows"]}
- Rows belonging to complete-duplicate groups (all copies counted): {audit["complete_duplicate_group_rows"]}
- Additional duplicate `(Station_No, date)` rows beyond the first: {audit["duplicate_station_timestamp_additional_rows"]}
- Rows in duplicate `(Station_No, date)` groups (all copies counted): {audit["duplicate_station_timestamp_group_rows"]}
- Invalid timestamp values: {audit["invalid_timestamps"]}

Parse failures were converted to missing values only after being counted:

{issues}

## 2. Temporal coverage

- Earliest timestamp: {audit["timestamp_min"]}
- Latest timestamp: {audit["timestamp_max"]}
- Unique observed timestamps: {audit["unique_timestamps"]}
- Modal positive interval between unique timestamps: {audit["modal_positive_timestamp_interval"]}
- Overall gaps greater than one hour in the union of station timestamps: {audit["overall_gaps_gt_1h"]}

## 3. Station coverage

{_markdown_table(audit["coverage"])}

## 4. Missingness

Variable-level missingness:

{_markdown_table(audit["missingness_by_variable"])}

Station-by-variable missingness is saved in `reports/tables/missingness_by_station.csv`.
Rows are retained when secondary pollutants are missing.

{_markdown_table(audit["missingness_by_station"])}

## 5. PM2.5 statistics

{_markdown_table(audit["pm25_statistics"])}

Standard deviation uses the sample definition (`ddof=1`). Quartiles use pandas'
default linear quantile method. Values are reported as observed, including zero,
negative, and extreme values.

Pairwise-complete Pearson correlations (descriptive only):

{_markdown_table(audit["correlations"])}

## 6. Temporal gaps

The 20 largest gaps greater than one hour are shown below. The complete table is
saved in `reports/tables/temporal_gaps.csv`. Gaps are documented, not filled.

{_markdown_table(gap_records)}

## 7. Outlier flags

`pm25_iqr_flag` applies the Q1 - 1.5 IQR / Q3 + 1.5 IQR rule globally;
`pm25_station_iqr_flag` applies it within each station. `pm25_negative_flag` and
`pm25_zero_flag` are separate. These are screening flags, not proof of
measurement error; no flagged observation was removed. Flagged rows are saved
in `reports/tables/pm25_flagged_observations.csv`.

## 8. Recommended train/validation/test split

{_markdown_table(split_rows)}

The boundaries approximate 70%/15%/15% of unique observed timestamps while
keeping equal timestamps in one partition. They should be reviewed against
station coverage before modeling. All preprocessing parameters must be fit on
training data only; random time-series splitting is inappropriate.

## 9. Recommended forecast horizons

Initial targets: **t+1 hour, t+2 hours, and t+3 hours**. The source observations
are hourly; no finer-resolution ground truth is created.

## 10. Known limitations

- Station observations do not directly measure road-level PM2.5.
- No station coordinates are inferred or invented.
- IQR flags identify unusual values but do not establish that values are invalid.
- Pairwise correlations use available pairs and differing sample sizes; they do
  not imply causality.
- Large temporal gaps remain unfilled.
- Before feature engineering, lag features must contain only information
  available at prediction time. Future PM2.5 must never enter predictors, and
  validation/test data must not influence fitted preprocessing parameters.
"""


def write_outputs(
    clean: pd.DataFrame, audit: dict[str, Any], root: Path
) -> None:
    """Write processed data, tables, report, and research figures."""
    processed = root / "data" / "processed"
    reports = root / "reports"
    tables = reports / "tables"
    figures = reports / "figures"
    for directory in (processed, reports, tables, figures):
        directory.mkdir(parents=True, exist_ok=True)

    clean.to_csv(processed / "airquality_hcmc_clean.csv", index=False)
    pd.DataFrame(audit["missingness_by_station"]).to_csv(
        tables / "missingness_by_station.csv", index=False
    )
    pd.DataFrame(audit["gaps"]).to_csv(
        tables / "temporal_gaps.csv", index=False
    )
    pd.DataFrame(audit["correlations"]).to_csv(
        tables / "pm25_correlations.csv", index=False
    )
    pd.DataFrame(audit["pm25_flags"]).to_csv(
        tables / "pm25_flagged_observations.csv", index=False
    )
    (reports / "data_audit.md").write_text(
        render_report(audit), encoding="utf-8"
    )
    create_audit_figures(clean, figures)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/Air Quality Ho Chi Minh City.csv"),
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    source = load_air_quality_csv(args.input)
    missing = [column for column in EXPECTED_COLUMNS if column not in source]
    if missing:
        raise ValueError(
            "Required columns absent from the actual CSV: " + ", ".join(missing)
        )
    clean, audit = audit_dataset(source)
    write_outputs(clean, audit, args.root)


if __name__ == "__main__":
    main()
