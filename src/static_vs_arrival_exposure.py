"""P0-2A: static/current exposure vs forecast-bucket-aware arrival-time exposure.

Development/exploratory only. Uses the selected C_xgboost_current_pm forecaster.
Does not overwrite historical XGBoost V1 artifacts or modify spatial/routing cores.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Final, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .eta_engine import SegmentETA, propagate_segment_etas
from .exposure import (
    FORECASTING_ORIGIN,
    ROUTE_DEPARTURE,
    SegmentExposure,
    _kendall_tau_a,
    _spearman,
    aggregate_exposure_index,
    compute_oracle_exposure,
    compute_predicted_exposure,
)
from .forecasting_fairness import MODEL_C
from .road_network import RoadNetwork, load_network
from .route_candidates import CandidateRoute
from .route_optimizer import (
    TIME_TOLERANCES_MINUTES,
    candidate_diversity_rows,
    generate_diverse_candidates,
    generate_od_scenarios,
)
from .spatial_estimation import STATION_BY_ID, estimate_with_diagnostics
from .target_time_integration import classify_spatial_reliability


RANDOM_SEED: Final[int] = 42
SCENARIO_COUNT: Final[int] = 30
MATERIAL_RANK_SHIFT: Final[int] = 1
EXPOSURE_UNIT: Final[str] = "(µg/m³)·min"
EVALUATION_LABEL: Final[str] = "development_exploratory_not_untouched_final"


@dataclass(frozen=True)
class ArrivalEvidenceDecision:
    classification: str
    rationale: str
    criteria: Mapping[str, object]


def load_static_snapshot(
    clean: pd.DataFrame,
    snapshot_time: object = ROUTE_DEPARTURE,
) -> dict[int, float]:
    """Observed station PM2.5 at departure T0 for the static baseline."""
    timestamp = pd.Timestamp(snapshot_time)
    rows = clean.loc[clean["date"].eq(timestamp), ["Station_No", "PM2.5"]].copy()
    if rows.empty:
        raise ValueError(f"No observed PM2.5 snapshot at {timestamp}.")
    if rows["Station_No"].duplicated().any():
        raise ValueError("Static snapshot has duplicate station rows.")
    values = {
        int(station): float(value)
        for station, value in zip(rows["Station_No"], rows["PM2.5"], strict=True)
    }
    if set(values) != set(STATION_BY_ID):
        raise ValueError("Static snapshot must cover all HealthyAir stations.")
    if any(not np.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("Static snapshot values must be finite and non-negative.")
    return values


def load_model_c_forecast_tables(
    fairness_predictions: pd.DataFrame,
    forecasting_origin: object = FORECASTING_ORIGIN,
) -> dict[pd.Timestamp, dict[int, float]]:
    """Station forecasts from selected C_xgboost_current_pm at one origin."""
    origin = pd.Timestamp(forecasting_origin)
    rows = fairness_predictions.copy()
    rows["origin_time"] = pd.to_datetime(rows["origin_time"], errors="raise")
    rows["target_time"] = pd.to_datetime(rows["target_time"], errors="raise")
    rows["Station_No"] = rows["Station_No"].astype(int)
    rows["horizon_hours"] = rows["horizon_hours"].astype(int)
    rows = rows.loc[
        rows["split"].eq("validation")
        & rows["model"].eq(MODEL_C)
        & rows["origin_time"].eq(origin)
        & rows["horizon_hours"].isin((1, 2, 3))
    ]
    if rows.duplicated(["horizon_hours", "Station_No"]).any():
        raise ValueError("Model C forecast table has duplicate station/horizon rows.")
    forecasted: dict[pd.Timestamp, dict[int, float]] = {}
    for horizon, group in rows.groupby("horizon_hours", sort=True):
        if set(group["Station_No"]) != set(STATION_BY_ID):
            raise ValueError(f"Incomplete Model C t+{horizon}h station forecasts.")
        if group["target_time"].nunique() != 1:
            raise ValueError("Model C forecasts have inconsistent target times.")
        target = pd.Timestamp(group["target_time"].iloc[0])
        if target != origin + pd.Timedelta(hours=int(horizon)):
            raise ValueError("Model C target time mismatches origin plus horizon.")
        forecasted[target] = {
            int(station): float(value)
            for station, value in zip(
                group["Station_No"], group["prediction"], strict=True
            )
        }
    if set(forecasted) != {
        origin + pd.Timedelta(hours=1),
        origin + pd.Timedelta(hours=2),
        origin + pd.Timedelta(hours=3),
    }:
        raise ValueError("Model C tables must cover exactly t+1h, t+2h, and t+3h.")
    return forecasted


def load_oracle_observed_tables(
    clean: pd.DataFrame,
    forecasting_origin: object = FORECASTING_ORIGIN,
) -> dict[pd.Timestamp, dict[int, float]]:
    """Observed station PM2.5 at supported hourly buckets after the origin."""
    origin = pd.Timestamp(forecasting_origin)
    observed: dict[pd.Timestamp, dict[int, float]] = {}
    for horizon in (1, 2, 3):
        target = origin + pd.Timedelta(hours=horizon)
        rows = clean.loc[clean["date"].eq(target), ["Station_No", "PM2.5"]]
        if set(rows["Station_No"].astype(int)) != set(STATION_BY_ID):
            raise ValueError(f"Incomplete observed stations at {target}.")
        observed[target] = {
            int(station): float(value)
            for station, value in zip(
                rows["Station_No"], rows["PM2.5"], strict=True
            )
        }
    return observed


def compute_static_exposure(
    scenario_id: str,
    segments: Sequence[SegmentETA],
    snapshot_time: object,
    station_values_at_snapshot: Mapping[int | str, float],
) -> list[SegmentExposure]:
    """Method A: assign the same departure-time IDW snapshot to every segment.

    E_static(R) = Σ_i PM_static(X_i, T0) × duration_i

    ETA is recorded for diagnostics but does not change the pollution snapshot.
    """
    if not segments:
        raise ValueError("Static exposure requires at least one segment.")
    timestamp = pd.Timestamp(snapshot_time)
    values = {int(station): float(value) for station, value in station_values_at_snapshot.items()}
    if set(values) != set(STATION_BY_ID):
        raise ValueError("Static exposure requires all station values at T0.")
    records: list[SegmentExposure] = []
    seen: set[str] = set()
    for expected_index, segment in enumerate(segments, start=1):
        if segment.segment_index != expected_index:
            raise ValueError("Segments must be contiguous and ordered.")
        if segment.edge_id in seen:
            raise ValueError("Every route segment must be included exactly once.")
        seen.add(segment.edge_id)
        duration_minutes = float(segment.segment_duration_seconds) / 60.0
        if not np.isfinite(duration_minutes) or duration_minutes < 0:
            raise ValueError("Segment duration must be non-negative and finite.")
        estimate = estimate_with_diagnostics(
            segment.representative_latitude,
            segment.representative_longitude,
            timestamp,
            values,
            method="idw",
            power=1,
        )
        if not np.isfinite(estimate.predicted_pm25) or estimate.predicted_pm25 < 0:
            raise ValueError("Static segment PM2.5 must be finite and non-negative.")
        records.append(
            SegmentExposure(
                scenario_id=scenario_id,
                route_id=segment.route_id,
                mode=segment.mode,
                pipeline_mode="static_current_exposure",
                segment_index=segment.segment_index,
                segment_id=segment.edge_id,
                eta=segment.target_arrival_timestamp,
                mapped_target_time=timestamp,
                mapping_method="static_departure_snapshot",
                forecast_horizon_hours=0,
                latitude=segment.representative_latitude,
                longitude=segment.representative_longitude,
                segment_duration_minutes=duration_minutes,
                pm25_estimate=estimate.predicted_pm25,
                exposure_contribution=estimate.predicted_pm25 * duration_minutes,
                contribution_fraction=0.0,
                nearest_station_distance_km=estimate.nearest_distance_km,
                second_nearest_station_distance_km=estimate.second_nearest_distance_km,
                contributing_station_count=estimate.contributing_stations,
                maximum_idw_weight=estimate.maximum_weight,
                effective_station_count=estimate.effective_station_count,
                reliability_status=classify_spatial_reliability(estimate),
            )
        )
    total = aggregate_exposure_index(records)
    if total <= 0:
        raise ValueError("Static route exposure must be positive.")
    return [
        replace(record, contribution_fraction=record.exposure_contribution / total)
        for record in records
    ]


def summarize_dual_exposure(
    route: CandidateRoute,
    scenario_id: str,
    static_records: Sequence[SegmentExposure],
    airpath_records: Sequence[SegmentExposure],
    oracle_records: Sequence[SegmentExposure],
    diversity: Mapping[str, object],
) -> dict[str, object]:
    static_total = aggregate_exposure_index(static_records)
    airpath_total = aggregate_exposure_index(airpath_records)
    oracle_total = aggregate_exposure_index(oracle_records)
    difference = airpath_total - static_total
    return {
        "scenario_id": scenario_id,
        "mode": route.mode,
        "route_id": route.route_id,
        "total_distance_m": route.total_distance_m,
        "total_travel_time_minutes": route.total_travel_time_seconds / 60.0,
        "segment_count": len(route.edge_ids),
        "static_exposure_index": static_total,
        "airpath_exposure_index": airpath_total,
        "oracle_exposure_index": oracle_total,
        "absolute_exposure_difference_airpath_minus_static": difference,
        "percentage_exposure_difference_airpath_vs_static": 100.0
        * difference
        / static_total,
        "edge_jaccard_with_fastest": float(diversity["edge_jaccard_with_fastest"]),
        "edge_difference_fraction_from_fastest": float(
            diversity["edge_difference_fraction_from_fastest"]
        ),
        "evaluation_label": EVALUATION_LABEL,
        "forecaster": MODEL_C,
        "exposure_framework_b": "hourly_forecast_bucket_aware_arrival_time_exposure",
    }


def compare_route_rankings(route_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    for (scenario_id, mode), group in route_summary.groupby(
        ["scenario_id", "mode"], sort=True
    ):
        static_order = group.sort_values(
            ["static_exposure_index", "route_id"]
        )["route_id"].tolist()
        airpath_order = group.sort_values(
            ["airpath_exposure_index", "route_id"]
        )["route_id"].tolist()
        static_rank = {route_id: index + 1 for index, route_id in enumerate(static_order)}
        airpath_rank = {
            route_id: index + 1 for index, route_id in enumerate(airpath_order)
        }
        route_ids = sorted(static_rank)
        static_values = [static_rank[route_id] for route_id in route_ids]
        airpath_values = [airpath_rank[route_id] for route_id in route_ids]
        material_changes = 0
        for route_id in route_ids:
            shift = airpath_rank[route_id] - static_rank[route_id]
            ranking_rows.append(
                {
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "route_id": route_id,
                    "rank_static": static_rank[route_id],
                    "rank_airpath": airpath_rank[route_id],
                    "rank_shift_airpath_minus_static": shift,
                    "material_rank_change": abs(shift) >= MATERIAL_RANK_SHIFT,
                }
            )
            material_changes += int(abs(shift) >= MATERIAL_RANK_SHIFT)
        quality_rows.append(
            {
                "scenario_id": scenario_id,
                "mode": mode,
                "route_count": len(group),
                "spearman_static_vs_airpath": _spearman(static_values, airpath_values),
                "kendall_tau_a_static_vs_airpath": _kendall_tau_a(
                    static_values, airpath_values
                ),
                "top_1_agreement": static_order[0] == airpath_order[0],
                "routes_with_material_rank_change": material_changes,
                "percentage_routes_with_material_rank_change": 100.0
                * material_changes
                / len(route_ids),
            }
        )
    return pd.DataFrame(ranking_rows), pd.DataFrame(quality_rows)


def constrained_selection_comparison(
    route_summary: pd.DataFrame,
    tolerances: Sequence[float] = TIME_TOLERANCES_MINUTES,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (scenario_id, mode), group in route_summary.groupby(
        ["scenario_id", "mode"], sort=True
    ):
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
            static_selected = feasible.sort_values(
                ["static_exposure_index", "route_id"]
            ).iloc[0]
            airpath_selected = feasible.sort_values(
                ["airpath_exposure_index", "route_id"]
            ).iloc[0]
            selections_differ = (
                static_selected["route_id"] != airpath_selected["route_id"]
            )
            oracle_static = float(static_selected["oracle_exposure_index"])
            oracle_airpath = float(airpath_selected["oracle_exposure_index"])
            oracle_improvement_pct = (
                100.0 * (oracle_static - oracle_airpath) / oracle_static
                if selections_differ
                else 0.0
            )
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "delta_time_allowed_minutes": float(tolerance),
                    "fastest_route_id": fastest["route_id"],
                    "fastest_time_minutes": fastest_time,
                    "maximum_feasible_time_minutes": maximum_time,
                    "feasible_route_count": int(len(feasible)),
                    "only_one_feasible_route": len(feasible) == 1,
                    "static_selected_route_id": static_selected["route_id"],
                    "airpath_selected_route_id": airpath_selected["route_id"],
                    "selections_differ": bool(selections_differ),
                    "static_selected_travel_time_minutes": float(
                        static_selected["total_travel_time_minutes"]
                    ),
                    "airpath_selected_travel_time_minutes": float(
                        airpath_selected["total_travel_time_minutes"]
                    ),
                    "static_selected_static_exposure": float(
                        static_selected["static_exposure_index"]
                    ),
                    "airpath_selected_airpath_exposure": float(
                        airpath_selected["airpath_exposure_index"]
                    ),
                    "static_selected_airpath_exposure": float(
                        static_selected["airpath_exposure_index"]
                    ),
                    "airpath_selected_static_exposure": float(
                        airpath_selected["static_exposure_index"]
                    ),
                    "oracle_exposure_static_selected": oracle_static,
                    "oracle_exposure_airpath_selected": oracle_airpath,
                    "oracle_percent_improvement_airpath_over_static": (
                        oracle_improvement_pct
                    ),
                    "static_predicted_reduction_vs_fastest": float(
                        fastest["static_exposure_index"]
                        - static_selected["static_exposure_index"]
                    ),
                    "airpath_predicted_reduction_vs_fastest": float(
                        fastest["airpath_exposure_index"]
                        - airpath_selected["airpath_exposure_index"]
                    ),
                    "oracle_reduction_static_selected_vs_fastest": float(
                        fastest["oracle_exposure_index"]
                        - static_selected["oracle_exposure_index"]
                    ),
                    "oracle_reduction_airpath_selected_vs_fastest": float(
                        fastest["oracle_exposure_index"]
                        - airpath_selected["oracle_exposure_index"]
                    ),
                    "evaluation_label": EVALUATION_LABEL,
                }
            )
    return pd.DataFrame(rows)


def edge_case_summary(selections: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for tolerance, group in selections.groupby(
        "delta_time_allowed_minutes", sort=True
    ):
        rows.append(
            {
                "delta_time_allowed_minutes": tolerance,
                "scenario_mode_cases": len(group),
                "same_route_selected": int((~group["selections_differ"]).sum()),
                "different_routes_selected": int(group["selections_differ"].sum()),
                "only_one_feasible_route": int(group["only_one_feasible_route"].sum()),
                "no_alternative_beyond_fastest": int(
                    group["feasible_route_count"].eq(1).sum()
                ),
                "percentage_selections_differ": float(
                    100.0 * group["selections_differ"].mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def mode_tolerance_summary(selections: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (mode, tolerance), group in selections.groupby(
        ["mode", "delta_time_allowed_minutes"], sort=True
    ):
        differing = group.loc[group["selections_differ"]]
        rows.append(
            {
                "mode": mode,
                "delta_time_allowed_minutes": tolerance,
                "cases": len(group),
                "percentage_selections_differ": float(
                    100.0 * group["selections_differ"].mean()
                ),
                "mean_static_predicted_reduction_vs_fastest": float(
                    group["static_predicted_reduction_vs_fastest"].mean()
                ),
                "mean_airpath_predicted_reduction_vs_fastest": float(
                    group["airpath_predicted_reduction_vs_fastest"].mean()
                ),
                "mean_oracle_reduction_static_selected_vs_fastest": float(
                    group["oracle_reduction_static_selected_vs_fastest"].mean()
                ),
                "mean_oracle_reduction_airpath_selected_vs_fastest": float(
                    group["oracle_reduction_airpath_selected_vs_fastest"].mean()
                ),
                "differing_cases": len(differing),
                "mean_oracle_percent_improvement_when_differ": (
                    float(
                        differing[
                            "oracle_percent_improvement_airpath_over_static"
                        ].mean()
                    )
                    if not differing.empty
                    else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows)


def decide_arrival_evidence(
    selections: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    edge_cases: pd.DataFrame,
) -> ArrivalEvidenceDecision:
    nontrivial = selections.loc[selections["delta_time_allowed_minutes"].gt(0)]
    differ_rate = float(nontrivial["selections_differ"].mean())
    differing = nontrivial.loc[nontrivial["selections_differ"]]
    mean_oracle_gain = (
        float(differing["oracle_percent_improvement_airpath_over_static"].mean())
        if not differing.empty
        else 0.0
    )
    positive_gain_rate = (
        float(
            differing["oracle_percent_improvement_airpath_over_static"].gt(0).mean()
        )
        if not differing.empty
        else 0.0
    )
    mean_spearman = float(ranking_quality["spearman_static_vs_airpath"].mean())
    mean_material_rank_pct = float(
        ranking_quality["percentage_routes_with_material_rank_change"].mean()
    )
    five_min = edge_cases.loc[
        edge_cases["delta_time_allowed_minutes"].eq(5)
    ].iloc[0]
    criteria = {
        "evaluation_status": EVALUATION_LABEL,
        "forecaster": MODEL_C,
        "nontrivial_selection_difference_rate": differ_rate,
        "mean_oracle_percent_improvement_when_differ": mean_oracle_gain,
        "positive_oracle_gain_rate_when_differ": positive_gain_rate,
        "mean_spearman_static_vs_airpath": mean_spearman,
        "mean_percentage_routes_with_material_rank_change": mean_material_rank_pct,
        "five_minute_selection_difference_percentage": float(
            five_min["percentage_selections_differ"]
        ),
        "strong_differ_rate_ge_0_25": differ_rate >= 0.25,
        "strong_oracle_gain_ge_1_0": mean_oracle_gain >= 1.0,
        "strong_positive_gain_rate_ge_0_60": positive_gain_rate >= 0.60,
        "mixed_differ_rate_ge_0_10": differ_rate >= 0.10,
        "mixed_rank_change_ge_10": mean_material_rank_pct >= 10.0,
    }
    strong = (
        criteria["strong_differ_rate_ge_0_25"]
        and criteria["strong_oracle_gain_ge_1_0"]
        and criteria["strong_positive_gain_rate_ge_0_60"]
    )
    mixed = (
        criteria["mixed_differ_rate_ge_0_10"]
        or criteria["mixed_rank_change_ge_10"]
        or differ_rate > 0
    ) and not strong
    if strong:
        classification = "A. STRONG EVIDENCE FOR ARRIVAL-TIME INFORMATION BENEFIT"
        rationale = (
            "Feasible route selections differ often under nontrivial time budgets, "
            "and AIRPATH selections improve oracle exposure on average when they differ."
        )
    elif mixed:
        classification = "B. MIXED EVIDENCE"
        rationale = (
            "Static and AIRPATH frameworks sometimes reorder or reselect routes, "
            "but oracle gains when selections differ are weak, inconsistent, or limited."
        )
    else:
        classification = "C. LITTLE / NO EVIDENCE"
        rationale = (
            "Arrival-time forecast buckets rarely change ranking or constrained "
            "selection relative to the static departure snapshot."
        )
    return ArrivalEvidenceDecision(classification, rationale, criteria)


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    if frame.empty:
        return "_No observations._"
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _plot_outputs(
    route_summary: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    selections: pd.DataFrame,
    mode_summary: pd.DataFrame,
    output_directory: Path,
) -> None:
    figure, axis = plt.subplots(figsize=(6, 6))
    axis.scatter(
        route_summary["static_exposure_index"],
        route_summary["airpath_exposure_index"],
        alpha=0.45,
        s=18,
    )
    lower = min(
        route_summary["static_exposure_index"].min(),
        route_summary["airpath_exposure_index"].min(),
    )
    upper = max(
        route_summary["static_exposure_index"].max(),
        route_summary["airpath_exposure_index"].max(),
    )
    axis.plot([lower, upper], [lower, upper], "k--", linewidth=1)
    axis.set(
        xlabel=f"Static exposure {EXPOSURE_UNIT}",
        ylabel=f"AIRPATH exposure {EXPOSURE_UNIT}",
        title="Static vs AIRPATH route exposure",
    )
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "static_vs_airpath_exposure_scatter.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(10, 5))
    labels = ranking_quality["scenario_id"] + "/" + ranking_quality["mode"]
    axis.bar(labels, ranking_quality["spearman_static_vs_airpath"], color="#1565c0")
    axis.set(
        ylabel="Spearman(static, AIRPATH)",
        title="Route-ranking agreement by scenario/mode",
        ylim=(-1.05, 1.05),
    )
    axis.tick_params(axis="x", rotation=90, labelsize=6)
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "ranking_correlation.png", dpi=180)
    plt.close(figure)

    differ = (
        selections.groupby(["mode", "delta_time_allowed_minutes"], as_index=False)[
            "selections_differ"
        ]
        .mean()
        .assign(percentage=lambda frame: 100 * frame["selections_differ"])
    )
    figure, axis = plt.subplots(figsize=(8, 5))
    for mode, group in differ.groupby("mode", sort=True):
        axis.plot(
            group["delta_time_allowed_minutes"],
            group["percentage"],
            marker="o",
            label=mode,
        )
    axis.set(
        xlabel="Additional travel time allowed (minutes)",
        ylabel="Percentage of selections that differ",
        title="Time-budget sensitivity of route selection",
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "selection_difference_by_tolerance.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    for mode, group in mode_summary.groupby("mode", sort=True):
        axis.plot(
            group["delta_time_allowed_minutes"],
            group["mean_oracle_percent_improvement_when_differ"],
            marker="o",
            label=mode,
        )
    axis.axhline(0.0, color="#424242", linewidth=1)
    axis.set(
        xlabel="Additional travel time allowed (minutes)",
        ylabel="Mean oracle % improvement when selections differ",
        title="Downstream oracle gain of AIRPATH over static",
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "oracle_gain_when_differ.png", dpi=180)
    plt.close(figure)


def render_report(
    scenarios: pd.DataFrame,
    route_summary: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    selections: pd.DataFrame,
    edge_cases: pd.DataFrame,
    mode_summary: pd.DataFrame,
    decision: ArrivalEvidenceDecision,
) -> str:
    pooled = {
        "n_routes": len(route_summary),
        "mean_static": float(route_summary["static_exposure_index"].mean()),
        "mean_airpath": float(route_summary["airpath_exposure_index"].mean()),
        "mean_abs_diff": float(
            route_summary[
                "absolute_exposure_difference_airpath_minus_static"
            ]
            .abs()
            .mean()
        ),
        "mean_pct_diff": float(
            route_summary[
                "percentage_exposure_difference_airpath_vs_static"
            ].mean()
        ),
    }
    per_mode = (
        route_summary.groupby("mode", as_index=False)
        .agg(
            n_routes=("route_id", "count"),
            mean_static_exposure=("static_exposure_index", "mean"),
            mean_airpath_exposure=("airpath_exposure_index", "mean"),
            mean_pct_diff=(
                "percentage_exposure_difference_airpath_vs_static",
                "mean",
            ),
        )
    )
    nontrivial = selections.loc[selections["delta_time_allowed_minutes"].gt(0)]
    differ_rate = float(nontrivial["selections_differ"].mean())
    differing = nontrivial.loc[nontrivial["selections_differ"]]
    oracle_gain = (
        float(differing["oracle_percent_improvement_airpath_over_static"].mean())
        if not differing.empty
        else float("nan")
    )
    return f"""# AIRPATH-AI P0-2A — static vs arrival-time exposure

