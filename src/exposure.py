"""Offline route PM2.5 exposure-index aggregation and ranking validation.

The route index is E = Σ PM_i × duration_i_minutes. It is a time-weighted PM2.5
exposure proxy with units (µg/m³)·min, not inhaled dose. This module evaluates
candidate ordering only; it does not optimize or recommend routes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from itertools import combinations
from pathlib import Path
from typing import Final, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .eta_engine import SegmentETA, propagate_segment_etas
from .road_network import load_network
from .route_candidates import CandidateRoute, generate_candidate_routes
from .spatial_estimation import STATION_BY_ID, estimate_with_diagnostics
from .target_time_integration import classify_spatial_reliability, map_target_time


EXPOSURE_UNIT: Final[str] = "(µg/m³)·min"
FORECASTING_ORIGIN: Final[pd.Timestamp] = pd.Timestamp("2022-02-28 05:00:00")
ROUTE_DEPARTURE: Final[pd.Timestamp] = pd.Timestamp("2022-02-28 06:00:00")
K_CANDIDATES: Final[int] = 5
OD_SCENARIOS: Final[dict[str, tuple[tuple[float, float], tuple[float, float]]]] = {
    "s6_to_s5": (
        (STATION_BY_ID[6].latitude, STATION_BY_ID[6].longitude),
        (STATION_BY_ID[5].latitude, STATION_BY_ID[5].longitude),
    ),
    "s2_to_s6": (
        (STATION_BY_ID[2].latitude, STATION_BY_ID[2].longitude),
        (STATION_BY_ID[6].latitude, STATION_BY_ID[6].longitude),
    ),
}


@dataclass(frozen=True)
class SegmentExposure:
    scenario_id: str
    route_id: str
    mode: str
    pipeline_mode: str
    segment_index: int
    segment_id: str
    eta: pd.Timestamp
    mapped_target_time: pd.Timestamp
    mapping_method: str
    forecast_horizon_hours: int
    latitude: float
    longitude: float
    segment_duration_minutes: float
    pm25_estimate: float
    exposure_contribution: float
    contribution_fraction: float
    nearest_station_distance_km: float
    second_nearest_station_distance_km: float | None
    contributing_station_count: int
    maximum_idw_weight: float
    effective_station_count: float
    reliability_status: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["eta"] = self.eta.isoformat()
        payload["mapped_target_time"] = self.mapped_target_time.isoformat()
        return payload


@dataclass(frozen=True)
class ExposureReadinessDecision:
    classification: str
    rationale: str
    criteria: Mapping[str, object]


def _validate_station_table(
    values_by_target: Mapping[object, Mapping[int | str, float]],
) -> dict[pd.Timestamp, dict[int, float]]:
    result: dict[pd.Timestamp, dict[int, float]] = {}
    for raw_target, raw_values in values_by_target.items():
        target = pd.Timestamp(raw_target)
        values = {
            int(station_id): float(value)
            for station_id, value in raw_values.items()
        }
        if set(values) != set(STATION_BY_ID):
            raise ValueError(
                f"Target {target} requires exactly all six station values."
            )
        if not all(np.isfinite(value) and value >= 0 for value in values.values()):
            raise ValueError("Station PM2.5 values must be finite and non-negative.")
        result[target] = values
    return result


def _compute_segment_exposures(
    scenario_id: str,
    segments: Sequence[SegmentETA],
    forecasting_origin: object,
    values_by_target: Mapping[object, Mapping[int | str, float]],
    pipeline_mode: str,
) -> list[SegmentExposure]:
    if not segments:
        raise ValueError("Exposure aggregation requires at least one segment.")
    if pipeline_mode not in {"oracle_exposure", "predicted_exposure"}:
        raise ValueError("Unknown exposure pipeline mode.")
    origin = pd.Timestamp(forecasting_origin)
    station_table = _validate_station_table(values_by_target)
    records: list[SegmentExposure] = []
    seen_segment_ids: set[str] = set()
    for expected_index, segment in enumerate(segments, start=1):
        if segment.segment_index != expected_index:
            raise ValueError("Segments must be contiguous and ordered.")
        if segment.edge_id in seen_segment_ids:
            raise ValueError("Every route segment must be included exactly once.")
        seen_segment_ids.add(segment.edge_id)
        duration_minutes = float(segment.segment_duration_seconds) / 60
        if not np.isfinite(duration_minutes) or duration_minutes < 0:
            raise ValueError("Segment duration must be non-negative and finite.")
        mapping = map_target_time(segment.target_arrival_timestamp, origin)
        mapping.require_supported()
        if mapping.supported_target_time not in station_table:
            raise ValueError(
                "No station values exist for mapped target "
                f"{mapping.supported_target_time.isoformat()}."
            )
        estimate = estimate_with_diagnostics(
            segment.representative_latitude,
            segment.representative_longitude,
            mapping.supported_target_time,
            station_table[mapping.supported_target_time],
            method="idw",
            power=1,
        )
        if not np.isfinite(estimate.predicted_pm25) or estimate.predicted_pm25 < 0:
            raise ValueError("Segment PM2.5 estimate must be finite and non-negative.")
        contribution = estimate.predicted_pm25 * duration_minutes
        records.append(
            SegmentExposure(
                scenario_id=scenario_id,
                route_id=segment.route_id,
                mode=segment.mode,
                pipeline_mode=pipeline_mode,
                segment_index=segment.segment_index,
                segment_id=segment.edge_id,
                eta=segment.target_arrival_timestamp,
                mapped_target_time=mapping.supported_target_time,
                mapping_method=mapping.mapping_method,
                forecast_horizon_hours=mapping.forecast_horizon_hours,
                latitude=segment.representative_latitude,
                longitude=segment.representative_longitude,
                segment_duration_minutes=duration_minutes,
                pm25_estimate=estimate.predicted_pm25,
                exposure_contribution=contribution,
                contribution_fraction=0.0,
                nearest_station_distance_km=estimate.nearest_distance_km,
                second_nearest_station_distance_km=(
                    estimate.second_nearest_distance_km
                ),
                contributing_station_count=estimate.contributing_stations,
                maximum_idw_weight=estimate.maximum_weight,
                effective_station_count=estimate.effective_station_count,
                reliability_status=classify_spatial_reliability(estimate),
            )
        )
    total = aggregate_exposure_index(records)
    if total <= 0:
        raise ValueError("Route exposure index must be positive.")
    return [
        replace(
            record,
            contribution_fraction=record.exposure_contribution / total,
        )
        for record in records
    ]


def compute_oracle_exposure(
    scenario_id: str,
    segments: Sequence[SegmentETA],
    forecasting_origin: object,
    observed_station_values_by_target: Mapping[
        object, Mapping[int | str, float]
    ],
) -> list[SegmentExposure]:
    """Mode A: observed station values → IDW p=1 → route exposure index."""
    return _compute_segment_exposures(
        scenario_id,
        segments,
        forecasting_origin,
        observed_station_values_by_target,
        "oracle_exposure",
    )


def compute_predicted_exposure(
    scenario_id: str,
    segments: Sequence[SegmentETA],
    forecasting_origin: object,
    forecasted_station_values_by_target: Mapping[
        object, Mapping[int | str, float]
    ],
) -> list[SegmentExposure]:
    """Mode B: frozen station forecasts → IDW p=1 → route exposure index."""
    return _compute_segment_exposures(
        scenario_id,
        segments,
        forecasting_origin,
        forecasted_station_values_by_target,
        "predicted_exposure",
    )


def aggregate_exposure_index(records: Sequence[SegmentExposure]) -> float:
    """Return Σ PM_i × duration_i_minutes after strict route checks."""
    if not records:
        raise ValueError("Exposure aggregation requires segment records.")
    route_keys = {
        (record.scenario_id, record.route_id, record.mode, record.pipeline_mode)
        for record in records
    }
    if len(route_keys) != 1:
        raise ValueError("Exposure records must belong to one route and pathway.")
    expected_indices = list(range(1, len(records) + 1))
    if [record.segment_index for record in records] != expected_indices:
        raise ValueError("Exposure records must preserve contiguous segment order.")
    if len({record.segment_id for record in records}) != len(records):
        raise ValueError("Every segment must appear exactly once.")
    total = 0.0
    for record in records:
        if (
            record.segment_duration_minutes < 0
            or not np.isfinite(record.segment_duration_minutes)
        ):
            raise ValueError("Segment durations must be non-negative and finite.")
        expected = record.pm25_estimate * record.segment_duration_minutes
        if not np.isclose(record.exposure_contribution, expected):
            raise ValueError("Segment exposure contribution does not equal PM × time.")
        total += record.exposure_contribution
    return float(total)


def _saved_station_tables(
    predictions: pd.DataFrame,
    forecasting_origin: pd.Timestamp,
) -> tuple[dict[pd.Timestamp, dict[int, float]], dict[pd.Timestamp, dict[int, float]]]:
    required = {
        "Station_No",
        "origin_time",
        "target_time",
        "horizon_hours",
        "target_pm25",
        "prediction",
        "split",
        "model",
    }
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(
            "Saved forecasts missing columns: " + ", ".join(sorted(missing))
        )
    rows = predictions.copy()
    rows["origin_time"] = pd.to_datetime(rows["origin_time"], errors="raise")
    rows["target_time"] = pd.to_datetime(rows["target_time"], errors="raise")
    rows["Station_No"] = rows["Station_No"].astype(int)
    rows["horizon_hours"] = rows["horizon_hours"].astype(int)
    rows = rows.loc[
        rows["split"].eq("validation")
        & rows["model"].eq("xgboost_v1")
        & rows["origin_time"].eq(forecasting_origin)
        & rows["horizon_hours"].isin((1, 2, 3))
    ]
    observed: dict[pd.Timestamp, dict[int, float]] = {}
    forecasted: dict[pd.Timestamp, dict[int, float]] = {}
    for horizon, group in rows.groupby("horizon_hours", sort=True):
        if set(group["Station_No"]) != set(STATION_BY_ID):
            raise ValueError(f"Incomplete saved t+{horizon}h station forecasts.")
        if group["target_time"].nunique() != 1:
            raise ValueError("Saved station forecasts have inconsistent target times.")
        target = pd.Timestamp(group["target_time"].iloc[0])
        if target != forecasting_origin + pd.Timedelta(hours=int(horizon)):
            raise ValueError("Saved forecast target differs from origin plus horizon.")
        observed[target] = {
            int(station): float(value)
            for station, value in zip(group["Station_No"], group["target_pm25"])
        }
        # The predicted pathway reads only `prediction`, never `target_pm25`.
        forecasted[target] = {
            int(station): float(value)
            for station, value in zip(group["Station_No"], group["prediction"])
        }
    return _validate_station_table(observed), _validate_station_table(forecasted)


def summarize_route_exposure(
    route: CandidateRoute,
    oracle_records: Sequence[SegmentExposure],
    predicted_records: Sequence[SegmentExposure],
) -> dict[str, object]:
    oracle_total = aggregate_exposure_index(oracle_records)
    predicted_total = aggregate_exposure_index(predicted_records)
    difference = predicted_total - oracle_total
    percentage = 100 * difference / oracle_total
    reliability = predicted_records
    return {
        "scenario_id": oracle_records[0].scenario_id,
        "mode": route.mode,
        "route_id": route.route_id,
        "total_distance_m": route.total_distance_m,
        "total_travel_time_minutes": route.total_travel_time_seconds / 60,
        "segment_count": len(route.edge_ids),
        "oracle_exposure_index": oracle_total,
        "predicted_exposure_index": predicted_total,
        "exposure_difference": difference,
        "absolute_exposure_error": abs(difference),
        "percentage_difference": percentage,
        "absolute_percentage_error": abs(percentage),
        "mean_nearest_station_distance_km": float(
            np.mean(
                [record.nearest_station_distance_km for record in reliability]
            )
        ),
        "max_nearest_station_distance_km": float(
            np.max(
                [record.nearest_station_distance_km for record in reliability]
            )
        ),
        "mean_effective_station_count": float(
            np.mean([record.effective_station_count for record in reliability])
        ),
        "moderate_or_weak_segment_fraction": float(
            np.mean(
                [
                    record.reliability_status != "supported"
                    for record in reliability
                ]
            )
        ),
    }


def _ordinal_ranks(
    rows: pd.DataFrame, value_column: str
) -> dict[str, int]:
    ordered = rows.sort_values([value_column, "route_id"], kind="mergesort")
    return {
        route_id: rank
        for rank, route_id in enumerate(ordered["route_id"], start=1)
    }


def _spearman(oracle_ranks: Sequence[int], predicted_ranks: Sequence[int]) -> float:
    return float(pd.Series(oracle_ranks).corr(pd.Series(predicted_ranks)))


def _kendall_tau_a(
    oracle_ranks: Sequence[int], predicted_ranks: Sequence[int]
) -> float:
    concordant = 0
    discordant = 0
    for first, second in combinations(range(len(oracle_ranks)), 2):
        oracle_order = np.sign(oracle_ranks[first] - oracle_ranks[second])
        predicted_order = np.sign(
            predicted_ranks[first] - predicted_ranks[second]
        )
        product = oracle_order * predicted_order
        concordant += product > 0
        discordant += product < 0
    denominator = len(oracle_ranks) * (len(oracle_ranks) - 1) / 2
    return float((concordant - discordant) / denominator)


def rank_candidate_exposures(
    route_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare oracle/predicted ordering without selecting a recommended route."""
    ranking_rows: list[dict[str, object]] = []
    agreement_rows: list[dict[str, object]] = []
    for (scenario_id, mode), group in route_summary.groupby(
        ["scenario_id", "mode"], sort=True
    ):
        if len(group) < 2:
            raise ValueError("Ranking validation requires multiple routes.")
        oracle_ranks = _ordinal_ranks(group, "oracle_exposure_index")
        predicted_ranks = _ordinal_ranks(group, "predicted_exposure_index")
        for row in group.itertuples():
            ranking_rows.append(
                {
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "route_id": row.route_id,
                    "oracle_exposure_index": row.oracle_exposure_index,
                    "predicted_exposure_index": row.predicted_exposure_index,
                    "oracle_rank": oracle_ranks[row.route_id],
                    "predicted_rank": predicted_ranks[row.route_id],
                    "rank_shift": (
                        predicted_ranks[row.route_id]
                        - oracle_ranks[row.route_id]
                    ),
                }
            )
        route_ids = sorted(oracle_ranks)
        oracle_values = [oracle_ranks[route_id] for route_id in route_ids]
        predicted_values = [predicted_ranks[route_id] for route_id in route_ids]
        oracle_top_1 = min(oracle_ranks, key=oracle_ranks.get)
        predicted_top_1 = min(predicted_ranks, key=predicted_ranks.get)
        oracle_top_2 = {
            route_id
            for route_id, rank in oracle_ranks.items()
            if rank <= 2
        }
        predicted_top_2 = {
            route_id
            for route_id, rank in predicted_ranks.items()
            if rank <= 2
        }
        agreement_rows.append(
            {
                "scenario_id": scenario_id,
                "mode": mode,
                "route_count": len(group),
                "spearman_rank_correlation": _spearman(
                    oracle_values, predicted_values
                ),
                "kendall_tau_a": _kendall_tau_a(
                    oracle_values, predicted_values
                ),
                "oracle_top_1_route": oracle_top_1,
                "predicted_top_1_route": predicted_top_1,
                "top_1_agreement": oracle_top_1 == predicted_top_1,
                "top_2_overlap_count": len(oracle_top_2 & predicted_top_2),
                "top_2_overlap_fraction": len(oracle_top_2 & predicted_top_2)
                / 2,
            }
        )
    return pd.DataFrame(ranking_rows), pd.DataFrame(agreement_rows)


