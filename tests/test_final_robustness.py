import pandas as pd
import pytest

from src.final_robustness import (
    BASELINE_SCALE,
    FROZEN_FORECASTER,
    PERTURBATION_SCALES,
    apply_prediction_perturbation,
    baseline_oracle_quality,
    build_constrained_decisions,
    decide_research_engine_readiness,
    stability_against_baseline,
    summarize_stability,
)


def _routes() -> pd.DataFrame:
    rows = []
    for departure in ("2022-02-27T06:00:00", "2022-02-27T17:00:00"):
        for index, (airpath, oracle, minutes) in enumerate(
            (
                (100.0, 110.0, 20.0),
                (90.0, 100.0, 21.0),
                (80.0, 105.0, 23.0),
                (70.0, 90.0, 28.0),
            ),
            start=1,
        ):
            rows.append(
                {
                    "scenario_id": "od_01",
                    "mode": "walking",
                    "route_id": f"walking-{index}",
                    "departure_time": departure,
                    "total_travel_time_minutes": minutes,
                    "airpath_exposure_index": airpath,
                    "oracle_exposure_index": oracle,
                    "static_exposure_index": airpath + 5,
                    "percentage_exposure_difference_airpath_vs_static": -5.0,
                    "forecaster": FROZEN_FORECASTER,
                }
            )
    return pd.DataFrame(rows)


def test_frozen_forecaster_is_current_pm_model() -> None:
    assert FROZEN_FORECASTER == "C_xgboost_current_pm"
    assert BASELINE_SCALE in PERTURBATION_SCALES
    assert 0.8 in PERTURBATION_SCALES
    assert 1.2 in PERTURBATION_SCALES


def test_perturbation_scales_predicted_only() -> None:
    routes = apply_prediction_perturbation(_routes(), 1.1)
    assert routes["predicted_exposure_index"].iloc[0] == pytest.approx(110.0)
    assert routes["oracle_exposure_index"].iloc[0] == pytest.approx(110.0)
    assert routes["total_travel_time_minutes"].iloc[0] == pytest.approx(20.0)


def test_global_scale_preserves_selected_route() -> None:
    frames = [
        apply_prediction_perturbation(_routes(), scale)
        for scale in (0.8, 1.0, 1.2)
    ]
    all_routes = pd.concat(frames, ignore_index=True)
    _, decisions = build_constrained_decisions(all_routes, tolerances=(0, 5))
    selected = (
        decisions.groupby("perturbation_scale")["predicted_selected_route_id"]
        .unique()
        .apply(list)
    )
    assert selected.loc[0.8] == selected.loc[1.0] == selected.loc[1.2]


def test_stability_and_oracle_metrics() -> None:
    frames = [
        apply_prediction_perturbation(_routes(), scale)
        for scale in PERTURBATION_SCALES
    ]
    all_routes = pd.concat(frames, ignore_index=True)
    shortlists, decisions = build_constrained_decisions(
        all_routes, tolerances=(0, 3, 5)
    )
    stability = stability_against_baseline(decisions, shortlists)
    summary = summarize_stability(stability)
    oracle = baseline_oracle_quality(decisions)
    readiness = decide_research_engine_readiness(summary, oracle)

    assert stability["top1_agreement"].all()
    assert summary.loc[
        summary["summary_level"].eq("all")
        & ~summary["perturbation_scale"].eq(1.0),
        "top1_agreement_rate",
    ].min() == 1.0
    assert oracle.loc[oracle["summary_level"].eq("all"), "cases"].iloc[0] > 0
    assert readiness.classification in {
        "A. READY TO FREEZE",
        "B. READY WITH RESTRICTIONS",
        "C. NOT READY",
    }
    assert readiness.criteria["frozen_forecaster"] == FROZEN_FORECASTER


def test_negative_scale_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        apply_prediction_perturbation(_routes(), -1.0)
