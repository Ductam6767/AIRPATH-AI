import pandas as pd
import pytest

from src.end_to_end_validation import (
    ROUTE_DEPARTURE_TIME,
    ROUTE_FORECAST_ORIGIN,
    aggregate_heldout_metrics,
    decide_readiness,
    error_decomposition,
    evaluate_heldout_stations,
    evaluate_route_mapping_sensitivity,
    map_target_time_for_sensitivity,
    mapping_sensitivity_metrics,
    reliability_error_relationship,
)
from src.eta_engine import SegmentETA


def _synthetic_predictions(include_test: bool = False) -> pd.DataFrame:
    rows = []
    for day_offset, origin in enumerate(
        (ROUTE_FORECAST_ORIGIN, ROUTE_FORECAST_ORIGIN + pd.Timedelta(days=1))
    ):
        for horizon in (1, 2, 3):
            target = origin + pd.Timedelta(hours=horizon)
            for station in range(1, 7):
                actual = float(10 * station + horizon + day_offset)
                rows.append(
                    {
                        "Station_No": station,
                        "origin_time": origin,
                        "target_time": target,
                        "horizon_hours": horizon,
                        "target_pm25": actual,
                        "prediction": actual + station / 2,
                        "split": "validation",
                        "model": "xgboost_v1",
                    }
                )
    if include_test:
        for station in range(1, 7):
            rows.append(
                {
                    "Station_No": station,
                    "origin_time": pd.Timestamp("2022-05-01 00:00"),
                    "target_time": pd.Timestamp("2022-05-01 01:00"),
                    "horizon_hours": 1,
                    "target_pm25": 10_000.0,
                    "prediction": -10_000.0,
                    "split": "test",
                    "model": "xgboost_v1",
                }
            )
    return pd.DataFrame(rows)


def _segment(index: int, minute: int) -> SegmentETA:
    target = ROUTE_DEPARTURE_TIME + pd.Timedelta(minutes=minute)
    return SegmentETA(
        route_id="walking-1",
        segment_index=index,
        edge_id=f"edge-{index}",
        start_node=index,
        end_node=index + 1,
        road_type="residential",
        direction="forward",
        mode="walking",
        segment_geometry=((10.78, 106.66), (10.781, 106.661)),
        representative_latitude=10.7805 + index / 1000,
        representative_longitude=106.6605 + index / 1000,
        segment_duration_seconds=120.0,
        entry_elapsed_seconds=float((minute - 1) * 60),
        cumulative_elapsed_seconds=float((minute + 1) * 60),
        entry_timestamp=target - pd.Timedelta(minutes=1),
        target_arrival_timestamp=target,
        estimated_arrival_timestamp=target + pd.Timedelta(minutes=1),
    )


def test_heldout_evaluation_has_three_distinct_pathways() -> None:
    evaluation = evaluate_heldout_stations(_synthetic_predictions())

    assert len(evaluation) == 2 * 3 * 6
    assert set(evaluation["horizon_hours"]) == {1, 2, 3}
    assert set(evaluation["held_out_station"]) == set(range(1, 7))
    assert evaluation[
        [
            "forecast_only_prediction",
            "oracle_spatial_prediction",
            "forecast_spatial_prediction",
        ]
    ].notna().all().all()
    assert (
        evaluation["oracle_spatial_prediction"]
        != evaluation["forecast_spatial_prediction"]
    ).any()
    assert (evaluation["contributing_station_count"] == 5).all()


def test_exposed_test_rows_are_excluded_from_development_evaluation() -> None:
    without_test = evaluate_heldout_stations(_synthetic_predictions(False))
    with_test = evaluate_heldout_stations(_synthetic_predictions(True))

    pd.testing.assert_frame_equal(without_test, with_test)
    assert with_test["target_time"].max() < pd.Timestamp("2022-04-08 01:00")


