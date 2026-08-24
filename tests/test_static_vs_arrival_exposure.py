import pandas as pd
import pytest

from src.eta_engine import SegmentETA
from src.forecasting_fairness import MODEL_C
from src.static_vs_arrival_exposure import (
    compare_route_rankings,
    compute_static_exposure,
    constrained_selection_comparison,
    decide_arrival_evidence,
    edge_case_summary,
    load_model_c_forecast_tables,
    load_static_snapshot,
    mode_tolerance_summary,
)


def _clean_snapshot() -> pd.DataFrame:
    rows = []
    for station in range(1, 7):
        rows.append(
            {
                "date": pd.Timestamp("2022-02-28 06:00:00"),
                "Station_No": station,
                "PM2.5": float(10 + station),
            }
        )
    return pd.DataFrame(rows)


def _segments() -> list[SegmentETA]:
    return [
        SegmentETA(
            route_id="walking-1",
            segment_index=1,
            edge_id="e1",
            start_node=1,
            end_node=2,
            road_type="residential",
            direction="forward",
            mode="walking",
            segment_geometry=((10.78, 106.65), (10.7805, 106.6505)),
            representative_latitude=10.78,
            representative_longitude=106.65,
            segment_duration_seconds=120.0,
            entry_elapsed_seconds=0.0,
            cumulative_elapsed_seconds=120.0,
            entry_timestamp=pd.Timestamp("2022-02-28 06:00:00"),
            target_arrival_timestamp=pd.Timestamp("2022-02-28 06:02:00"),
            estimated_arrival_timestamp=pd.Timestamp("2022-02-28 06:02:00"),
        ),
        SegmentETA(
            route_id="walking-1",
            segment_index=2,
            edge_id="e2",
            start_node=2,
            end_node=3,
            road_type="residential",
            direction="forward",
            mode="walking",
            segment_geometry=((10.7805, 106.6505), (10.781, 106.651)),
            representative_latitude=10.781,
            representative_longitude=106.651,
            segment_duration_seconds=180.0,
            entry_elapsed_seconds=120.0,
            cumulative_elapsed_seconds=300.0,
            entry_timestamp=pd.Timestamp("2022-02-28 06:02:00"),
            target_arrival_timestamp=pd.Timestamp("2022-02-28 06:05:00"),
            estimated_arrival_timestamp=pd.Timestamp("2022-02-28 06:05:00"),
        ),
    ]


def _route_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "scenario_id": ["od_01"] * 4,
            "mode": ["walking"] * 4,
            "route_id": [f"walking-{index}" for index in range(1, 5)],
            "total_distance_m": [2000, 2100, 2300, 2600],
            "total_travel_time_minutes": [20.0, 21.0, 23.0, 28.0],
            "segment_count": [10, 11, 12, 14],
            "static_exposure_index": [100.0, 90.0, 80.0, 70.0],
            "airpath_exposure_index": [100.0, 85.0, 95.0, 60.0],
            "oracle_exposure_index": [110.0, 100.0, 105.0, 90.0],
            "edge_jaccard_with_fastest": [1.0, 0.8, 0.5, 0.2],
            "edge_difference_fraction_from_fastest": [0.0, 0.2, 0.5, 0.8],
        }
    )


def test_static_snapshot_requires_all_stations() -> None:
    values = load_static_snapshot(_clean_snapshot())
    assert set(values) == {1, 2, 3, 4, 5, 6}
    assert values[1] == pytest.approx(11.0)


def test_static_exposure_uses_same_snapshot_for_all_segments() -> None:
    values = load_static_snapshot(_clean_snapshot())
    records = compute_static_exposure(
        "od_01",
        _segments(),
        pd.Timestamp("2022-02-28 06:00:00"),
        values,
    )
    assert len(records) == 2
    assert {record.mapped_target_time for record in records} == {
        pd.Timestamp("2022-02-28 06:00:00")
    }
    assert {record.mapping_method for record in records} == {
        "static_departure_snapshot"
    }
    assert all(record.forecast_horizon_hours == 0 for record in records)
    # Different locations may differ spatially, but the time snapshot is fixed.
    assert records[0].eta != records[1].eta


def test_model_c_loader_rejects_old_v1_model_name() -> None:
    frame = pd.DataFrame(
        {
            "Station_No": [1, 2, 3, 4, 5, 6],
            "origin_time": [pd.Timestamp("2022-02-28 05:00:00")] * 6,
            "target_time": [pd.Timestamp("2022-02-28 06:00:00")] * 6,
            "horizon_hours": [1] * 6,
            "prediction": [10.0] * 6,
            "split": ["validation"] * 6,
            "model": ["xgboost_v1"] * 6,
        }
    )
    with pytest.raises(ValueError, match="Incomplete Model C|must cover exactly"):
        load_model_c_forecast_tables(frame)


def test_ranking_and_selection_detect_framework_disagreement() -> None:
    summary = _route_summary()
    ranking, quality = compare_route_rankings(summary)
    selections = constrained_selection_comparison(summary, tolerances=(0, 5))
    assert quality.iloc[0]["top_1_agreement"] in (True, False)
    assert ranking["material_rank_change"].any()
    five = selections.loc[selections["delta_time_allowed_minutes"].eq(5)].iloc[0]
    # δ=5 keeps routes with times 20/21/23; walking-4 at 28 remains infeasible.
    assert five["static_selected_route_id"] == "walking-3"
    assert five["airpath_selected_route_id"] == "walking-2"
    assert five["selections_differ"]
    zero = selections.loc[selections["delta_time_allowed_minutes"].eq(0)].iloc[0]
    assert zero["only_one_feasible_route"]
    assert not zero["selections_differ"]


def test_selection_difference_records_oracle_improvement() -> None:
    summary = _route_summary()
    # Make AIRPATH prefer walking-2 while static prefers walking-3 under +3 min.
    summary.loc[
        summary["route_id"].eq("walking-2"), "airpath_exposure_index"
    ] = 50.0
    summary.loc[
        summary["route_id"].eq("walking-3"), "static_exposure_index"
    ] = 40.0
    selections = constrained_selection_comparison(summary, tolerances=(3,))
    row = selections.iloc[0]
    assert row["selections_differ"]
    assert row["static_selected_route_id"] == "walking-3"
    assert row["airpath_selected_route_id"] == "walking-2"
    expected = 100 * (105.0 - 100.0) / 105.0
    assert row["oracle_percent_improvement_airpath_over_static"] == pytest.approx(
        expected
    )


def test_edge_cases_and_decision_labels() -> None:
    selections = constrained_selection_comparison(
        _route_summary(), tolerances=(0, 5)
    )
    edges = edge_case_summary(selections)
    modes = mode_tolerance_summary(selections)
    ranking, quality = compare_route_rankings(_route_summary())
    decision = decide_arrival_evidence(selections, quality, edges)
    assert edges.loc[
        edges["delta_time_allowed_minutes"].eq(0),
        "no_alternative_beyond_fastest",
    ].iloc[0] == 1
    assert not modes.empty
    assert decision.classification in {
        "A. STRONG EVIDENCE FOR ARRIVAL-TIME INFORMATION BENEFIT",
        "B. MIXED EVIDENCE",
        "C. LITTLE / NO EVIDENCE",
    }
    assert decision.criteria["forecaster"] == MODEL_C
    assert decision.criteria["evaluation_status"].startswith("development_")
