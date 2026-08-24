"""P0-2B: temporal robustness of static vs arrival-time exposure.

Development/exploratory only. Reuses P0-2A OD scenarios and C_xgboost_current_pm.
Does not modify raw data, spatial/forecasting definitions, or P0-2A artifacts.
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

from .eta_engine import propagate_segment_etas
from .exposure import (
    _kendall_tau_a,
    _spearman,
    compute_oracle_exposure,
    compute_predicted_exposure,
)
from .forecasting_fairness import MODEL_C
from .road_network import load_network
from .route_candidates import CandidateRoute
from .route_optimizer import (
    TIME_TOLERANCES_MINUTES,
    candidate_diversity_rows,
    generate_diverse_candidates,
)
from .spatial_estimation import STATION_BY_ID
from .static_vs_arrival_exposure import (
    EVALUATION_LABEL,
    EXPOSURE_UNIT,
    MATERIAL_RANK_SHIFT,
    SCENARIO_COUNT,
    compute_static_exposure,
    constrained_selection_comparison,
    decide_arrival_evidence,
    edge_case_summary,
    load_model_c_forecast_tables,
    load_oracle_observed_tables,
    load_static_snapshot,
    mode_tolerance_summary,
    summarize_dual_exposure,
)


RANDOM_SEED: Final[int] = 42
# Preferred clock times from the P0-2B brief.
PREFERRED_DEPARTURE_HOURS: Final[tuple[int, ...]] = (6, 8, 12, 17, 20)
# Feb 28 (P0-2A day) lacks complete Model C / observed coverage for 08:00 and 12:00.
# Feb 27 supports all five preferred clock times with intact +1/+2/+3h horizons.
ANALYSIS_DATE: Final[pd.Timestamp] = pd.Timestamp("2022-02-27")


@dataclass(frozen=True)
class DepartureSupport:
    departure_time: pd.Timestamp
    forecasting_origin: pd.Timestamp
    supported: bool
    exclusion_reason: str | None


@dataclass(frozen=True)
class TemporalGapDecision:
    classification: str
    rationale: str
    criteria: Mapping[str, object]
    strongest_departure_times: tuple[str, ...]
    weakest_departure_times: tuple[str, ...]
    gap1_conclusion_changed: bool


def forecasting_origin_for_departure(departure_time: object) -> pd.Timestamp:
    """Keep the P0-2A convention: origin is one hour before departure."""
    return pd.Timestamp(departure_time) - pd.Timedelta(hours=1)


def departure_is_supported(
    clean: pd.DataFrame,
    fairness_predictions: pd.DataFrame,
    departure_time: object,
) -> DepartureSupport:
    departure = pd.Timestamp(departure_time)
    origin = forecasting_origin_for_departure(departure)
    reason: str | None = None
    try:
        load_static_snapshot(clean, departure)
        load_model_c_forecast_tables(fairness_predictions, origin)
        load_oracle_observed_tables(clean, origin)
        supported = True
    except ValueError as error:
        supported = False
        reason = str(error)
    return DepartureSupport(
        departure_time=departure,
        forecasting_origin=origin,
        supported=supported,
        exclusion_reason=reason,
    )


def select_departure_times(
    clean: pd.DataFrame,
    fairness_predictions: pd.DataFrame,
    *,
    analysis_date: pd.Timestamp = ANALYSIS_DATE,
    preferred_hours: Sequence[int] = PREFERRED_DEPARTURE_HOURS,
) -> tuple[pd.DataFrame, list[DepartureSupport]]:
    rows: list[dict[str, object]] = []
    supported: list[DepartureSupport] = []
    for hour in preferred_hours:
        departure = analysis_date + pd.Timedelta(hours=int(hour))
        record = departure_is_supported(clean, fairness_predictions, departure)
        rows.append(
            {
                "preferred_clock_time": f"{hour:02d}:00",
                "analysis_date": analysis_date.date().isoformat(),
                "departure_time": record.departure_time.isoformat(),
                "forecasting_origin": record.forecasting_origin.isoformat(),
                "supported": record.supported,
                "exclusion_reason": record.exclusion_reason,
            }
        )
        if record.supported:
            supported.append(record)
    if not supported:
        raise RuntimeError("No preferred departure times are fully supported.")
    return pd.DataFrame(rows), supported


def compare_route_rankings_temporal(
    route_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking_rows: list[dict[str, object]] = []
    quality_rows: list[dict[str, object]] = []
    group_keys = ["departure_time", "scenario_id", "mode"]
    for keys, group in route_summary.groupby(group_keys, sort=True):
        departure_time, scenario_id, mode = keys
        static_order = group.sort_values(
            ["static_exposure_index", "route_id"]
        )["route_id"].tolist()
        airpath_order = group.sort_values(
            ["airpath_exposure_index", "route_id"]
        )["route_id"].tolist()
        static_rank = {
            route_id: index + 1 for index, route_id in enumerate(static_order)
        }
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
                    "departure_time": departure_time,
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
                "departure_time": departure_time,
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


def constrained_selection_temporal(
    route_summary: pd.DataFrame,
    tolerances: Sequence[float] = TIME_TOLERANCES_MINUTES,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for departure_time, group in route_summary.groupby("departure_time", sort=True):
        selected = constrained_selection_comparison(group, tolerances=tolerances)
        selected.insert(0, "departure_time", departure_time)
        frames.append(selected)
    return pd.concat(frames, ignore_index=True)


def departure_time_summary(
    selections: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    route_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for departure_time, group in selections.groupby("departure_time", sort=True):
        nontrivial = group.loc[group["delta_time_allowed_minutes"].gt(0)]
        differing = nontrivial.loc[nontrivial["selections_differ"]]
        quality = ranking_quality.loc[
            ranking_quality["departure_time"].eq(departure_time)
        ]
        exposure = route_summary.loc[
            route_summary["departure_time"].eq(departure_time)
        ]
        rows.append(
            {
                "departure_time": departure_time,
                "clock_time": pd.Timestamp(departure_time).strftime("%H:%M"),
                "scenario_mode_cases": int(
                    group[["scenario_id", "mode"]]
                    .drop_duplicates()
                    .shape[0]
                ),
                "mean_abs_pct_exposure_diff": float(
                    exposure[
                        "percentage_exposure_difference_airpath_vs_static"
                    ]
                    .abs()
                    .mean()
                ),
                "mean_spearman": float(
                    quality["spearman_static_vs_airpath"].mean()
                ),
                "mean_kendall": float(
                    quality["kendall_tau_a_static_vs_airpath"].mean()
                ),
                "mean_material_rank_change_pct": float(
                    quality[
                        "percentage_routes_with_material_rank_change"
                    ].mean()
                ),
                "nontrivial_selection_difference_rate": float(
                    nontrivial["selections_differ"].mean()
                ),
                "mean_oracle_pct_improvement_when_differ": (
                    float(
                        differing[
                            "oracle_percent_improvement_airpath_over_static"
                        ].mean()
                    )
                    if not differing.empty
                    else float("nan")
                ),
                "positive_oracle_gain_rate_when_differ": (
                    float(
                        differing[
                            "oracle_percent_improvement_airpath_over_static"
                        ]
                        .gt(0)
                        .mean()
                    )
                    if not differing.empty
                    else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("departure_time").reset_index(drop=True)


def decide_temporal_gap_evidence(
    departure_summary: pd.DataFrame,
    selections: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    *,
    p0_2a_differ_rate: float = 0.0633,
) -> TemporalGapDecision:
    nontrivial = selections.loc[selections["delta_time_allowed_minutes"].gt(0)]
    overall_differ = float(nontrivial["selections_differ"].mean())
    differing = nontrivial.loc[nontrivial["selections_differ"]]
    overall_oracle = (
        float(differing["oracle_percent_improvement_airpath_over_static"].mean())
        if not differing.empty
        else 0.0
    )
    overall_spearman = float(ranking_quality["spearman_static_vs_airpath"].mean())
    ranked = departure_summary.sort_values(
        [
            "nontrivial_selection_difference_rate",
            "mean_oracle_pct_improvement_when_differ",
        ],
        ascending=False,
    )
    strongest = tuple(ranked.head(2)["clock_time"].tolist())
    weakest = tuple(ranked.tail(2)["clock_time"].tolist()[::-1])
    max_differ = float(departure_summary["nontrivial_selection_difference_rate"].max())
    min_differ = float(departure_summary["nontrivial_selection_difference_rate"].min())
    conclusion_changed = abs(overall_differ - p0_2a_differ_rate) >= 0.10 or (
        overall_oracle >= 1.0 and overall_differ >= 0.25
    )

    base = decide_arrival_evidence(
        selections,
        ranking_quality,
        edge_case_summary(selections),
    )
    criteria = {
        **dict(base.criteria),
        "analysis_date": ANALYSIS_DATE.date().isoformat(),
        "overall_nontrivial_selection_difference_rate": overall_differ,
        "overall_mean_oracle_pct_improvement_when_differ": overall_oracle,
        "overall_mean_spearman": overall_spearman,
        "max_departure_differ_rate": max_differ,
        "min_departure_differ_rate": min_differ,
        "p0_2a_reference_differ_rate": p0_2a_differ_rate,
        "gap1_conclusion_changed_vs_p0_2a": conclusion_changed,
        "strongest_departure_times": list(strongest),
        "weakest_departure_times": list(weakest),
    }
    if base.classification.startswith("A."):
        classification = "A. STRONG EVIDENCE FOR ARRIVAL-TIME INFORMATION BENEFIT"
    elif overall_differ > 0:
        classification = "B. MIXED EVIDENCE"
    else:
        classification = "C. LITTLE / NO EVIDENCE"

    rationale = (
        f"Across supported departure times on {ANALYSIS_DATE.date()}, "
        f"nontrivial selection differences average {100 * overall_differ:.1f}% "
        f"(range {100 * min_differ:.1f}–{100 * max_differ:.1f}%). "
        f"Strongest clock times: {', '.join(strongest)}; "
        f"weakest: {', '.join(weakest)}. "
        f"Mean oracle gain when selections differ is {overall_oracle:.2f}%. "
        + (
            "The pooled Gap 1 conclusion changes relative to single-time P0-2A."
            if conclusion_changed
            else "The pooled Gap 1 conclusion remains aligned with MIXED/weak evidence from P0-2A."
        )
    )
    return TemporalGapDecision(
        classification=classification,
        rationale=rationale,
        criteria=criteria,
        strongest_departure_times=strongest,
        weakest_departure_times=weakest,
        gap1_conclusion_changed=conclusion_changed,
    )


def evaluate_departure(
    *,
    scenarios: pd.DataFrame,
    routes_by_key: Mapping[tuple[str, str], list[CandidateRoute]],
    diversity_by_key: Mapping[tuple[str, str], pd.DataFrame],
    network,
    clean: pd.DataFrame,
    fairness: pd.DataFrame,
    departure: DepartureSupport,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    static_snapshot = load_static_snapshot(clean, departure.departure_time)
    airpath_forecasts = load_model_c_forecast_tables(
        fairness, departure.forecasting_origin
    )
    oracle_tables = load_oracle_observed_tables(clean, departure.forecasting_origin)
    route_rows: list[dict[str, object]] = []
    segment_rows: list[dict[str, object]] = []

    for scenario in scenarios.itertuples():
        for mode in ("walking", "motorbike"):
            key = (scenario.scenario_id, mode)
            routes = routes_by_key[key]
            metadata_lookup = diversity_by_key[key].set_index("route_id")
            for route in routes:
                segments = propagate_segment_etas(
                    network, route, departure.departure_time
                )
                static_records = compute_static_exposure(
                    scenario.scenario_id,
                    segments,
                    departure.departure_time,
                    static_snapshot,
                )
                airpath_records = [
                    replace(record, pipeline_mode="airpath_arrival_time_exposure")
                    for record in compute_predicted_exposure(
                        scenario.scenario_id,
                        segments,
                        departure.forecasting_origin,
                        airpath_forecasts,
                    )
                ]
                oracle_records = compute_oracle_exposure(
                    scenario.scenario_id,
                    segments,
                    departure.forecasting_origin,
                    oracle_tables,
                )
                for record in (*static_records, *airpath_records, *oracle_records):
                    payload = asdict(record)
                    payload["departure_time"] = departure.departure_time.isoformat()
                    payload["forecasting_origin"] = (
                        departure.forecasting_origin.isoformat()
                    )
                    segment_rows.append(payload)
                summary = summarize_dual_exposure(
                    route,
                    scenario.scenario_id,
                    static_records,
                    airpath_records,
                    oracle_records,
                    metadata_lookup.loc[route.route_id],
                )
                summary["departure_time"] = departure.departure_time.isoformat()
                summary["forecasting_origin"] = (
                    departure.forecasting_origin.isoformat()
                )
                summary["clock_time"] = departure.departure_time.strftime("%H:%M")
                route_rows.append(summary)
    return pd.DataFrame(route_rows), segment_rows


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    if frame.empty:
        return "_No observations._"
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _plot_outputs(
    departure_summary: pd.DataFrame,
    mode_summary: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    output_directory: Path,
) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.plot(
        departure_summary["clock_time"],
        100
        * departure_summary["nontrivial_selection_difference_rate"],
        marker="o",
        label="selection differ %",
    )
    axis.plot(
        departure_summary["clock_time"],
        departure_summary["mean_oracle_pct_improvement_when_differ"],
        marker="s",
        label="oracle % gain when differ",
    )
    axis.set(
        xlabel="Departure clock time",
        ylabel="Percent",
        title="Departure-time sensitivity of Gap 1 signal",
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "departure_time_sensitivity.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    axis.plot(
        departure_summary["clock_time"],
        departure_summary["mean_spearman"],
        marker="o",
    )
    axis.set(
        xlabel="Departure clock time",
        ylabel="Mean Spearman(static, AIRPATH)",
        title="Ranking agreement by departure time",
        ylim=(-0.05, 1.05),
    )
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "ranking_by_departure.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 5))
    for mode, group in mode_summary.groupby("mode", sort=True):
        pivot = (
            group.groupby("delta_time_allowed_minutes", as_index=False)[
                "percentage_selections_differ"
            ]
            .mean()
        )
        axis.plot(
            pivot["delta_time_allowed_minutes"],
            pivot["percentage_selections_differ"],
            marker="o",
            label=mode,
        )
    axis.set(
        xlabel="Additional travel time allowed (minutes)",
        ylabel="Percentage of selections that differ",
        title="Tolerance sensitivity pooled across departure times",
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "tolerance_sensitivity.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    display = (
        ranking_quality.groupby("departure_time", as_index=False)[
            "percentage_routes_with_material_rank_change"
        ]
        .mean()
        .assign(
            clock_time=lambda frame: pd.to_datetime(frame["departure_time"]).dt.strftime(
                "%H:%M"
            )
        )
    )
    axis.bar(display["clock_time"], display["percentage_routes_with_material_rank_change"])
    axis.set(
        xlabel="Departure clock time",
        ylabel="Mean % routes with material rank change",
        title="Material ranking changes by departure time",
    )
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output_directory / "material_rank_by_departure.png", dpi=180)
    plt.close(figure)


def render_report(
    support_table: pd.DataFrame,
    departure_summary: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    selections: pd.DataFrame,
    mode_summary: pd.DataFrame,
    edge_cases: pd.DataFrame,
    decision: TemporalGapDecision,
    n_scenarios: int,
) -> str:
    nontrivial = selections.loc[selections["delta_time_allowed_minutes"].gt(0)]
    n_cases = int(
        selections[["departure_time", "scenario_id", "mode"]]
        .drop_duplicates()
        .shape[0]
    )
    return f"""# AIRPATH-AI P0-2B — temporal robustness of Gap 1