def test_metrics_cover_pooled_station_horizon_and_decomposition() -> None:
    evaluation = evaluate_heldout_stations(_synthetic_predictions())
    metrics = aggregate_heldout_metrics(evaluation)
    decomposition = error_decomposition(metrics)

    assert set(metrics["pipeline"]) == {
        "forecast_only",
        "oracle_spatial",
        "forecast_spatial",
    }
    assert set(metrics["aggregation"]) == {
        "pooled",
        "per_station",
        "per_horizon",
        "station_horizon",
    }
    assert set(decomposition["horizon_hours"].astype(str)) == {
        "ALL",
        "1",
        "2",
        "3",
    }
    pooled = metrics.loc[metrics["aggregation"].eq("pooled")]
    assert pooled[["mae", "rmse", "r2"]].notna().all().all()


def test_mapping_sensitivity_rules_are_deterministic_without_interpolation() -> None:
    requested = pd.Timestamp("2022-02-28 06:20")
    ceiling = map_target_time_for_sensitivity(
        requested, ROUTE_FORECAST_ORIGIN, "ceiling"
    )
    floor = map_target_time_for_sensitivity(
        requested, ROUTE_FORECAST_ORIGIN, "floor"
    )
    nearest = map_target_time_for_sensitivity(
        requested, ROUTE_FORECAST_ORIGIN, "nearest"
    )

    assert ceiling.mapped_target_time == pd.Timestamp("2022-02-28 07:00")
    assert floor.mapped_target_time == pd.Timestamp("2022-02-28 06:00")
    assert nearest.mapped_target_time == floor.mapped_target_time
    assert ceiling.horizon_hours == 2
    assert floor.horizon_hours == 1
    assert "no_interpolation" in ceiling.mapping_method
    tie = map_target_time_for_sensitivity(
        "2022-02-28 06:30", ROUTE_FORECAST_ORIGIN, "nearest"
    )
    assert tie.mapped_target_time == pd.Timestamp("2022-02-28 07:00")


def test_route_sensitivity_preserves_segments_and_hourly_references() -> None:
    segments = [_segment(1, 10), _segment(2, 40)]
    rows = evaluate_route_mapping_sensitivity(
        _synthetic_predictions(),
        {"walking": segments},
    )
    metrics = mapping_sensitivity_metrics(rows)

    assert len(rows) == len(segments) * 3
    for rule in ("ceiling", "floor", "nearest"):
        selected = rows.loc[rows["mapping_rule"].eq(rule)]
        assert selected["segment_index"].tolist() == [1, 2]
    assert set(rows["forecast_horizon_hours"]) == {1, 2}
    assert rows["oracle_spatial_pm25"].notna().all()
    assert rows["forecast_spatial_pm25"].notna().all()
    assert rows["absolute_error"].ge(0).all()
    assert rows["reference_type"].str.contains("not a road measurement").all()
    assert set(metrics["mapping_rule"]) == {"ceiling", "floor", "nearest"}


def test_reliability_analysis_returns_proxy_correlations_and_status_errors() -> None:
    heldout = evaluate_heldout_stations(_synthetic_predictions())
    route_rows = evaluate_route_mapping_sensitivity(
        _synthetic_predictions(),
        {"walking": [_segment(1, 10), _segment(2, 40)]},
    )

    correlations, status = reliability_error_relationship(heldout, route_rows)

    assert set(correlations["analysis"]) == {
        "heldout_station_aggregate",
        "route_segments_ceiling",
    }
    assert {
        "nearest_station_distance_km",
        "second_nearest_station_distance_km",
        "maximum_idw_weight",
        "effective_station_count",
    } == set(correlations["proxy"])
    assert not status.empty
    assert status["segments"].sum() == 2


def test_readiness_decision_uses_explicit_observed_criteria() -> None:
    rows = [
        {
            "pipeline": "forecast_spatial",
            "aggregation": "pooled",
            "held_out_station": "ALL",
            "horizon_hours": "ALL",
            "mae": 7.0,
            "rmse": 9.0,
            "r2": 0.2,
        }
    ]
    for station in range(1, 7):
        rows.append(
            {
                "pipeline": "forecast_spatial",
                "aggregation": "per_station",
                "held_out_station": station,
                "horizon_hours": "ALL",
                "mae": 7.0,
                "rmse": 9.0,
                "r2": 0.1 if station <= 4 else -0.1,
            }
        )

    decision = decide_readiness(pd.DataFrame(rows))

    assert decision.classification == "B. READY WITH RESTRICTIONS"
    assert decision.criteria["positive_station_r2_count"] == 4
