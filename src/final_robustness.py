"""P0-3: freeze C_xgboost_current_pm and validate final decision robustness.

Development/exploratory research-engine freeze. Reuses the P0-2B OD × mode ×
departure-time scenario set. Does not build a web application and does not
overwrite historical milestone artifacts.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .forecasting_fairness import MODEL_C
from .route_optimizer import TIME_TOLERANCES_MINUTES
from .static_vs_arrival_exposure import EVALUATION_LABEL


FROZEN_FORECASTER: Final[str] = MODEL_C
PERTURBATION_SCALES: Final[tuple[float, ...]] = (
    0.80,
    0.90,
    0.95,
    1.00,
    1.05,
    1.10,
    1.20,
)
BASELINE_SCALE: Final[float] = 1.00
SHORTLIST_SIZE: Final[int] = 3
GAP1_CONCLUSION: Final[str] = (
    "MIXED/WEAK evidence that hourly forecast-bucket-aware exposure changes "
    "route decisions relative to a static departure-time snapshot "
    "(P0-2A/P0-2B)."
)


@dataclass(frozen=True)
class ResearchEngineReadiness:
    classification: str
    rationale: str
    criteria: Mapping[str, object]
    remaining_issues: tuple[str, ...]


def load_frozen_route_exposure(
    path: str | Path = (
        "data/processed/temporal_gap_analysis/route_exposure_comparison.csv"
    ),
) -> pd.DataFrame:
    """Load the refreshed Model-C downstream route table from P0-2B."""
    frame = pd.read_csv(path)
    required = {
        "scenario_id",
        "mode",
        "route_id",
        "departure_time",
        "total_travel_time_minutes",
        "airpath_exposure_index",
        "oracle_exposure_index",
        "forecaster",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            "Frozen route exposure missing columns: " + ", ".join(sorted(missing))
        )
    if not frame["forecaster"].eq(FROZEN_FORECASTER).all():
        raise ValueError(
            f"Frozen downstream table must use only {FROZEN_FORECASTER}."
        )
    if frame[["departure_time", "scenario_id", "mode", "route_id"]].duplicated().any():
        raise ValueError("Frozen route exposure contains duplicate route keys.")
    return frame


def apply_prediction_perturbation(
    route_summary: pd.DataFrame,
    scale: float,
) -> pd.DataFrame:
    """Scale predicted/AIRPATH exposures only; leave oracle and times unchanged.

    A global multiplicative scale models controlled forecast-magnitude bias.
    Because every candidate route exposure is scaled by the same factor, route
    ordering by predicted exposure is mathematically invariant. This experiment
    therefore stress-tests selection stability under global bias rather than
    calibrated uncertainty intervals.
    """
    if scale <= 0 or not np.isfinite(scale):
        raise ValueError("Perturbation scale must be a positive finite value.")
    perturbed = route_summary.copy()
    perturbed["perturbation_scale"] = float(scale)
    perturbed["predicted_exposure_index"] = (
        perturbed["airpath_exposure_index"] * float(scale)
    )
    # Keep an explicit unscaled copy for reporting.
    perturbed["baseline_airpath_exposure_index"] = perturbed["airpath_exposure_index"]
    return perturbed


def build_constrained_decisions(
    route_summary: pd.DataFrame,
    tolerances: Sequence[float] = TIME_TOLERANCES_MINUTES,
    *,
    shortlist_size: int = SHORTLIST_SIZE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select min predicted-exposure and min oracle-exposure feasible routes."""
    if shortlist_size < 1:
        raise ValueError("shortlist_size must be positive.")
    if "predicted_exposure_index" not in route_summary.columns:
        raise ValueError("predicted_exposure_index is required.")
    if "perturbation_scale" not in route_summary.columns:
        raise ValueError("perturbation_scale is required.")

    shortlist_rows: list[dict[str, object]] = []
    decision_rows: list[dict[str, object]] = []
    group_keys = ["perturbation_scale", "departure_time", "scenario_id", "mode"]
    for keys, group in route_summary.groupby(group_keys, sort=True):
        scale, departure_time, scenario_id, mode = keys
        fastest = group.sort_values(
            ["total_travel_time_minutes", "route_id"]
        ).iloc[0]
        fastest_time = float(fastest["total_travel_time_minutes"])
        for tolerance in tolerances:
            maximum_time = fastest_time + float(tolerance)
            feasible = group.loc[
                group["total_travel_time_minutes"].le(maximum_time + 1e-9)
            ].copy()
            if feasible.empty:
                raise AssertionError("Fastest route must remain feasible.")
            predicted_ranked = feasible.sort_values(
                ["predicted_exposure_index", "route_id"]
            )
            oracle_ranked = feasible.sort_values(
                ["oracle_exposure_index", "route_id"]
            )
            predicted_selected = predicted_ranked.iloc[0]
            oracle_selected = oracle_ranked.iloc[0]
            alternatives = predicted_ranked.loc[
                ~predicted_ranked["route_id"].eq(fastest["route_id"])
            ].head(shortlist_size)
            shortlist = pd.concat(
                [
                    fastest.to_frame().T.assign(
                        route_type="fastest", shortlist_rank=0
                    ),
                    alternatives.assign(
                        route_type="AIRPATH alternative",
                        shortlist_rank=range(1, len(alternatives) + 1),
                    ),
                ],
                ignore_index=True,
            )
            for row in shortlist.itertuples():
                shortlist_rows.append(
                    {
                        "perturbation_scale": float(scale),
                        "departure_time": departure_time,
                        "scenario_id": scenario_id,
                        "mode": mode,
                        "delta_time_allowed_minutes": float(tolerance),
                        "route_id": row.route_id,
                        "rank": int(row.shortlist_rank),
                        "route_type": row.route_type,
                        "travel_time_minutes": float(row.total_travel_time_minutes),
                        "predicted_exposure_index": float(
                            row.predicted_exposure_index
                        ),
                        "oracle_exposure_index": float(row.oracle_exposure_index),
                        "available_feasible_alternatives": len(feasible) - 1,
                        "fewer_than_requested_alternatives": (
                            len(alternatives) < shortlist_size
                        ),
                    }
                )
            oracle_denominator = float(oracle_selected["oracle_exposure_index"])
            regret = (
                float(predicted_selected["oracle_exposure_index"]) - oracle_denominator
            ) / oracle_denominator
            if regret < -1e-12:
                raise AssertionError("Decision regret cannot be negative.")
            decision_rows.append(
                {
                    "perturbation_scale": float(scale),
                    "departure_time": departure_time,
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "delta_time_allowed_minutes": float(tolerance),
                    "fastest_route_id": fastest["route_id"],
                    "feasible_route_count": int(len(feasible)),
                    "predicted_selected_route_id": predicted_selected["route_id"],
                    "oracle_selected_route_id": oracle_selected["route_id"],
                    "predicted_selected_travel_time_minutes": float(
                        predicted_selected["total_travel_time_minutes"]
                    ),
                    "predicted_selected_predicted_exposure": float(
                        predicted_selected["predicted_exposure_index"]
                    ),
                    "predicted_selected_oracle_exposure": float(
                        predicted_selected["oracle_exposure_index"]
                    ),
                    "oracle_selected_oracle_exposure": oracle_denominator,
                    "decision_regret": max(0.0, float(regret)),
                    "oracle_optimal_agreement": (
                        predicted_selected["route_id"]
                        == oracle_selected["route_id"]
                    ),
                    "top3_predicted_route_ids": json.dumps(
                        predicted_ranked["route_id"].head(shortlist_size).tolist()
                    ),
                    "evaluation_label": EVALUATION_LABEL,
                    "forecaster": FROZEN_FORECASTER,
                    "oracle_label": "model_based_idw_oracle_not_road_measured",
                }
            )
    return pd.DataFrame(shortlist_rows), pd.DataFrame(decision_rows)


