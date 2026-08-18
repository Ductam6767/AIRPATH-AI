import pandas as pd
import pytest

from src.baselines import evaluate_baselines, regression_metrics
from src.forecasting_data import build_forecasting_samples


def _continuous_clean() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=15, freq="h")
    split = pd.Series("train", index=range(len(timestamps)), dtype="string")
    split.loc[7:10] = "validation"
    split.loc[11:] = "test"
    return pd.DataFrame(
        {
            "Station_No": 1,
            "date": timestamps,
            "PM2.5": [float(value) for value in range(len(timestamps))],
            "temporal_split": split,
            "pm25_iqr_flag": False,
            "pm25_station_iqr_flag": False,
            "pm25_negative_flag": False,
            "pm25_zero_flag": False,
        }
    )


def test_exact_horizons_lags_and_no_future_leakage() -> None:
    clean = _continuous_clean()
    samples, _ = build_forecasting_samples(clean)
    row = samples.loc[
        samples["origin_time"].eq(pd.Timestamp("2024-01-01 04:00"))
        & samples["horizon_hours"].eq(2)
    ].iloc[0]

    assert row["target_time"] == pd.Timestamp("2024-01-01 06:00")
    assert row["target_pm25"] == 6.0
    assert row["pm25_current"] == 4.0
    assert row["pm25_lag_1h"] == 3.0
    assert row["pm25_lag_2h"] == 2.0
    assert row["pm25_lag_3h"] == 1.0
    assert max(
        row["origin_time"] - pd.Timedelta(hours=lag) for lag in (1, 2, 3)
    ) < row["target_time"]


def test_missing_timestamp_is_not_replaced_by_next_row() -> None:
    clean = _continuous_clean().loc[
        lambda frame: ~frame["date"].eq(pd.Timestamp("2024-01-01 09:00"))
    ].reset_index(drop=True)

    samples, counts = build_forecasting_samples(clean)

    assert not (
        samples["origin_time"].eq(pd.Timestamp("2024-01-01 08:00"))
        & samples["horizon_hours"].eq(1)
    ).any()
    # Exact t+2 remains scientifically valid even though t+1 is absent.
    assert (
        samples["origin_time"].eq(pd.Timestamp("2024-01-01 08:00"))
        & samples["horizon_hours"].eq(2)
    ).any()
    assert counts["valid_samples"].sum() < counts[
        "exact_nonmissing_targets"
    ].sum()


def test_cross_partition_targets_are_excluded() -> None:
    clean = _continuous_clean()
    samples, counts = build_forecasting_samples(clean)

    assert not (
        samples["origin_time"].eq(pd.Timestamp("2024-01-01 06:00"))
        & samples["horizon_hours"].eq(1)
    ).any()
    assert counts["cross_partition_candidates"].sum() > 0
    split_order = {"train": 0, "validation": 1, "test": 2}
    assert samples.sort_values("origin_time")["split"].map(
        split_order
    ).is_monotonic_increasing


def test_historical_baseline_uses_training_values_only() -> None:
    clean = pd.DataFrame(
        {
            "Station_No": [1, 1, 1],
            "date": pd.to_datetime(
                [
                    "2024-01-01 01:00",
                    "2024-01-08 01:00",
                    "2024-01-15 01:00",
                ]
            ),
            "PM2.5": [10.0, 100.0, 1000.0],
            "temporal_split": pd.Series(
                ["train", "validation", "test"], dtype="string"
            ),
        }
    )
    samples = pd.DataFrame(
        {
            "Station_No": [1, 1],
            "origin_time": pd.to_datetime(
                ["2024-01-08 00:00", "2024-01-15 00:00"]
            ),
            "target_time": pd.to_datetime(
                ["2024-01-08 01:00", "2024-01-15 01:00"]
            ),
            "horizon_hours": [1, 1],
            "pm25_current": [90.0, 900.0],
            "target_pm25": [100.0, 1000.0],
            "split": pd.Series(["validation", "test"], dtype="string"),
        }
    )

    predictions, metrics = evaluate_baselines(samples, clean)

    assert predictions["historical_time_prediction"].tolist() == [10.0, 10.0]
    assert not predictions["historical_fallback_used"].any()
    assert set(metrics["split"]) == {"validation", "test"}


def test_construction_is_reproducible_and_metrics_are_correct() -> None:
    clean = _continuous_clean()
    first_samples, first_counts = build_forecasting_samples(clean)
    second_samples, second_counts = build_forecasting_samples(clean)
    pd.testing.assert_frame_equal(first_samples, second_samples)
    pd.testing.assert_frame_equal(first_counts, second_counts)

    metrics = regression_metrics(
        pd.Series([1.0, 2.0, 3.0]), pd.Series([2.0, 2.0, 2.0])
    )
    assert metrics["mae"] == pytest.approx(2 / 3)
    assert metrics["rmse"] == pytest.approx((2 / 3) ** 0.5)
    assert metrics["r2"] == pytest.approx(0.0)