## Status

**Development / exploratory only.** This experiment does not claim untouched
final-test performance. It reuses the P0-2A OD scenarios and the selected
forecaster `{MODEL_C}`. P0-2A artifacts are not modified.

AIRPATH exposure remains:

**hourly forecast-bucket-aware arrival-time exposure**

No sub-hourly interpolation is performed.

## Departure-time support

Preferred clock times: {", ".join(f"{hour:02d}:00" for hour in PREFERRED_DEPARTURE_HOURS)}.

Analysis date: **{ANALYSIS_DATE.date()}**.

P0-2A used `2022-02-28 06:00`. On that calendar day, `08:00` and `12:00` cannot
support complete +1/+2/+3h Model C / observed station tables (station 4 gaps).
`2022-02-27` retains all five preferred clock times with intact horizons, so the
temporal comparison uses that day rather than mixing incomplete Feb-28 hours.

{_markdown_table(support_table)}

Forecasting origin remains one hour before each departure, matching P0-2A.

## A. Case count

- OD scenarios: **{n_scenarios}**
- Modes: walking, motorbike
- Supported departure times: **{len(departure_summary)}**
- OD × mode × departure-time cases: **{n_cases}**
- Nontrivial budget rows (δ > 0): **{len(nontrivial)}**

## B. Ranking correlations

