from pathlib import Path

import pandas as pd
import pytest

from src.data_loading import load_air_quality_csv
from src.data_validation import audit_dataset
from src.preprocessing import chronological_split_labels


def test_missing_input_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not download or synthesize"):
        load_air_quality_csv(tmp_path / "missing.csv")


def test_audit_reports_parse_failures_and_retains_rows() -> None:
    raw = pd.DataFrame(
        {
            "date": [
                "2024-01-01 00:00:00",
                "invalid",
                "2024-01-01 03:00:00",
                "2024-01-01 03:00:00",
            ],
            "Station_No": ["A", "A", "A", "A"],
            "TSP": [10, 20, None, 40],
            "PM2.5": ["5", "-1", "0", "500"],
            "O3": [1, None, 3, 4],
            "CO": [1, 2, 3, 4],
            "NO2": [1, 2, 3, 4],
            "SO2": [1, 2, 3, 4],
            "Temperature": [25, 26, 27, 28],
            "Humidity": [70, 71, 72, "not-numeric"],
        }
    )

    clean, audit = audit_dataset(raw)

    assert len(clean) == len(raw)
    assert audit["invalid_timestamps"] == 1
    assert any(
        issue["column"] == "Humidity" and issue["count"] == 1
        for issue in audit["parse_issues"]
    )
    global_stats = audit["pm25_statistics"][0]
    assert global_stats["negative"] == 1
    assert global_stats["zero"] == 1
    assert audit["duplicate_station_timestamp_rows"] == 2
    assert audit["coverage"][0]["gaps_gt_1h"] == 1


def test_chronological_split_keeps_equal_timestamps_together() -> None:
    timestamps = pd.Series(
        pd.to_datetime(
            [
                "2024-01-01 00:00",
                "2024-01-01 01:00",
                "2024-01-01 01:00",
                "2024-01-01 02:00",
                "2024-01-01 03:00",
                "2024-01-01 04:00",
                "2024-01-01 05:00",
            ]
        )
    )

    labels = chronological_split_labels(timestamps, 0.5, 0.25)

    assert labels.iloc[1] == labels.iloc[2]
    ordering = {"train": 0, "validation": 1, "test": 2}
    assert labels.map(ordering).is_monotonic_increasing
