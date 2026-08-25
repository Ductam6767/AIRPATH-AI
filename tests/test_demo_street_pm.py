import pandas as pd
import pytest

from src.demo_street_pm import (
    lane_factor,
    parse_lane_count,
    peak_factor,
    road_class_factor,
    simulate_route_exposures,
    simulate_segment_pm,
    way_id_from_edge_id,
)


def test_arterials_are_dirtier_than_residential_and_footways() -> None:
    background = 40.0
    residential = simulate_segment_pm(background, highway="residential", hour=6)
    primary = simulate_segment_pm(background, highway="primary", lanes=4, hour=6)
    footway = simulate_segment_pm(background, highway="footway", hour=6)
    assert primary > residential > footway
    assert primary / background > 1.2
    assert footway / background < 1.0


def test_peak_and_lanes_increase_arterial_pm() -> None:
    background = 40.0
    off_peak = simulate_segment_pm(background, highway="primary", hour=12)
    morning = simulate_segment_pm(background, highway="primary", hour=6)
    wide = simulate_segment_pm(background, highway="primary", lanes=6, hour=6)
    assert morning > off_peak
    assert wide > morning
    assert peak_factor(8, "primary") > peak_factor(12, "primary")
    assert peak_factor(6, "primary") == pytest.approx(1.12)
    assert peak_factor(6, "residential") == pytest.approx(1.0)
    assert lane_factor(6) > lane_factor(2)
    assert parse_lane_count("4;3") == 4
    assert road_class_factor("primary") > road_class_factor("service")


def test_route_exposure_is_duration_weighted() -> None:
    segments = pd.DataFrame(
        {
            "scenario_id": ["od_x", "od_x"],
            "route_id": ["walking-1", "walking-1"],
            "mode": ["walking", "walking"],
            "segment_id": ["1:0:f", "2:0:f"],
            "segment_duration_minutes": [10.0, 10.0],
            "pm25_estimate": [20.0, 20.0],
        }
    )
    lookup = {"1": {"highway": "primary"}, "2": {"highway": "residential"}}
    result = simulate_route_exposures(segments, lookup, hour=6)
    assert len(result) == 1
    expected = (
        simulate_segment_pm(20.0, highway="primary", hour=6) * 10
        + simulate_segment_pm(20.0, highway="residential", hour=6) * 10
    )
    assert result.iloc[0]["predicted_exposure_index"] == pytest.approx(expected)
    assert result.iloc[0]["background_exposure_index"] == pytest.approx(400.0)
    assert way_id_from_edge_id("197982830:1:r") == "197982830"
