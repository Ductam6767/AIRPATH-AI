"""Safe loading utilities for the HealthyAir HCMC data."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

EXPECTED_COLUMNS: Final[tuple[str, ...]] = (
    "date",
    "Station_No",
    "TSP",
    "PM2.5",
    "O3",
    "CO",
    "NO2",
    "SO2",
    "Temperature",
    "Humidity",
)


def load_air_quality_csv(path: str | Path) -> pd.DataFrame:
    """Load the source CSV without silently parsing or coercing its values."""
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {csv_path}. Place the original file at this path; "
            "the audit does not download or synthesize observations."
        )

    # Keep source values intact here. Parsing and validation are explicit later.
    return pd.read_csv(csv_path, low_memory=False)


def column_schema(df: pd.DataFrame) -> dict[str, list[str]]:
    """Compare observed columns with the documented expected schema."""
    observed = [str(column) for column in df.columns]
    return {
        "observed": observed,
        "missing_expected": [
            column for column in EXPECTED_COLUMNS if column not in observed
        ],
        "unexpected": [
            column for column in observed if column not in EXPECTED_COLUMNS
        ],
    }
