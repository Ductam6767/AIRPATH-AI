import pandas as pd
import pytest

from src.road_network import point_in_pilot_area
from src.route_optimizer import (
    build_feasible_shortlists,
    decision_regret_summary,
    decide_optimization_readiness,
    expanded_ranking_quality,
    feasibility_summary,
    generate_od_scenarios,
)


def _route_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "scenario_id": ["od_01"] * 5,
            "mode": ["walking"] * 5,
            "route_id": [f"walking-{index}" for index in range(1, 6)],
            "total_distance_m": [2000, 2100, 2200, 2400, 3000],
            "total_travel_time_minutes": [20.0, 21.0, 22.0, 24.0, 30.0],
            "segment_count": [20, 21, 22, 24, 30],
            "predicted_exposure_index": [100.0, 90.0, 80.0, 70.0, 60.0],
            "oracle_exposure_index": [100.0, 85.0, 95.0, 75.0, 65.0],
            "edge_jaccard_with_fastest": [1.0, 0.8, 0.6, 0.4, 0.2],
            "edge_difference_fraction_from_fastest": [0.0, 0.2, 0.4, 0.6, 0.8],
        }
    )


def test_scenarios_are_deterministic_varied_and_inside_pilot() -> None:
    first = generate_od_scenarios(seed=42, count_scenarios=10)
    second = generate_od_scenarios(seed=42, count_scenarios=10)

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 10
    assert first["straight_line_distance_km"].between(2, 6).all()
    assert first["straight_line_distance_km"].nunique() > 5
    assert all(
        point_in_pilot_area(row.origin_latitude, row.origin_longitude)
        and point_in_pilot_area(
            row.destination_latitude, row.destination_longitude
        )
        for row in first.itertuples()
    )


def test_absolute_minute_constraint_builds_exact_feasible_set() -> None:
    feasible, shortlist, decisions = build_feasible_shortlists(
        _route_summary(), tolerances=(0, 3)
    )

    zero = feasible.loc[feasible["delta_time_allowed_minutes"].eq(0)]
    assert zero.loc[zero["is_feasible"], "route_id"].tolist() == ["walking-1"]
    three = feasible.loc[feasible["delta_time_allowed_minutes"].eq(3)]
    assert set(three.loc[three["is_feasible"], "route_id"]) == {
        "walking-1",
        "walking-2",
        "walking-3",
    }
    decision = decisions.loc[
        decisions["delta_time_allowed_minutes"].eq(3)
    ].iloc[0]
    assert decision["maximum_feasible_time_minutes"] == 23
    assert decision["epsilon_internal"] == pytest.approx(3 / 20)
    assert decision["predicted_optimal_route_id"] == "walking-3"
    assert decision["oracle_optimal_route_id"] == "walking-2"


def test_fastest_is_always_retained_and_top_three_are_separate() -> None:
    _, shortlist, _ = build_feasible_shortlists(
        _route_summary(), tolerances=(10,), shortlist_size=3
    )

    assert shortlist.iloc[0]["route_type"] == "fastest"
    assert shortlist.iloc[0]["route_id"] == "walking-1"
    alternatives = shortlist.loc[
        shortlist["route_type"].eq("AIRPATH alternative")
    ]
    assert len(alternatives) == 3
    assert alternatives["rank"].tolist() == [1, 2, 3]
    assert alternatives["route_id"].tolist() == [
        "walking-5",
        "walking-4",
        "walking-3",
    ]
    assert (alternatives["additional_time_vs_fastest_minutes"] >= 0).all()


def test_fewer_than_three_alternatives_is_reported_explicitly() -> None:
    _, shortlist, _ = build_feasible_shortlists(
        _route_summary(), tolerances=(1,), shortlist_size=3
    )

    assert len(shortlist) == 2
    assert shortlist["fewer_than_requested_alternatives"].all()
    assert set(shortlist["available_feasible_alternatives"]) == {1}


def test_decision_regret_formula_and_summary() -> None:
    _, _, decisions = build_feasible_shortlists(
        _route_summary(), tolerances=(0, 3)
    )
    three = decisions.loc[
        decisions["delta_time_allowed_minutes"].eq(3)
    ].iloc[0]

    assert three["decision_regret"] == pytest.approx((95 - 85) / 85)
    assert not bool(three["oracle_optimal_agreement"])
    summary = decision_regret_summary(decisions)
    assert set(summary["delta_time_allowed_minutes"].astype(str)) == {
        "ALL",
        "0.0",
        "3.0",
    }
    assert summary.loc[
        summary["delta_time_allowed_minutes"].eq("0.0"),
        "zero_regret_percentage",
    ].iloc[0] == 100


def test_ranking_quality_is_downstream_and_does_not_mutate_exposures() -> None:
    summary = _route_summary()
    original = summary.copy(deep=True)

    ranking, quality = expanded_ranking_quality(summary)

    pd.testing.assert_frame_equal(summary, original)
    assert len(ranking) == 5
    assert quality.iloc[0]["top_1_agreement"] in (True, False)
    assert -1 <= quality.iloc[0]["spearman_rank_correlation"] <= 1
    assert -1 <= quality.iloc[0]["kendall_tau_a"] <= 1


def test_feasibility_categories_and_readiness_gate() -> None:
    _, _, decisions = build_feasible_shortlists(
        _route_summary(), tolerances=(0, 5)
    )
    feasibility = feasibility_summary(decisions)
    assert feasibility.loc[
        feasibility["delta_time_allowed_minutes"].eq(0),
        "no_alternative_beyond_fastest",
    ].iloc[0] == 1
    quality = pd.DataFrame(
        {
            "spearman_rank_correlation": [0.8, 0.7],
        }
    )
    # Duplicate nontrivial decisions to represent a small multi-case experiment.
    expanded = pd.concat([decisions, decisions.assign(scenario_id="od_02")])
    decision = decide_optimization_readiness(expanded, quality, feasibility)
    assert decision.classification in {
        "A. READY FOR PROTOTYPE INTEGRATION",
        "B. READY WITH RESTRICTIONS",
        "C. NOT READY",
    }


def test_negative_user_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        build_feasible_shortlists(_route_summary(), tolerances=(-1,))