Mean Spearman by departure time:

{_markdown_table(departure_summary[
    ["clock_time", "mean_spearman", "mean_kendall", "mean_material_rank_change_pct"]
])}

Pooled mean Spearman: **{float(ranking_quality["spearman_static_vs_airpath"].mean()):.4f}**

## C. Route-selection differences

{_markdown_table(departure_summary[
    [
        "clock_time",
        "nontrivial_selection_difference_rate",
        "mean_oracle_pct_improvement_when_differ",
        "positive_oracle_gain_rate_when_differ",
    ]
])}

Edge cases by tolerance (pooled over departure times):

{_markdown_table(edge_cases)}

## D. Oracle improvement

Oracle exposure remains IDW-derived from monitors and is **not** road-measured
ground truth. Values above are mean percent improvement of AIRPATH-selected
routes over static-selected routes **when selections differ**.

## E. Departure-time sensitivity

Strongest clock times: **{", ".join(decision.strongest_departure_times)}**

Weakest clock times: **{", ".join(decision.weakest_departure_times)}**

{_markdown_table(departure_summary)}

## F. Tolerance sensitivity

{_markdown_table(mode_summary)}

## G. Updated Gap 1 conclusion

### {decision.classification}

{decision.rationale}

Gap 1 conclusion changed vs single-time P0-2A: **{decision.gap1_conclusion_changed}**