## Status

**Development / exploratory only.** This experiment does not claim untouched
final-test performance. It uses the selected development forecaster
`{MODEL_C}` and does not modify historical XGBoost V1 artifacts.

AIRPATH exposure here is explicitly labeled:

**hourly forecast-bucket-aware arrival-time exposure**

Hourly target buckets are used. No sub-hourly interpolation is performed. This
does **not** establish minute-level PM2.5 accuracy.

## Definitions

### Method A — static / current pollution exposure

At departure time `T0 = {ROUTE_DEPARTURE}`:

1. read the observed HealthyAir PM2.5 state at `T0`;
2. estimate spatial PM2.5 with existing IDW p=1;
3. assign that **same departure-time snapshot** to every route segment;
4. compute `E_static(R) = Σ_i PM_static(X_i, T0) × duration_i`.

ETA is recorded but does not change the pollution field.

### Method B — AIRPATH arrival-time exposure

Forecasting origin `{FORECASTING_ORIGIN}` with `{MODEL_C}`:

segment `i` → `ETA_i` → supported hourly bucket → station forecasts → IDW p=1
→ `PM2.5(X_i, ETA_bucket)` →
`E_AIRPATH(R) = Σ_i PM_AIRPATH_i × duration_i`.

Oracle exposure remains the existing ETA-bucket observed-station IDW pathway.
Oracle values are IDW-derived and are **not** road-measured ground truth.

