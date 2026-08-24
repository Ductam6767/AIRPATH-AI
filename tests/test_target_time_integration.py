import inspect

import pandas as pd
import pytest

from src.eta_engine import SegmentETA
from src.target_time_integration import (
    StationLagBundle,
    StationValueError,
    UnsupportedTargetTimeError,
    build_station_lag_bundle,
    classify_spatial_reliability,
    forecast_station_values,
    integrate_route_deployment,
    integrate_route_oracle,
    map_target_time,
)
from src.spatial_estimation import SpatialEstimate


ORIGIN = pd.Timestamp("2024-01-01 17:00:00")


class FakeForecaster:
    station_ids = ("1", "2")
    models = {1: object(), 2: object(), 3: object()}

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def predict_pm25(
        self,
        station_or_location,
        target_time,
        *,
        prediction_time,
        pm25_lags,
        temperature=None,
        humidity=None,
    ) -> float:
        target = pd.Timestamp(target_time)
        prediction = pd.Timestamp(prediction_time)
        self.calls.append(
            {
                "station": int(station_or_location),
                "target_time": target,
                "prediction_time": prediction,
                "lags": dict(pm25_lags),
            }
        )
        horizon = int((target - prediction) / pd.Timedelta(hours=1))
        return float(10 * int(station_or_location) + horizon)


def _lag_bundle(origin: pd.Timestamp = ORIGIN) -> StationLagBundle:
    return StationLagBundle(
        forecasting_origin_time=origin,
        values_by_station={
            1: {1: 10.0, 2: 9.0, 3: 8.0},
            2: {1: 20.0, 2: 19.0, 3: 18.0},
        },
        source_times_by_station={
            station: {
                lag: origin - pd.Timedelta(hours=lag) for lag in (1, 2, 3)
            }
            for station in (1, 2)
        },
    )


def _segment(index: int, minute: int) -> SegmentETA:
    entry = ORIGIN + pd.Timedelta(minutes=minute - 1)
    target = ORIGIN + pd.Timedelta(minutes=minute)
    end = ORIGIN + pd.Timedelta(minutes=minute + 1)
    start_node = index
    end_node = index + 1
    return SegmentETA(
        route_id="walking-1",
        segment_index=index,
        edge_id=f"edge-{index}",
        start_node=start_node,
        end_node=end_node,
        road_type="residential",
        direction="forward",
        mode="walking",
        segment_geometry=((10.78, 106.66), (10.781, 106.661)),
        representative_latitude=10.7805,
        representative_longitude=106.6605,
        segment_duration_seconds=120.0,
        entry_elapsed_seconds=float((minute - 1) * 60),
        cumulative_elapsed_seconds=float((minute + 1) * 60),
        entry_timestamp=entry,
        target_arrival_timestamp=target,
        estimated_arrival_timestamp=end,
    )


def test_hourly_target_mapping_is_deterministic_and_explicit() -> None:
    first = map_target_time("2024-01-01 17:03:00", ORIGIN)
    second = map_target_time(pd.Timestamp("2024-01-01 17:03:00"), ORIGIN)

    assert first == second
    assert first.supported_target_time == pd.Timestamp("2024-01-01 18:00:00")
    assert first.mapping_method == "ceiling_to_next_hour_no_interpolation"
    assert first.mapping_offset_seconds == 57 * 60
    assert not first.is_exact
    assert first.forecast_horizon_hours == 1
    assert first.supported

    exact = map_target_time("2024-01-01 18:00:00", ORIGIN)
    assert exact.mapping_method == "exact_hour"
    assert exact.mapping_offset_seconds == 0
    assert exact.is_exact


def test_unsupported_horizon_is_reported_and_never_extrapolated() -> None:
    mapping = map_target_time("2024-01-01 20:01:00", ORIGIN)

    assert not mapping.supported
    assert mapping.status == "unsupported_forecast_horizon"
    assert mapping.forecast_horizon_hours == 4
    with pytest.raises(UnsupportedTargetTimeError, match="horizon=4h"):
        mapping.require_supported()


def test_deployment_forecasts_use_exact_pre_origin_lags_only() -> None:
    forecaster = FakeForecaster()
    mapping = map_target_time("2024-01-01 17:03:00", ORIGIN)

    bundle = forecast_station_values(forecaster, mapping, _lag_bundle())

    assert bundle.source_mode == "deployment_forecast"
    assert bundle.target_time == pd.Timestamp("2024-01-01 18:00:00")
    assert bundle.values == {1: 11.0, 2: 21.0}
    assert len(forecaster.calls) == 2
    assert all(call["target_time"] == bundle.target_time for call in forecaster.calls)
    assert all(call["prediction_time"] == ORIGIN for call in forecaster.calls)
    assert "observed_station_values" not in inspect.signature(
        integrate_route_deployment
    ).parameters