```json
{json.dumps(dict(decision.criteria), indent=2)}
```

## H. Implications for the final paper

1. A single morning departure is not sufficient to claim Gap 1 benefit.
2. Temporal replication across clock times is required before product claims.
3. If signals remain weak across times of day, AIRPATH should emphasize
   transparency of alternatives rather than asserting large arrival-time gains.
4. Hourly buckets remain a binding scientific limitation.

## Limitations

1. Hourly forecasting buckets only.
2. Constant-speed ETA omits traffic and signals.
3. No road-level PM2.5 measurements.
4. Oracle exposure is IDW-derived.
5. Pilot-area OSM / station support remains bounded.
6. Calendar day shifted from P0-2A to obtain complete preferred clock coverage.
7. Development/exploratory protocol; previously exposed test partition unused.
"""


def generate_temporal_gap_outputs(
    *,
    clean_csv: str | Path = "data/processed/airquality_hcmc_clean.csv",
    fairness_predictions_csv: str | Path = (
        "data/processed/forecasting_fairness/fairness_predictions.csv"
    ),
    scenarios_csv: str | Path = (
        "data/processed/static_vs_arrival_exposure/od_scenarios.csv"
    ),
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    output_directory: str | Path = "data/processed/temporal_gap_analysis",
    report_path: str | Path = "reports/temporal_gap_analysis.md",
) -> dict[str, object]:
    clean = pd.read_csv(clean_csv, parse_dates=["date"], low_memory=False)
    fairness = pd.read_csv(
        fairness_predictions_csv,
        parse_dates=["origin_time", "target_time"],
        low_memory=False,
    )
    scenarios = pd.read_csv(scenarios_csv)
    if len(scenarios) != SCENARIO_COUNT:
        raise ValueError(
            f"Expected {SCENARIO_COUNT} P0-2A OD scenarios, found {len(scenarios)}."
        )
    support_table, supported = select_departure_times(clean, fairness)
    network = load_network(network_path)

    routes_by_key: dict[tuple[str, str], list[CandidateRoute]] = {}
    diversity_by_key: dict[tuple[str, str], pd.DataFrame] = {}
    diversity_frames: list[pd.DataFrame] = []
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
            metadata, _ = candidate_diversity_rows(scenario.scenario_id, routes)
            key = (scenario.scenario_id, mode)
            routes_by_key[key] = routes
            diversity_by_key[key] = metadata
            diversity_frames.append(
                metadata.assign(scenario_id=scenario.scenario_id, mode=mode)
            )

    route_frames: list[pd.DataFrame] = []
    segment_paths: list[str] = []
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    for departure in supported:
        route_frame, segments = evaluate_departure(
            scenarios=scenarios,
            routes_by_key=routes_by_key,
            diversity_by_key=diversity_by_key,
            network=network,
            clean=clean,
            fairness=fairness,
            departure=departure,
        )
        route_frames.append(route_frame)
        clock = departure.departure_time.strftime("%H%M")
        segment_path = (
            output_directory / f"segment_exposure_comparison_{clock}.csv.gz"
        )
        pd.DataFrame(segments).to_csv(
            segment_path, index=False, compression="gzip"
        )
        segment_paths.append(segment_path.name)

    route_summary = pd.concat(route_frames, ignore_index=True)
    ranking_rows, ranking_quality = compare_route_rankings_temporal(route_summary)
    selections = constrained_selection_temporal(route_summary)
    edge_cases = edge_case_summary(selections)
    # mode×tolerance pooled across departure times
    mode_summary = mode_tolerance_summary(
        selections.drop(columns=["departure_time"], errors="ignore")
    )
    # Also emit mode×tolerance×departure for detail
    mode_departure_rows: list[pd.DataFrame] = []
    for departure_time, group in selections.groupby("departure_time", sort=True):
        summary = mode_tolerance_summary(group)
        summary.insert(0, "departure_time", departure_time)
        mode_departure_rows.append(summary)
    mode_departure_summary = pd.concat(mode_departure_rows, ignore_index=True)
    departure_summary = departure_time_summary(
        selections, ranking_quality, route_summary
    )
    decision = decide_temporal_gap_evidence(
        departure_summary, selections, ranking_quality
    )

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    support_table.to_csv(output_directory / "departure_support.csv", index=False)
    scenarios.to_csv(output_directory / "od_scenarios.csv", index=False)
    pd.concat(diversity_frames, ignore_index=True).to_csv(
        output_directory / "candidate_routes.csv", index=False
    )
    route_summary.to_csv(
        output_directory / "route_exposure_comparison.csv", index=False
    )
    (output_directory / "segment_exposure_files.json").write_text(
        json.dumps({"files": segment_paths}, indent=2), encoding="utf-8"
    )
    ranking_rows.to_csv(
        output_directory / "route_ranking_comparison.csv", index=False
    )
    ranking_quality.to_csv(output_directory / "ranking_quality.csv", index=False)
    selections.to_csv(
        output_directory / "constrained_selection_comparison.csv", index=False
    )
    edge_cases.to_csv(output_directory / "edge_case_summary.csv", index=False)
    mode_summary.to_csv(output_directory / "mode_tolerance_summary.csv", index=False)
    mode_departure_summary.to_csv(
        output_directory / "mode_tolerance_departure_summary.csv", index=False
    )
    departure_summary.to_csv(
        output_directory / "departure_time_summary.csv", index=False
    )
    (output_directory / "evidence_decision.json").write_text(
        json.dumps(asdict(decision), indent=2), encoding="utf-8"
    )
    _plot_outputs(
        departure_summary, mode_departure_summary, ranking_quality, output_directory
    )
    report_path.write_text(
        render_report(
            support_table,
            departure_summary,
            ranking_quality,
            selections,
            mode_departure_summary,
            edge_cases,
            decision,
            len(scenarios),
        ),
        encoding="utf-8",
    )
    return {
        "support_table": support_table,
        "scenarios": scenarios,
        "route_summary": route_summary,
        "ranking_quality": ranking_quality,
        "selections": selections,
        "departure_summary": departure_summary,
        "mode_summary": mode_summary,
        "mode_departure_summary": mode_departure_summary,
        "edge_cases": edge_cases,
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
        "--scenarios-csv",
        default="data/processed/static_vs_arrival_exposure/od_scenarios.csv",
    )
    parser.add_argument(
        "--network",
        default="data/processed/road_network/healthyair_pilot_osm.json.gz",
    )
    parser.add_argument(
        "--output-directory", default="data/processed/temporal_gap_analysis"
    )
    parser.add_argument("--report", default="reports/temporal_gap_analysis.md")
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_temporal_gap_outputs(
        clean_csv=arguments.clean_csv,
        fairness_predictions_csv=arguments.fairness_predictions,
        scenarios_csv=arguments.scenarios_csv,
        network_path=arguments.network,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
    )
    print(outputs["support_table"].to_string(index=False))
    print(outputs["departure_summary"].to_string(index=False))
    print(outputs["decision"])


if __name__ == "__main__":
    main()