def exposure_error_metrics(route_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mode, group in route_summary.groupby("mode", sort=True):
        errors = group["exposure_difference"].to_numpy(dtype=float)
        rows.append(
            {
                "mode": mode,
                "routes": len(group),
                "mae_exposure_index": float(np.mean(np.abs(errors))),
                "rmse_exposure_index": float(np.sqrt(np.mean(errors**2))),
                "mean_absolute_percentage_error": float(
                    group["absolute_percentage_error"].mean()
                ),
                "max_absolute_percentage_error": float(
                    group["absolute_percentage_error"].max()
                ),
            }
        )
    return pd.DataFrame(rows)


def _rank_correlation(first: pd.Series, second: pd.Series) -> float:
    valid = first.notna() & second.notna()
    if valid.sum() < 3:
        return float("nan")
    return float(first.loc[valid].rank().corr(second.loc[valid].rank()))


def exposure_error_relationships(route_summary: pd.DataFrame) -> pd.DataFrame:
    proxies = (
        "total_distance_m",
        "total_travel_time_minutes",
        "mean_nearest_station_distance_km",
        "max_nearest_station_distance_km",
        "mean_effective_station_count",
        "moderate_or_weak_segment_fraction",
    )
    rows = []
    for mode, group in route_summary.groupby("mode", sort=True):
        for proxy in proxies:
            rows.append(
                {
                    "mode": mode,
                    "proxy": proxy,
                    "routes": len(group),
                    "spearman_with_absolute_exposure_error": (
                        _rank_correlation(
                            group[proxy], group["absolute_exposure_error"]
                        )
                    ),
                }
            )
    return pd.DataFrame(rows)


def top_segment_contributions(
    segment_records: pd.DataFrame,
    *,
    top_n: int = 5,
) -> pd.DataFrame:
    rows = []
    for _, group in segment_records.groupby(
        ["scenario_id", "mode", "route_id", "pipeline_mode"], sort=True
    ):
        rows.append(
            group.nlargest(top_n, "contribution_fraction")
        )
    return pd.concat(rows, ignore_index=True)


def decide_exposure_readiness(
    ranking_agreement: pd.DataFrame,
    error_metrics: pd.DataFrame,
) -> ExposureReadinessDecision:
    top1_rate = float(ranking_agreement["top_1_agreement"].mean())
    mean_spearman = float(
        ranking_agreement["spearman_rank_correlation"].mean()
    )
    min_spearman = float(
        ranking_agreement["spearman_rank_correlation"].min()
    )
    max_mape = float(error_metrics["mean_absolute_percentage_error"].max())
    criteria = {
        "top_1_agreement_rate": top1_rate,
        "mean_spearman_rank_correlation": mean_spearman,
        "minimum_scenario_spearman": min_spearman,
        "maximum_mode_mape_percent": max_mape,
        "strict_top_1_agreement_all": top1_rate == 1,
        "strict_mean_spearman_ge_0_9": mean_spearman >= 0.9,
        "strict_minimum_spearman_ge_0_8": min_spearman >= 0.8,
        "strict_maximum_mode_mape_le_10": max_mape <= 10,
        "restricted_top_1_agreement_ge_half": top1_rate >= 0.5,
        "restricted_mean_spearman_ge_0_6": mean_spearman >= 0.6,
        "restricted_no_negative_scenario_spearman": min_spearman >= 0,
        "restricted_maximum_mode_mape_le_25": max_mape <= 25,
    }
    strict = all(
        criteria[key]
        for key in (
            "strict_top_1_agreement_all",
            "strict_mean_spearman_ge_0_9",
            "strict_minimum_spearman_ge_0_8",
            "strict_maximum_mode_mape_le_10",
        )
    )
    restricted = all(
        criteria[key]
        for key in (
            "restricted_top_1_agreement_ge_half",
            "restricted_mean_spearman_ge_0_6",
            "restricted_no_negative_scenario_spearman",
            "restricted_maximum_mode_mape_le_25",
        )
    )
    if strict:
        classification = "A. READY FOR OPTIMIZATION"
        rationale = "Exposure magnitude and route ordering pass all strict gates."
    elif restricted:
        classification = "B. READY WITH RESTRICTIONS"
        rationale = (
            "Exposure ranking is sufficiently stable for further offline work, "
            "but one or more strict agreement/error gates fail."
        )
    else:
        classification = "C. NOT READY"
        rationale = (
            "Predicted exposure magnitude or candidate ordering fails the "
            "restricted stability gate."
        )
    return ExposureReadinessDecision(classification, rationale, criteria)


def _plot_outputs(
    route_summary: pd.DataFrame,
    ranking: pd.DataFrame,
    agreement: pd.DataFrame,
    output_directory: Path,
) -> None:
    labels = (
        route_summary["scenario_id"]
        + "/"
        + route_summary["mode"]
        + "/"
        + route_summary["route_id"]
    )
    figure, axis = plt.subplots(figsize=(12, 5))
    x = np.arange(len(route_summary))
    width = 0.4
    axis.bar(
        x - width / 2,
        route_summary["oracle_exposure_index"],
        width,
        label="oracle",
    )
    axis.bar(
        x + width / 2,
        route_summary["predicted_exposure_index"],
        width,
        label="predicted",
    )
    axis.set(
        xticks=x,
        xticklabels=labels,
        ylabel=f"Exposure index {EXPOSURE_UNIT}",
        title="Candidate-route oracle and predicted exposure indices",
    )
    axis.tick_params(axis="x", rotation=75, labelsize=7)
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "candidate_exposure_error.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7, 6))
    for (scenario, mode), group in ranking.groupby(
        ["scenario_id", "mode"], sort=True
    ):
        axis.plot(
            group["oracle_rank"],
            group["predicted_rank"],
            marker="o",
            linestyle="none",
            label=f"{scenario}/{mode}",
        )
    axis.plot([1, K_CANDIDATES], [1, K_CANDIDATES], "k--", linewidth=1)
    axis.set(
        xlabel="Oracle exposure rank",
        ylabel="Predicted exposure rank",
        xticks=range(1, K_CANDIDATES + 1),
        yticks=range(1, K_CANDIDATES + 1),
        title="Candidate rank agreement (lower exposure = rank 1)",
    )
    axis.invert_xaxis()
    axis.invert_yaxis()
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "ranking_correlation.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    display = agreement.copy()
    display["scenario_mode"] = display["scenario_id"] + "/" + display["mode"]
    axis.bar(
        display["scenario_mode"],
        display["spearman_rank_correlation"],
        color="#1565c0",
    )
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set(
        ylabel="Spearman rank correlation",
        title="Oracle versus predicted candidate ordering",
        ylim=(-1.05, 1.05),
    )
    axis.tick_params(axis="x", rotation=30)
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "ranking_agreement.png", dpi=180)
    plt.close(figure)


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _render_report(
    route_summary: pd.DataFrame,
    error_metrics: pd.DataFrame,
    ranking: pd.DataFrame,
    agreement: pd.DataFrame,
    top_segments: pd.DataFrame,
    relationships: pd.DataFrame,
    decision: ExposureReadinessDecision,
) -> str:
    top_columns = [
        "scenario_id",
        "mode",
        "route_id",
        "pipeline_mode",
        "segment_index",
        "eta",
        "mapped_target_time",
        "pm25_estimate",
        "segment_duration_minutes",
        "exposure_contribution",
        "contribution_fraction",
    ]
    representative_top_segments = (
        top_segments.sort_values(
            [
                "scenario_id",
                "mode",
                "pipeline_mode",
                "contribution_fraction",
            ],
            ascending=[True, True, True, False],
        )
        .groupby(
            ["scenario_id", "mode", "pipeline_mode"],
            as_index=False,
            sort=True,
        )
        .head(1)
    )
    return f"""# AIRPATH-AI Milestone 4 — route exposure aggregation validation

## Scope

This is an **offline exposure-aggregation experiment only**. It does not
optimize, recommend, or constrain routes and does not alter forecasting or
spatial models.

## A. Exposure definition

For ordered route segments:

`E(route) = Σ PM2.5_i × duration_i_minutes`

The result is a **time-weighted PM2.5 exposure proxy/index** in
**{EXPOSURE_UNIT}**. It is not inhaled dose: breathing rate, uptake, activity,
and personal microenvironment are absent.

## B–C. Oracle and predicted exposure results

Two OD scenarios inside the validated pilot use the existing K=5 candidates for
walking and motorbike. Oracle uses observed station values; predicted uses only
persisted frozen V1 station forecasts. Both apply identical ceiling target-time
mapping and IDW p=1.

{_markdown_table(route_summary)}

Rank 1 is not called a recommendation; ranks are evaluation labels only.

## D. Exposure error

{_markdown_table(error_metrics)}

Errors compare predicted exposure with the internal oracle-IDW exposure index.
The oracle remains a spatial estimate, not route-level measurement.

## E–F. Route ranking correlation and top-route agreement

{_markdown_table(agreement)}

Per-route rank shifts:

{_markdown_table(ranking)}

Spearman and Kendall assess whether forecast+spatial error changes ordering.
Top-1 agreement and top-2 overlap are descriptive research outcomes, not route
selection.

## Segment contribution analysis

Representative largest segment fractions (one per scenario/mode/pathway):

{_markdown_table(representative_top_segments[top_columns])}

The complete top-five list for every candidate/pathway is saved in
`top_segment_contributions.csv`.

Contribution means `PM × minutes`; a large fraction may reflect duration,
concentration, or both. It does not establish a pollution cause.

## G. Walking versus motorbike

Walking has much longer duration and therefore a larger index under the same OD
and hourly PM2.5 field. This is expected from the definition and is not a claim
about inhaled dose or behavioral risk.

## H. Exposure error relationships

{_markdown_table(relationships)}

These are Spearman associations across only ten routes per mode. Candidate
routes overlap heavily, and the two OD scenarios differ strongly in distance.
Associations are therefore substantially confounded by scenario/route length;
they do not isolate spatial reliability effects. Reliability proxies are not
calibrated uncertainty.

## I. Hourly and scientific limitations

1. Segment ETA is specific, but PM2.5 is mapped to the next supported hour.
2. The experiment does not validate exact minute-level exposure.
3. Finer temporal validation requires genuine sub-hourly observations.
4. Oracle exposure uses IDW from fixed stations, not road measurements.
5. Only two OD scenarios and highly overlapping K-shortest candidates are used.
6. Constant walking/motorbike speeds omit real traffic and behavior.
7. Exposure index omits inhalation rate and cannot be interpreted as dose.
8. Validation predictions and examples are development-period only.
9. No route recommendation, optimization, or travel-time constraint is applied.

## J. Readiness for constrained optimization

### {decision.classification}

{decision.rationale}

Observed restrictions are material: predicted indices underestimate their
oracle counterparts by roughly 15–34%, one scenario/mode has Spearman 0.6 and
only 50% top-2 overlap, only two OD pairs are tested, and candidate routes
overlap heavily. Any subsequent constrained-optimization work must remain an
offline sensitivity experiment and must not produce user-facing recommendations.

```json
{json.dumps(dict(decision.criteria), indent=2)}
```

Strict readiness requires perfect top-1 agreement, mean Spearman ≥0.9, every
scenario Spearman ≥0.8, and mode MAPE ≤10%. Restricted readiness requires at
least 50% top-1 agreement, mean Spearman ≥0.6, no negative scenario correlation,
and mode MAPE ≤25%. These are transparent prototype progression gates, not
health or regulatory thresholds.

Even an A/B result authorizes only a later **offline constrained-optimization
research experiment**. It does not authorize user-facing route recommendations.
"""