def test_future_or_inexact_lag_provenance_is_rejected() -> None:
    bundle = _lag_bundle()
    bad_times = {
        station: dict(times)
        for station, times in bundle.source_times_by_station.items()
    }
    bad_times[1][1] = ORIGIN + pd.Timedelta(hours=1)
    bad = StationLagBundle(
        ORIGIN,
        bundle.values_by_station,
        bad_times,
    )
    mapping = map_target_time("2024-01-01 17:03:00", ORIGIN)

    with pytest.raises(StationValueError, match="strictly pre-origin"):
        forecast_station_values(FakeForecaster(), mapping, bad)


def test_oracle_and_deployment_paths_are_distinct_and_time_consistent() -> None:
    segments = [_segment(1, 3), _segment(2, 10)]
    forecaster = FakeForecaster()
    deployment = integrate_route_deployment(
        segments, ORIGIN, forecaster, _lag_bundle()
    )
    oracle = integrate_route_oracle(
        segments,
        ORIGIN,
        {pd.Timestamp("2024-01-01 18:00:00"): {1: 100.0, 2: 200.0}},
    )

    assert [record.segment_index for record in deployment] == [1, 2]
    assert [record.segment_id for record in deployment] == ["edge-1", "edge-2"]
    assert all(record.requested_target_time is not None for record in deployment)
    assert all(
        record.station_values_target_time == record.supported_target_time
        for record in deployment + oracle
    )
    assert all(
        record.station_value_source == "deployment_forecast"
        for record in deployment
    )
    assert all(
        record.station_value_source == "oracle_observed" for record in oracle
    )
    assert deployment[0].station_values_used != oracle[0].station_values_used
    assert deployment[0].predicted_pm25 != oracle[0].predicted_pm25
    assert all(record.spatial_method == "idw" for record in deployment + oracle)
    assert all(record.spatial_power == 1.0 for record in deployment + oracle)


def test_segment_beyond_horizon_raises_explicit_error() -> None:
    unsupported = _segment(1, 181)

    with pytest.raises(UnsupportedTargetTimeError, match="horizon=4h"):
        integrate_route_deployment(
            [unsupported], ORIGIN, FakeForecaster(), _lag_bundle()
        )


def test_noncontiguous_segment_order_is_rejected() -> None:
    segments = [_segment(1, 3), _segment(3, 10)]

    with pytest.raises(ValueError, match="ordering"):
        integrate_route_deployment(
            segments, ORIGIN, FakeForecaster(), _lag_bundle()
        )


def test_build_lag_bundle_uses_only_exact_historical_timestamps() -> None:
    rows = []
    for station in (1, 2):
        for lag in (1, 2, 3):
            rows.append(
                {
                    "Station_No": station,
                    "date": ORIGIN - pd.Timedelta(hours=lag),
                    "PM2.5": float(station * 10 + lag),
                }
            )
    # A future value exists but must not enter the deployment lag bundle.
    rows.append(
        {
            "Station_No": 1,
            "date": ORIGIN + pd.Timedelta(hours=1),
            "PM2.5": 9999.0,
        }
    )
    clean = pd.DataFrame(rows)

    bundle = build_station_lag_bundle(clean, ORIGIN, (1, 2))

    assert bundle.values_by_station[1] == {1: 11.0, 2: 12.0, 3: 13.0}
    assert 9999.0 not in {
        value
        for values in bundle.values_by_station.values()
        for value in values.values()
    }
    assert all(
        timestamp < ORIGIN
        for times in bundle.source_times_by_station.values()
        for timestamp in times.values()
    )


def test_reliability_heuristic_recognises_near_monitor_support() -> None:
    estimate = SpatialEstimate(
        predicted_pm25=20.0,
        target_time=ORIGIN + pd.Timedelta(hours=1),
        method="idw",
        power=1.0,
        nearest_station_id=6,
        nearest_distance_km=0.1,
        second_nearest_distance_km=3.0,
        contributing_stations=6,
        maximum_weight=0.9,
        weight_concentration=0.82,
        effective_station_count=1.22,
    )

    assert classify_spatial_reliability(estimate) == "supported"
