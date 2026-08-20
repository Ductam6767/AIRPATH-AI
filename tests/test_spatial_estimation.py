import numpy as np
import pandas as pd
import pytest

from src.spatial_estimation import (
    STATION_BY_ID,
    estimate_deployment_pm25,
    estimate_oracle_pm25,
    estimate_pm25,
    estimate_with_diagnostics,
    evaluate_leave_one_station_out,
    haversine_distance_km,
    pairwise_station_distances,
    station_geometry_frame,
    temporal_robustness_metrics,
)


def _synthetic_six_station_data() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01", periods=5, freq="h")
    rows = []
    for time_index, timestamp in enumerate(timestamps):
        split = "train" if time_index < 4 else "test"
        for station_id in range(1, 7):
            rows.append(
                {
                    "date": timestamp,
                    "Station_No": station_id,
                    "PM2.5": float(10 + station_id + time_index),
                    "temporal_split": split,
                }
            )
    return pd.DataFrame(rows)


def test_station_geometry_is_complete_authoritative_shape() -> None:
    geometry = station_geometry_frame()

    assert geometry["station_id"].tolist() == [1, 2, 3, 4, 5, 6]
    assert geometry["station_id"].is_unique
    assert geometry["latitude"].between(10, 11).all()
    assert geometry["longitude"].between(106, 107).all()
    assert geometry["station_type"].str.len().gt(0).all()
    assert geometry["coordinate_source"].str.contains("108774").all()

    distances = pairwise_station_distances()
    assert len(distances) == 15
    assert distances["distance_km"].gt(0).all()


def test_haversine_is_symmetric_and_validates_coordinates() -> None:
    first = STATION_BY_ID[1]
    second = STATION_BY_ID[2]
    forward = haversine_distance_km(
        first.latitude, first.longitude, second.latitude, second.longitude
    )
    backward = haversine_distance_km(
        second.latitude, second.longitude, first.latitude, first.longitude
    )

    assert forward == pytest.approx(backward)
    assert forward == pytest.approx(24.24, abs=0.02)
    with pytest.raises(ValueError, match="Latitude"):
        haversine_distance_km(91, 106.7, 10.8, 106.6)


def test_zero_distance_returns_coincident_station_for_both_methods() -> None:
    station = STATION_BY_ID[4]
    values = {1: 12.0, 4: 37.5, 6: 20.0}

    for method, power in (("nearest", 2), ("idw", 1), ("idw", 2)):
        estimate = estimate_with_diagnostics(
            station.latitude,
            station.longitude,
            "2024-01-01 18:00",
            values,
            method=method,
            power=power,
        )
        assert estimate.predicted_pm25 == pytest.approx(37.5)
        assert estimate.nearest_distance_km == pytest.approx(0.0)
        assert estimate.contributing_stations == 1
        assert estimate.maximum_weight == pytest.approx(1.0)


def test_nearest_and_idw_use_only_supplied_station_values() -> None:
    station_5 = STATION_BY_ID[5]
    station_6 = STATION_BY_ID[6]
    midpoint = (
        (station_5.latitude + station_6.latitude) / 2,
        (station_5.longitude + station_6.longitude) / 2,
    )
    values = {"5": 10.0, "6": 30.0}

    nearest = estimate_pm25(
        midpoint[0],
        midpoint[1],
        "2024-01-01 18:00",
        values,
        method="nearest",
    )
    idw = estimate_pm25(
        midpoint[0],
        midpoint[1],
        pd.Timestamp("2024-01-01 18:00"),
        values,
        method="idw",
        power=2,
    )

    assert nearest in {10.0, 30.0}
    assert idw == pytest.approx(20.0, abs=0.05)


def test_oracle_and_deployment_wrappers_share_algorithm_without_dataset() -> None:
    values = {station_id: float(station_id * 5) for station_id in range(1, 7)}
    target_time = pd.Timestamp("2024-01-01 17:08")
    location = (10.79, 106.67)

    oracle = estimate_oracle_pm25(
        *location, target_time, values, method="idw", power=1
    )
    deployment = estimate_deployment_pm25(
        *location, target_time, values, method="idw", power=1
    )

    assert oracle == pytest.approx(deployment)
    assert np.isfinite(deployment)


def test_reliability_proxies_are_bounded_and_labelled() -> None:
    values = {station_id: float(station_id) for station_id in range(1, 7)}
    estimate = estimate_with_diagnostics(
        10.79,
        106.67,
        "2024-01-01 18:00",
        values,
        method="idw",
        power=2,
    )

    assert estimate.contributing_stations == 6
    assert estimate.second_nearest_distance_km >= estimate.nearest_distance_km
    assert 1 / 6 <= estimate.weight_concentration <= 1
    assert 1 <= estimate.effective_station_count <= 6
    assert 0 < estimate.maximum_weight < 1


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({}, "At least one"),
        ({99: 1.0}, "Unknown"),
        ({1: np.nan}, "finite"),
    ],
)
def test_invalid_station_values_fail_clearly(
    values: dict[int, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        estimate_pm25(10.8, 106.7, "2024-01-01", values)


def test_loso_uses_development_only_and_holds_out_each_station() -> None:
    clean = _synthetic_six_station_data()
    predictions, metrics = evaluate_leave_one_station_out(clean)

    assert predictions["target_time"].max() == pd.Timestamp("2024-01-01 03:00")
    assert set(predictions["held_out_station"]) == set(range(1, 7))
    assert set(predictions["model"]) == {"nearest", "idw_p1", "idw_p2"}
    assert len(predictions) == 4 * 6 * 3
    assert predictions["contributing_stations"].max() == 5
    assert set(metrics["held_out_station"].astype(str)) == {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "ALL",
    }
    assert set(
        metrics.loc[metrics["held_out_station"].eq("ALL"), "unique_timestamps"]
    ) == {4}


def test_temporal_robustness_has_three_chronological_periods() -> None:
    clean = _synthetic_six_station_data()
    predictions, _ = evaluate_leave_one_station_out(clean)
    temporal = temporal_robustness_metrics(predictions)

    assert temporal["period"].astype(str).drop_duplicates().tolist() == [
        "early",
        "middle",
        "late",
    ]
    assert set(temporal["model"]) == {"nearest", "idw_p1", "idw_p2"}
    assert temporal[["mae", "rmse", "r2"]].notna().all().all()
