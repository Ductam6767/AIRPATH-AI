import inspect

import pandas as pd
import pytest

from src.eta_engine import SegmentETA
from src.exposure import (
    SegmentExposure,
    aggregate_exposure_index,
    compute_oracle_exposure,
    compute_predicted_exposure,
    decide_exposure_readiness,
    rank_candidate_exposures,
)


ORIGIN = pd.Timestamp("2024-01-01 17:00:00")
TARGET = pd.Timestamp("2024-01-01 18:00:00")


def _record(
    index: int,
    pm25: float,
    duration_minutes: float,
    *,
    pipeline: str = "predicted_exposure",
    segment_id: str | None = None,
) -> SegmentExposure:
    return SegmentExposure(
        scenario_id="scenario-1",
        route_id="walking-1",
        mode="walking",
        pipeline_mode=pipeline,
        segment_index=index,
        segment_id=segment_id or f"edge-{index}",
        eta=ORIGIN + pd.Timedelta(minutes=index),
        mapped_target_time=TARGET,
        mapping_method="ceiling_to_next_hour_no_interpolation",
        forecast_horizon_hours=1,
        latitude=10.78,
        longitude=106.66,
        segment_duration_minutes=duration_minutes,
        pm25_estimate=pm25,
        exposure_contribution=pm25 * duration_minutes,
        contribution_fraction=0.0,
        nearest_station_distance_km=1.0,
        second_nearest_station_distance_km=3.0,
        contributing_station_count=6,
        maximum_idw_weight=0.4,
        effective_station_count=3.5,
        reliability_status="supported",
    )


def _segment(index: int, minute: int, duration_seconds: float) -> SegmentETA:
    target = ORIGIN + pd.Timedelta(minutes=minute)
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
        segment_duration_seconds=duration_seconds,
        entry_elapsed_seconds=0.0,
        cumulative_elapsed_seconds=duration_seconds,
        entry_timestamp=ORIGIN,
        target_arrival_timestamp=target,
        estimated_arrival_timestamp=target + pd.Timedelta(seconds=duration_seconds / 2),
    )


def _station_values(base: float) -> dict[pd.Timestamp, dict[int, float]]:
    return {
        TARGET: {
            station: base + station for station in range(1, 7)
        }
    }


def test_exposure_equals_sum_pm_times_duration_minutes() -> None:
    records = [_record(1, 10.0, 2.0), _record(2, 20.0, 3.0)]

    exposure = aggregate_exposure_index(records)

    assert exposure == pytest.approx(10 * 2 + 20 * 3)


def test_exposure_is_deterministic_and_includes_every_segment_once() -> None:
    segments = [_segment(1, 3, 120), _segment(2, 10, 180)]

    first = compute_predicted_exposure(
        "scenario-1", segments, ORIGIN, _station_values(10)
    )
    second = compute_predicted_exposure(
        "scenario-1", segments, ORIGIN, _station_values(10)
    )

    assert first == second
    assert [record.segment_index for record in first] == [1, 2]
    assert len({record.segment_id for record in first}) == 2
    assert sum(record.contribution_fraction for record in first) == pytest.approx(1)
    assert aggregate_exposure_index(first) == pytest.approx(
        sum(record.exposure_contribution for record in first)
    )


def test_negative_duration_and_duplicate_segments_are_rejected() -> None:
    negative = [_record(1, 10.0, -1.0)]
    with pytest.raises(ValueError, match="non-negative"):
        aggregate_exposure_index(negative)

    duplicate = [
        _record(1, 10.0, 1.0, segment_id="same"),
        _record(2, 10.0, 1.0, segment_id="same"),
    ]
    with pytest.raises(ValueError, match="exactly once"):
        aggregate_exposure_index(duplicate)


def test_oracle_and_predicted_exposure_paths_remain_separate() -> None:
    segments = [_segment(1, 3, 120), _segment(2, 10, 180)]

    oracle = compute_oracle_exposure(
        "scenario-1", segments, ORIGIN, _station_values(100)
    )
    predicted = compute_predicted_exposure(
        "scenario-1", segments, ORIGIN, _station_values(10)
    )

    assert all(record.pipeline_mode == "oracle_exposure" for record in oracle)
    assert all(
        record.pipeline_mode == "predicted_exposure" for record in predicted
    )
    assert aggregate_exposure_index(oracle) != aggregate_exposure_index(predicted)
    assert "observed_station_values_by_target" not in inspect.signature(
        compute_predicted_exposure
    ).parameters


def test_ranking_is_purely_downstream_of_exposure_calculation() -> None:
    summary = pd.DataFrame(
        {
            "scenario_id": ["s"] * 5,
            "mode": ["walking"] * 5,
            "route_id": [f"walking-{index}" for index in range(1, 6)],
            "oracle_exposure_index": [10, 20, 30, 40, 50],
            "predicted_exposure_index": [12, 19, 29, 42, 49],
        }
    )
    original = summary.copy(deep=True)

    ranking, agreement = rank_candidate_exposures(summary.sample(frac=1, random_state=3))

    pd.testing.assert_frame_equal(summary, original)
    assert len(ranking) == 5
    assert agreement.iloc[0]["spearman_rank_correlation"] == pytest.approx(1)
    assert agreement.iloc[0]["kendall_tau_a"] == pytest.approx(1)
    assert bool(agreement.iloc[0]["top_1_agreement"])
    assert agreement.iloc[0]["top_2_overlap_count"] == 2


def test_readiness_gate_uses_ranking_and_exposure_error() -> None:
    agreement = pd.DataFrame(
        {
            "top_1_agreement": [True, False, True, False],
            "spearman_rank_correlation": [0.8, 0.7, 0.6, 0.7],
        }
    )
    errors = pd.DataFrame(
        {
            "mode": ["walking", "motorbike"],
            "mean_absolute_percentage_error": [15.0, 20.0],
        }
    )

    decision = decide_exposure_readiness(agreement, errors)

    assert decision.classification == "B. READY WITH RESTRICTIONS"
    assert decision.criteria["restricted_top_1_agreement_ge_half"]