## A. OD scenarios

{len(scenarios)} deterministic OD scenarios (seed `{RANDOM_SEED}`) inside the
validated stations 2–6 polygon with straight-line distance 2–6 km.

{_markdown_table(scenarios.head(12))}

## B–D. Exposure comparison

Pooled mean static exposure: **{pooled['mean_static']:.4f}** {EXPOSURE_UNIT}

Pooled mean AIRPATH exposure: **{pooled['mean_airpath']:.4f}** {EXPOSURE_UNIT}

Mean absolute difference |AIRPATH − static|: **{pooled['mean_abs_diff']:.4f}**

Mean percentage difference: **{pooled['mean_pct_diff']:.4f}%**

Per mode:

{_markdown_table(per_mode)}

## E. Ranking correlations

{_markdown_table(ranking_quality)}

Mean Spearman: **{float(ranking_quality['spearman_static_vs_airpath'].mean()):.4f}**

Mean share of routes with material rank change (|Δrank| ≥ {MATERIAL_RANK_SHIFT}):
**{float(ranking_quality['percentage_routes_with_material_rank_change'].mean()):.2f}%**

## F. Route-selection differences

Nontrivial budgets (δ > 0): **{100 * differ_rate:.2f}%** of OD/mode/budget cases
select different routes.

{_markdown_table(edge_cases)}