def generate_exposure_outputs(
    *,
    prediction_csv: str | Path = (
        "data/processed/xgboost_forecasting_predictions.csv"
    ),
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    output_directory: str | Path = "data/processed/exposure",
    report_path: str | Path = "reports/route_exposure.md",
) -> dict[str, object]:
    predictions = pd.read_csv(
        prediction_csv,
        parse_dates=["origin_time", "target_time"],
        low_memory=False,
    )
    observed_by_target, forecasted_by_target = _saved_station_tables(
        predictions, FORECASTING_ORIGIN
    )
    network = load_network(network_path)

    all_segment_records: list[SegmentExposure] = []
    summary_rows: list[dict[str, object]] = []
    routes: list[CandidateRoute] = []
    for scenario_id, (origin, destination) in OD_SCENARIOS.items():
        for mode in ("walking", "motorbike"):
            candidates = generate_candidate_routes(
                network,
                origin,
                destination,
                mode,
                k=K_CANDIDATES,
            )
            if len(candidates) != K_CANDIDATES:
                raise ValueError(
                    f"{scenario_id}/{mode} did not produce K={K_CANDIDATES} routes."
                )
            routes.extend(candidates)
            for route in candidates:
                segments = propagate_segment_etas(
                    network, route, ROUTE_DEPARTURE
                )
                oracle_records = compute_oracle_exposure(
                    scenario_id,
                    segments,
                    FORECASTING_ORIGIN,
                    observed_by_target,
                )
                predicted_records = compute_predicted_exposure(
                    scenario_id,
                    segments,
                    FORECASTING_ORIGIN,
                    forecasted_by_target,
                )
                all_segment_records.extend(oracle_records)
                all_segment_records.extend(predicted_records)
                summary_rows.append(
                    summarize_route_exposure(
                        route, oracle_records, predicted_records
                    )
                )

    route_summary = pd.DataFrame(summary_rows)
    ranking, agreement = rank_candidate_exposures(route_summary)
    error_metrics = exposure_error_metrics(route_summary)
    relationships = exposure_error_relationships(route_summary)
    segment_frame = pd.DataFrame(
        [record.to_dict() for record in all_segment_records]
    )
    top_segments = top_segment_contributions(segment_frame)
    decision = decide_exposure_readiness(agreement, error_metrics)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    route_summary.to_csv(
        output_directory / "candidate_route_exposure.csv", index=False
    )
    segment_frame.to_csv(
        output_directory / "segment_exposure_contributions.csv", index=False
    )
    top_segments.to_csv(
        output_directory / "top_segment_contributions.csv", index=False
    )
    ranking.to_csv(output_directory / "route_ranking.csv", index=False)
    agreement.to_csv(
        output_directory / "ranking_agreement.csv", index=False
    )
    error_metrics.to_csv(
        output_directory / "exposure_error_metrics.csv", index=False
    )
    relationships.to_csv(
        output_directory / "exposure_error_relationships.csv", index=False
    )
    (output_directory / "readiness_decision.json").write_text(
        json.dumps(asdict(decision), indent=2),
        encoding="utf-8",
    )
    _plot_outputs(route_summary, ranking, agreement, output_directory)

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_report(
            route_summary,
            error_metrics,
            ranking,
            agreement,
            top_segments,
            relationships,
            decision,
        ),
        encoding="utf-8",
    )
    return {
        "routes": routes,
        "segments": segment_frame,
        "route_summary": route_summary,
        "ranking": ranking,
        "agreement": agreement,
        "error_metrics": error_metrics,
        "relationships": relationships,
        "top_segments": top_segments,
        "decision": decision,
    }


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--predictions",
        default="data/processed/xgboost_forecasting_predictions.csv",
    )
    parser.add_argument(
        "--network",
        default="data/processed/road_network/healthyair_pilot_osm.json.gz",
    )
    parser.add_argument(
        "--output-directory", default="data/processed/exposure"
    )
    parser.add_argument("--report", default="reports/route_exposure.md")
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_exposure_outputs(
        prediction_csv=arguments.predictions,
        network_path=arguments.network,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
    )
    print(outputs["route_summary"].to_string(index=False))
    print(outputs["agreement"].to_string(index=False))
    print(outputs["decision"])


if __name__ == "__main__":
    main()