def stability_against_baseline(
    decisions: pd.DataFrame,
    shortlists: pd.DataFrame,
    *,
    baseline_scale: float = BASELINE_SCALE,
) -> pd.DataFrame:
    """Compare each perturbation to the unperturbed baseline decisions."""
    if shortlists.empty:
        raise ValueError("Shortlists are required for stability comparison.")
    baseline = decisions.loc[
        decisions["perturbation_scale"].eq(baseline_scale)
    ].copy()
    if baseline.empty:
        raise ValueError("Baseline perturbation scale is missing.")
    key = [
        "departure_time",
        "scenario_id",
        "mode",
        "delta_time_allowed_minutes",
    ]
    baseline_lookup = baseline.set_index(key)

    rows: list[dict[str, object]] = []
    for row in decisions.itertuples():
        index = (
            row.departure_time,
            row.scenario_id,
            row.mode,
            row.delta_time_allowed_minutes,
        )
        base = baseline_lookup.loc[index]
        perturbed_top3 = set(json.loads(row.top3_predicted_route_ids))
        base_top3 = set(json.loads(base["top3_predicted_route_ids"]))
        overlap = len(perturbed_top3 & base_top3)
        rows.append(
            {
                "perturbation_scale": float(row.perturbation_scale),
                "departure_time": row.departure_time,
                "scenario_id": row.scenario_id,
                "mode": row.mode,
                "delta_time_allowed_minutes": float(
                    row.delta_time_allowed_minutes
                ),
                "top1_agreement": (
                    row.predicted_selected_route_id
                    == base["predicted_selected_route_id"]
                ),
                "top3_overlap_count": overlap,
                "top3_overlap_fraction": overlap / max(len(base_top3), 1),
                "selected_travel_time_difference_minutes": float(
                    row.predicted_selected_travel_time_minutes
                    - base["predicted_selected_travel_time_minutes"]
                ),
                "selected_predicted_exposure_difference": float(
                    row.predicted_selected_predicted_exposure
                    - base["predicted_selected_predicted_exposure"]
                ),
                "selected_oracle_exposure_difference": float(
                    row.predicted_selected_oracle_exposure
                    - base["predicted_selected_oracle_exposure"]
                ),
                "baseline_decision_regret": float(base["decision_regret"]),
                "perturbed_decision_regret": float(row.decision_regret),
                "decision_regret_difference": float(
                    row.decision_regret - base["decision_regret"]
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_stability(stability: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groupings = [
        ("all", ["perturbation_scale"]),
        ("mode", ["perturbation_scale", "mode"]),
        ("tolerance", ["perturbation_scale", "delta_time_allowed_minutes"]),
        (
            "mode_tolerance",
            ["perturbation_scale", "mode", "delta_time_allowed_minutes"],
        ),
    ]
    for label, columns in groupings:
        for keys, group in stability.groupby(columns, sort=True):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = {"summary_level": label}
            for column, value in zip(columns, keys, strict=True):
                row[column] = value
            row.update(
                {
                    "cases": len(group),
                    "top1_agreement_rate": float(group["top1_agreement"].mean()),
                    "mean_top3_overlap_fraction": float(
                        group["top3_overlap_fraction"].mean()
                    ),
                    "mean_abs_travel_time_difference_minutes": float(
                        group["selected_travel_time_difference_minutes"]
                        .abs()
                        .mean()
                    ),
                    "mean_abs_predicted_exposure_difference": float(
                        group["selected_predicted_exposure_difference"]
                        .abs()
                        .mean()
                    ),
                    "mean_decision_regret_difference": float(
                        group["decision_regret_difference"].mean()
                    ),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def baseline_oracle_quality(decisions: pd.DataFrame) -> pd.DataFrame:
    baseline = decisions.loc[
        decisions["perturbation_scale"].eq(BASELINE_SCALE)
    ].copy()
    rows: list[dict[str, object]] = []
    groupings = [
        ("all", []),
        ("mode", ["mode"]),
        ("tolerance", ["delta_time_allowed_minutes"]),
        ("departure", ["departure_time"]),
        ("mode_tolerance", ["mode", "delta_time_allowed_minutes"]),
    ]
    for label, columns in groupings:
        if not columns:
            groups = [("ALL", baseline)]
        else:
            groups = list(baseline.groupby(columns, sort=True))
        for key, group in groups:
            if not columns:
                key_map: dict[str, object] = {}
            elif not isinstance(key, tuple):
                key_map = {columns[0]: key}
            else:
                key_map = dict(zip(columns, key, strict=True))
            rows.append(
                {
                    "summary_level": label,
                    **key_map,
                    "cases": len(group),
                    "oracle_optimal_agreement_rate": float(
                        group["oracle_optimal_agreement"].mean()
                    ),
                    "mean_decision_regret": float(group["decision_regret"].mean()),
                    "median_decision_regret": float(
                        group["decision_regret"].median()
                    ),
                    "max_decision_regret": float(group["decision_regret"].max()),
                    "zero_regret_rate": float(
                        group["decision_regret"].le(1e-12).mean()
                    ),
                }
            )
    return pd.DataFrame(rows)


def refreshed_pipeline_summary(route_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mode, departure_time), group in route_summary.groupby(
        ["mode", "departure_time"], sort=True
    ):
        rows.append(
            {
                "forecaster": FROZEN_FORECASTER,
                "mode": mode,
                "departure_time": departure_time,
                "routes": len(group),
                "mean_airpath_exposure": float(
                    group["airpath_exposure_index"].mean()
                ),
                "mean_oracle_exposure": float(
                    group["oracle_exposure_index"].mean()
                ),
                "mean_static_exposure": float(
                    group["static_exposure_index"].mean()
                ),
                "mean_abs_pct_airpath_vs_static": float(
                    group[
                        "percentage_exposure_difference_airpath_vs_static"
                    ]
                    .abs()
                    .mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def decide_research_engine_readiness(
    stability_summary: pd.DataFrame,
    oracle_quality: pd.DataFrame,
) -> ResearchEngineReadiness:
    baseline_stability = stability_summary.loc[
        stability_summary["summary_level"].eq("all")
        & stability_summary["perturbation_scale"].eq(BASELINE_SCALE)
    ].iloc[0]
    nontrivial_scales = stability_summary.loc[
        stability_summary["summary_level"].eq("all")
        & ~stability_summary["perturbation_scale"].eq(BASELINE_SCALE)
    ]
    min_top1 = float(nontrivial_scales["top1_agreement_rate"].min())
    min_top3 = float(nontrivial_scales["mean_top3_overlap_fraction"].min())
    overall_oracle = oracle_quality.loc[
        oracle_quality["summary_level"].eq("all")
    ].iloc[0]
    agreement = float(overall_oracle["oracle_optimal_agreement_rate"])
    mean_regret = float(overall_oracle["mean_decision_regret"])
    max_regret = float(overall_oracle["max_decision_regret"])

    criteria = {
        "frozen_forecaster": FROZEN_FORECASTER,
        "gap1_conclusion": GAP1_CONCLUSION,
        "baseline_top1_agreement": float(baseline_stability["top1_agreement_rate"]),
        "min_perturbed_top1_agreement": min_top1,
        "min_perturbed_top3_overlap": min_top3,
        "oracle_optimal_agreement_rate": agreement,
        "mean_decision_regret": mean_regret,
        "max_decision_regret": max_regret,
        "global_multiplicative_perturbation_is_rank_invariant": True,
        "strict_top1_ge_0_95": min_top1 >= 0.95,
        "strict_top3_ge_0_90": min_top3 >= 0.90,
        "strict_oracle_agreement_ge_0_85": agreement >= 0.85,
        "strict_mean_regret_le_0_02": mean_regret <= 0.02,
        "strict_max_regret_le_0_10": max_regret <= 0.10,
        "restricted_top1_ge_0_90": min_top1 >= 0.90,
        "restricted_top3_ge_0_80": min_top3 >= 0.80,
        "restricted_oracle_agreement_ge_0_70": agreement >= 0.70,
        "restricted_mean_regret_le_0_05": mean_regret <= 0.05,
        "restricted_max_regret_le_0_20": max_regret <= 0.20,
    }
    strict = all(criteria[key] for key in criteria if key.startswith("strict_"))
    restricted = all(
        criteria[key] for key in criteria if key.startswith("restricted_")
    )
    remaining: list[str] = []
    if not criteria["strict_oracle_agreement_ge_0_85"]:
        remaining.append(
            "Model-based oracle agreement is below the strict 85% gate."
        )
    if not criteria["strict_mean_regret_le_0_02"]:
        remaining.append("Mean model-based decision regret exceeds 0.02.")
    if not criteria["strict_max_regret_le_0_10"]:
        remaining.append("Maximum model-based decision regret exceeds 0.10.")
    remaining.extend(
        [
            "Hourly HealthyAir resolution; no minute-level validation.",
            "Six-station spatial support; road PM2.5 is model-estimated.",
            "Oracle exposure is IDW-derived, not road-measured.",
            "Constant-speed ETA without traffic/signal/turn delay.",
            "Pilot-area only; Gap 1 hourly arrival-time benefit remains MIXED/WEAK.",
        ]
    )
    if strict:
        classification = "A. READY TO FREEZE"
        rationale = (
            "Frozen Model C downstream decisions are stable under global "
            "multiplicative prediction bias and pass strict model-based oracle gates."
        )
        remaining = [
            item
            for item in remaining
            if not item.startswith("Model-based")
            and not item.startswith("Mean model-based")
            and not item.startswith("Maximum model-based")
        ]
    elif restricted:
        classification = "B. READY WITH RESTRICTIONS"
        rationale = (
            "The research engine can be frozen for offline prototype integration "
            "with explicit restrictions: Gap 1 remains MIXED/WEAK, oracle quality "
            "is model-based only, and scientific limitations below still apply."
        )
    else:
        classification = "C. NOT READY"
        rationale = (
            "Decision stability or model-based oracle quality fails the restricted "
            "freeze gate."
        )
    return ResearchEngineReadiness(
        classification, rationale, criteria, tuple(remaining)
    )


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    if frame.empty:
        return "_No observations._"
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _plot_outputs(
    stability_summary: pd.DataFrame,
    oracle_quality: pd.DataFrame,
    output_directory: Path,
) -> None:
    overall = stability_summary.loc[
        stability_summary["summary_level"].eq("all")
    ].sort_values("perturbation_scale")
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.plot(
        overall["perturbation_scale"],
        100 * overall["top1_agreement_rate"],
        marker="o",
        label="top-1 agreement",
    )
    axis.plot(
        overall["perturbation_scale"],
        100 * overall["mean_top3_overlap_fraction"],
        marker="s",
        label="top-3 overlap",
    )
    axis.set(
        xlabel="Prediction perturbation scale",
        ylabel="Percent",
        title="Route-selection stability under PM prediction scaling",
        ylim=(0, 105),
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "perturbation_stability.png", dpi=180)
    plt.close(figure)

    by_mode = stability_summary.loc[
        stability_summary["summary_level"].eq("mode")
    ]
    figure, axis = plt.subplots(figsize=(8, 5))
    for mode, group in by_mode.groupby("mode", sort=True):
        axis.plot(
            group["perturbation_scale"],
            100 * group["top1_agreement_rate"],
            marker="o",
            label=mode,
        )
    axis.set(
        xlabel="Prediction perturbation scale",
        ylabel="Top-1 agreement (%)",
        title="Top-1 stability by mode",
        ylim=(0, 105),
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "top1_stability_by_mode.png", dpi=180)
    plt.close(figure)

    tol = oracle_quality.loc[
        oracle_quality["summary_level"].eq("tolerance")
    ].sort_values("delta_time_allowed_minutes")
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.plot(
        tol["delta_time_allowed_minutes"],
        100 * tol["oracle_optimal_agreement_rate"],
        marker="o",
        label="oracle agreement",
    )
    axis.plot(
        tol["delta_time_allowed_minutes"],
        100 * tol["mean_decision_regret"],
        marker="s",
        label="mean regret ×100",
    )
    axis.set(
        xlabel="Additional travel time allowed (minutes)",
        ylabel="Percent",
        title="Model-based oracle agreement and regret by tolerance",
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "oracle_quality_by_tolerance.png", dpi=180)
    plt.close(figure)


def render_report(
    pipeline_summary: pd.DataFrame,
    stability_summary: pd.DataFrame,
    oracle_quality: pd.DataFrame,
    readiness: ResearchEngineReadiness,
    n_routes: int,
    n_cases: int,
) -> str:
    overall_stability = stability_summary.loc[
        stability_summary["summary_level"].eq("all")
    ].sort_values("perturbation_scale")
    overall_oracle = oracle_quality.loc[
        oracle_quality["summary_level"].eq("all")
    ]
    mode_oracle = oracle_quality.loc[oracle_quality["summary_level"].eq("mode")]
    return f"""# AIRPATH-AI P0-3 — downstream freeze and final robustness

## Status

**Development / exploratory research-engine freeze.** This report does not claim
untouched final-test performance and does not authorize a web application.

## A. Forecasting model frozen

Frozen learned forecaster: **`{FROZEN_FORECASTER}`**

Persistence remains a strong baseline and retains lower MAE in the P0-1 fairness
experiment, while `{FROZEN_FORECASTER}` provides the fairer learned comparison and
better RMSE/R². The old unfair XGBoost V1 is **not** used for any new downstream
result in this freeze.

## B. Refreshed downstream exposure results

Pipeline:

`{FROZEN_FORECASTER}` → hourly target-time mapping → IDW p=1 → segment PM2.5 →
route exposure → constrained multi-route selection

Reuses the validated spatial model, OSM network, ETA engine, exposure definition,
and optimizer. Scenario set is the P0-2B reproducible panel
(30 OD × walking/motorbike × supported departure times).

Routes in refreshed table: **{n_routes}**

{_markdown_table(pipeline_summary)}

## C. Refreshed constrained-routing results

Constrained decisions evaluated: **{n_cases}**
(scenario × mode × departure × tolerance × perturbation, with baseline focus below).

Absolute budgets remain `δ ∈ {{0,1,2,3,5,10}}` minutes. The output retains the
fastest route and up to three lower-predicted-exposure feasible alternatives.

## D–F. Robustness under ±5/10/20% PM perturbation

Perturbation scales: {", ".join(str(value) for value in PERTURBATION_SCALES)}.

These are controlled prediction-error sensitivity experiments, **not** calibrated
uncertainty intervals. Only predicted/AIRPATH PM exposures are scaled; oracle
values are never perturbed.

Because the same global factor multiplies every candidate route exposure, predicted
route **ordering is mathematically invariant** under this perturbation family.
Observed top-1/top-3 stability is therefore expected to be perfect; the useful
content is confirmation of that invariance plus oracle quality on the unperturbed
baseline.

{_markdown_table(overall_stability[
    [
        "perturbation_scale",
        "cases",
        "top1_agreement_rate",
        "mean_top3_overlap_fraction",
        "mean_abs_travel_time_difference_minutes",
        "mean_abs_predicted_exposure_difference",
        "mean_decision_regret_difference",
    ]
])}

## G–H. Model-based oracle comparison (unperturbed baseline)

Oracle exposure is IDW-derived from monitors and is **not** road-measured ground
truth. Agreement/regret below are versus this **model-based oracle**.

{_markdown_table(overall_oracle)}

By mode:

{_markdown_table(mode_oracle)}

## I. Static vs arrival-time conclusion

{GAP1_CONCLUSION}

Do not claim a large Gap 1 route-selection benefit from hourly forecast buckets.

## J. Walking vs motorbike

Mode-specific oracle and stability summaries are saved under
`data/processed/final_robustness/`. Walking accumulates larger PM×minutes indexes
because travel durations are longer; selection stability under global multiplicative
bias remains complete for both modes.

## K. Final research-engine readiness

### {readiness.classification}

{readiness.rationale}

```json
{json.dumps(dict(readiness.criteria), indent=2)}
```

Remaining issues / restrictions:

{chr(10).join(f"- {item}" for item in readiness.remaining_issues)}

## L. Exact remaining limitations before prototype/web

1. HealthyAir is hourly; no minute-level validation.
2. Spatial network has only six stations.
3. Road-level PM2.5 is model-estimated.
4. Oracle is IDW-derived, not road-measured.
5. Constant-speed ETA; no traffic/signal/turn-delay model.
6. Pilot-area only.
7. Community/fine-resolution external data not yet validated.
8. Exposure is a time-weighted PM2.5 proxy, not inhaled dose.
9. Gap 1 hourly arrival-time benefit remains MIXED/WEAK.
10. No web application is authorized by this freeze.
"""


def generate_final_robustness_outputs(
    *,
    route_exposure_csv: str | Path = (
        "data/processed/temporal_gap_analysis/route_exposure_comparison.csv"
    ),
    output_directory: str | Path = "data/processed/final_robustness",
    report_path: str | Path = "reports/final_decision_robustness.md",
) -> dict[str, object]:
    baseline_routes = load_frozen_route_exposure(route_exposure_csv)
    pipeline_summary = refreshed_pipeline_summary(baseline_routes)

    perturbed_frames = [
        apply_prediction_perturbation(baseline_routes, scale)
        for scale in PERTURBATION_SCALES
    ]
    all_routes = pd.concat(perturbed_frames, ignore_index=True)
    shortlists, decisions = build_constrained_decisions(all_routes)
    stability = stability_against_baseline(decisions, shortlists)
    stability_summary = summarize_stability(stability)
    oracle_quality = baseline_oracle_quality(decisions)
    readiness = decide_research_engine_readiness(stability_summary, oracle_quality)

    freeze_manifest = {
        "frozen_forecaster": FROZEN_FORECASTER,
        "spatial_model": "idw_p1",
        "eta_model": "constant_speed_mode_specific",
        "exposure_definition": "sum_pm25_times_duration_minutes",
        "route_selector": "absolute_minute_feasible_min_predicted_exposure_plus_top3",
        "scenario_source": "P0-2B temporal_gap_analysis OD x mode x departure panel",
        "gap1_conclusion": GAP1_CONCLUSION,
        "perturbation_scales": list(PERTURBATION_SCALES),
        "perturbation_interpretation": (
            "global_multiplicative_predicted_pm_bias_not_calibrated_uncertainty"
        ),
        "evaluation_label": EVALUATION_LABEL,
        "readiness": asdict(readiness),
    }

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    baseline_routes.to_csv(
        output_directory / "refreshed_route_exposure.csv", index=False
    )
    pipeline_summary.to_csv(
        output_directory / "refreshed_pipeline_summary.csv", index=False
    )
    all_routes.to_csv(
        output_directory / "perturbed_route_exposure.csv", index=False
    )
    shortlists.to_csv(output_directory / "perturbed_shortlists.csv", index=False)
    decisions.to_csv(output_directory / "perturbed_decisions.csv", index=False)
    stability.to_csv(output_directory / "stability_case_metrics.csv", index=False)
    stability_summary.to_csv(
        output_directory / "stability_summary.csv", index=False
    )
    oracle_quality.to_csv(
        output_directory / "baseline_oracle_quality.csv", index=False
    )
    (output_directory / "freeze_manifest.json").write_text(
        json.dumps(freeze_manifest, indent=2), encoding="utf-8"
    )
    (output_directory / "readiness_decision.json").write_text(
        json.dumps(asdict(readiness), indent=2), encoding="utf-8"
    )
    _plot_outputs(stability_summary, oracle_quality, output_directory)
    baseline_decisions = decisions.loc[
        decisions["perturbation_scale"].eq(BASELINE_SCALE)
    ]
    report_path.write_text(
        render_report(
            pipeline_summary,
            stability_summary,
            oracle_quality,
            readiness,
            n_routes=len(baseline_routes),
            n_cases=len(baseline_decisions),
        ),
        encoding="utf-8",
    )
    return {
        "baseline_routes": baseline_routes,
        "pipeline_summary": pipeline_summary,
        "shortlists": shortlists,
        "decisions": decisions,
        "stability": stability,
        "stability_summary": stability_summary,
        "oracle_quality": oracle_quality,
        "readiness": readiness,
        "freeze_manifest": freeze_manifest,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--route-exposure-csv",
        default=(
            "data/processed/temporal_gap_analysis/route_exposure_comparison.csv"
        ),
    )
    parser.add_argument(
        "--output-directory", default="data/processed/final_robustness"
    )
    parser.add_argument(
        "--report", default="reports/final_decision_robustness.md"
    )
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_final_robustness_outputs(
        route_exposure_csv=arguments.route_exposure_csv,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
    )
    print(outputs["stability_summary"].loc[
        lambda frame: frame["summary_level"].eq("all")
    ].to_string(index=False))
    print(outputs["oracle_quality"].loc[
        lambda frame: frame["summary_level"].eq("all")
    ].to_string(index=False))
    print(outputs["readiness"])


if __name__ == "__main__":
    main()