## G. Oracle exposure improvement when selections differ

Mean oracle % improvement of AIRPATH-selected over static-selected routes when
they differ (δ > 0): **{oracle_gain:.4f}%**

Positive values favor AIRPATH selection under the IDW-derived oracle.

## H–I. Walking vs motorbike and time-budget sensitivity

{_markdown_table(mode_summary)}

## J. Scientific interpretation

This experiment tests whether **future hourly pollution buckets** change
route-exposure estimates and constrained route selection relative to a
**static departure snapshot**, using the same candidate routes.

It does **not** claim minute-level PM2.5 prediction, medical benefit, or
road-measured truth.

## K. Limitations

1. Hourly forecast buckets only; no sub-hourly interpolation.
2. Development/exploratory protocol; previously exposed test partition unused.
3. Oracle exposure is IDW-derived from monitors, not roadside measurements.
4. Constant-speed ETA omits traffic, signals, and turn delay.
5. Pilot-area OSM graph and spatial support remain bounded.
6. Model C hyperparameters were frozen from the fairness ablation.
7. Exposure remains a PM×minutes proxy, not inhaled dose.

## Final decision

### {decision.classification}

{decision.rationale}

```json
{json.dumps(dict(decision.criteria), indent=2)}
```
"""


def generate_static_vs_arrival_outputs(
    *,
    clean_csv: str | Path = "data/processed/airquality_hcmc_clean.csv",
    fairness_predictions_csv: str | Path = (
        "data/processed/forecasting_fairness/fairness_predictions.csv"
    ),
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    output_directory: str | Path = "data/processed/static_vs_arrival_exposure",
    report_path: str | Path = "reports/static_vs_arrival_exposure.md",
    scenario_count: int = SCENARIO_COUNT,
    seed: int = RANDOM_SEED,
) -> dict[str, object]:
    clean = pd.read_csv(clean_csv, parse_dates=["date"], low_memory=False)
    fairness = pd.read_csv(
        fairness_predictions_csv,
        parse_dates=["origin_time", "target_time"],
        low_memory=False,
    )
    static_snapshot = load_static_snapshot(clean, ROUTE_DEPARTURE)
    airpath_forecasts = load_model_c_forecast_tables(fairness, FORECASTING_ORIGIN)
    oracle_tables = load_oracle_observed_tables(clean, FORECASTING_ORIGIN)
    network = load_network(network_path)
    scenarios = generate_od_scenarios(seed=seed, count_scenarios=scenario_count)

    route_rows: list[dict[str, object]] = []
    diversity_frames: list[pd.DataFrame] = []
    pairwise_frames: list[pd.DataFrame] = []
    segment_rows: list[dict[str, object]] = []

    for scenario in scenarios.itertuples():
        origin = (scenario.origin_latitude, scenario.origin_longitude)
        destination = (
            scenario.destination_latitude,
            scenario.destination_longitude,
        )
        for mode in ("walking", "motorbike"):
            routes = generate_diverse_candidates(
                network, origin, destination, mode
            )
            metadata, pairwise = candidate_diversity_rows(
                scenario.scenario_id, routes
            )
            diversity_frames.append(metadata)
            pairwise_frames.append(pairwise)
            metadata_lookup = metadata.set_index("route_id")
            for route in routes:
                segments = propagate_segment_etas(
                    network, route, ROUTE_DEPARTURE
                )
                static_records = compute_static_exposure(
                    scenario.scenario_id,
                    segments,
                    ROUTE_DEPARTURE,
                    static_snapshot,
                )
                airpath_records = compute_predicted_exposure(
                    scenario.scenario_id,
                    segments,
                    FORECASTING_ORIGIN,
                    airpath_forecasts,
                )
                # Relabel predicted pathway for this experiment's naming.
                airpath_records = [
                    replace(
                        record,
                        pipeline_mode="airpath_arrival_time_exposure",
                    )
                    for record in airpath_records
                ]
                oracle_records = compute_oracle_exposure(
                    scenario.scenario_id,
                    segments,
                    FORECASTING_ORIGIN,
                    oracle_tables,
                )
                for record in (*static_records, *airpath_records, *oracle_records):
                    segment_rows.append(asdict(record))
                route_rows.append(
                    summarize_dual_exposure(
                        route,
                        scenario.scenario_id,
                        static_records,
                        airpath_records,
                        oracle_records,
                        metadata_lookup.loc[route.route_id],
                    )
                )

    route_summary = pd.DataFrame(route_rows)
    ranking_rows, ranking_quality = compare_route_rankings(route_summary)
    selections = constrained_selection_comparison(route_summary)
    edge_cases = edge_case_summary(selections)
    mode_summary = mode_tolerance_summary(selections)
    decision = decide_arrival_evidence(selections, ranking_quality, edge_cases)
    diversity = pd.concat(diversity_frames, ignore_index=True)
    pairwise = pd.concat(pairwise_frames, ignore_index=True)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    scenarios.to_csv(output_directory / "od_scenarios.csv", index=False)
    diversity.to_csv(output_directory / "candidate_routes.csv", index=False)
    pairwise.to_csv(output_directory / "route_diversity_pairwise.csv", index=False)
    route_summary.to_csv(output_directory / "route_exposure_comparison.csv", index=False)
    pd.DataFrame(segment_rows).to_csv(
        output_directory / "segment_exposure_comparison.csv.gz",
        index=False,
        compression="gzip",
    )
    ranking_rows.to_csv(output_directory / "route_ranking_comparison.csv", index=False)
    ranking_quality.to_csv(
        output_directory / "ranking_quality.csv", index=False
    )
    selections.to_csv(
        output_directory / "constrained_selection_comparison.csv", index=False
    )
    edge_cases.to_csv(output_directory / "edge_case_summary.csv", index=False)
    mode_summary.to_csv(output_directory / "mode_tolerance_summary.csv", index=False)
    (output_directory / "evidence_decision.json").write_text(
        json.dumps(asdict(decision), indent=2), encoding="utf-8"
    )
    _plot_outputs(
        route_summary, ranking_quality, selections, mode_summary, output_directory
    )
    report_path.write_text(
        render_report(
            scenarios,
            route_summary,
            ranking_quality,
            selections,
            edge_cases,
            mode_summary,
            decision,
        ),
        encoding="utf-8",
    )
    return {
        "scenarios": scenarios,
        "route_summary": route_summary,
        "ranking_rows": ranking_rows,
        "ranking_quality": ranking_quality,
        "selections": selections,
        "edge_cases": edge_cases,
        "mode_summary": mode_summary,
        "decision": decision,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clean-csv", default="data/processed/airquality_hcmc_clean.csv"
    )
    parser.add_argument(
        "--fairness-predictions",
        default="data/processed/forecasting_fairness/fairness_predictions.csv",
    )
    parser.add_argument(
        "--network",
        default="data/processed/road_network/healthyair_pilot_osm.json.gz",
    )
    parser.add_argument(
        "--output-directory",
        default="data/processed/static_vs_arrival_exposure",
    )
    parser.add_argument(
        "--report", default="reports/static_vs_arrival_exposure.md"
    )
    parser.add_argument("--scenario-count", type=int, default=SCENARIO_COUNT)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_static_vs_arrival_outputs(
        clean_csv=arguments.clean_csv,
        fairness_predictions_csv=arguments.fairness_predictions,
        network_path=arguments.network,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
        scenario_count=arguments.scenario_count,
        seed=arguments.seed,
    )
    print(outputs["edge_cases"].to_string(index=False))
    print(outputs["mode_summary"].to_string(index=False))
    print(outputs["decision"])


if __name__ == "__main__":
    main()
