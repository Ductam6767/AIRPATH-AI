import pandas as pd
import pytest

from src.temporal_gap_analysis import (
    ANALYSIS_DATE,
    PREFERRED_DEPARTURE_HOURS,
    compare_route_rankings_temporal,
    constrained_selection_temporal,
    decide_temporal_gap_evidence,
    departure_time_summary,
    forecasting_origin_for_departure,
    select_departure_times,
)


def _route_summary() -> pd.DataFrame:
    rows = []
    for hour, static_shift in ((6, 0.0), (17, 5.0), (20, 15.0)):
        departure = (ANALYSIS_DATE + pd.Timedelta(hours=hour)).isoformat()
        for index, (static_e, airpath_e, oracle_e, time_m) in enumerate(
            (
                (100.0, 100.0 + static_shift, 110.0, 20.0),
                (90.0, 80.0 + static_shift, 100.0, 21.0),
                (80.0, 95.0 + static_shift, 105.0, 23.0),
                (70.0, 60.0 + static_shift, 90.0, 28.0),
            ),
            start=1,
        ):
            rows.append(
                {
                    "departure_time": departure,
                    "clock_time": f"{hour:02d}:00",
                    "scenario_id": "od_01",
                    "mode": "walking",
                    "route_id": f"walking-{index}",
                    "total_distance_m": 2000 + 100 * index,
                    "total_travel_time_minutes": time_m,
                    "segment_count": 10 + index,
                    "static_exposure_index": static_e,
                    "airpath_exposure_index": airpath_e,
                    "oracle_exposure_index": oracle_e,
                    "percentage_exposure_difference_airpath_vs_static": 100
                    * (airpath_e - static_e)
                    / static_e,
                    "edge_jaccard_with_fastest": 1.0,
                    "edge_difference_fraction_from_fastest": 0.0,
                }
            )
    return pd.DataFrame(rows)


def test_forecasting_origin_is_one_hour_before_departure() -> None:
    departure = pd.Timestamp("2022-02-27 17:00:00")
    assert forecasting_origin_for_departure(departure) == pd.Timestamp(
        "2022-02-27 16:00:00"
    )


def test_preferred_hours_include_brief_targets() -> None:
    assert PREFERRED_DEPARTURE_HOURS == (6, 8, 12, 17, 20)


def test_select_departure_times_on_analysis_date_supports_all_preferred() -> None:
    clean = pd.read_csv(
        "data/processed/airquality_hcmc_clean.csv", parse_dates=["date"]
    )
    fairness = pd.read_csv(
        "data/processed/forecasting_fairness/fairness_predictions.csv",
        parse_dates=["origin_time", "target_time"],
    )
    table, supported = select_departure_times(clean, fairness)
    assert table["supported"].all()
    assert len(supported) == 5
    assert {item.departure_time.hour for item in supported} == set(
        PREFERRED_DEPARTURE_HOURS
    )


def test_feb28_excludes_incomplete_morning_and_midday() -> None:
    clean = pd.read_csv(
        "data/processed/airquality_hcmc_clean.csv", parse_dates=["date"]
    )
    fairness = pd.read_csv(
        "data/processed/forecasting_fairness/fairness_predictions.csv",
        parse_dates=["origin_time", "target_time"],
    )
    table, supported = select_departure_times(
        clean,
        fairness,
        analysis_date=pd.Timestamp("2022-02-28"),
    )
    unsupported = set(
        table.loc[~table["supported"], "preferred_clock_time"]
    )
    assert "08:00" in unsupported
    assert "12:00" in unsupported
    assert {item.departure_time.hour for item in supported} == {6, 17, 20}


def test_temporal_ranking_and_selection_are_departure_aware() -> None:
    summary = _route_summary()
    ranking, quality = compare_route_rankings_temporal(summary)
    selections = constrained_selection_temporal(summary, tolerances=(0, 5))
    assert set(quality["departure_time"]) == set(summary["departure_time"])
    assert "departure_time" in selections.columns
    assert ranking["material_rank_change"].any()


def test_departure_summary_and_decision_labels() -> None:
    summary = _route_summary()
    _, quality = compare_route_rankings_temporal(summary)
    selections = constrained_selection_temporal(summary, tolerances=(0, 3, 5))
    dep_summary = departure_time_summary(selections, quality, summary)
    decision = decide_temporal_gap_evidence(dep_summary, selections, quality)
    assert len(dep_summary) == 3
    assert decision.classification in {
        "A. STRONG EVIDENCE FOR ARRIVAL-TIME INFORMATION BENEFIT",
        "B. MIXED EVIDENCE",
        "C. LITTLE / NO EVIDENCE",
    }
    assert decision.criteria["forecaster"] == "C_xgboost_current_pm"
    assert len(decision.strongest_departure_times) == 2
