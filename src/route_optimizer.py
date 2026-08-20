"""Offline user-controlled constrained route-ranking research experiment.

The user-facing control is an absolute additional-time allowance in minutes.
This module never optimizes the road graph directly for exposure and never
returns a single recommendation: it preserves the fastest route and exposes up
to three lower-predicted-exposure feasible alternatives for inspection.
"""

from __future__ import annotations

import argparse
import heapq
import json
from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations, count
from pathlib import Path
from typing import Final, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .eta_engine import edge_duration_seconds, propagate_segment_etas, speed_for_mode
from .exposure import (
    FORECASTING_ORIGIN,
    ROUTE_DEPARTURE,
    _kendall_tau_a,
    _saved_station_tables,
    _spearman,
    compute_oracle_exposure,
    compute_predicted_exposure,
    summarize_route_exposure,
)
from .road_network import PILOT_POLYGON, RoadNetwork, load_network, point_in_pilot_area
from .route_candidates import CandidateRoute, generate_candidate_routes
from .spatial_estimation import haversine_distance_km


RANDOM_SEED: Final[int] = 42
SCENARIO_COUNT: Final[int] = 10
TARGET_CANDIDATES: Final[int] = 8
MINIMUM_CANDIDATES: Final[int] = 5
DEFAULT_SHORTLIST_SIZE: Final[int] = 3
TIME_TOLERANCES_MINUTES: Final[tuple[int, ...]] = (0, 1, 2, 3, 5, 10)
MAX_ROUTE_DURATION_MINUTES: Final[float] = 119.0
MAX_ADDITIONAL_CANDIDATE_MINUTES: Final[float] = 15.0


@dataclass(frozen=True)
class OptimizationReadinessDecision:
    classification: str
    rationale: str
    criteria: Mapping[str, object]


def generate_od_scenarios(
    *,
    seed: int = RANDOM_SEED,
    count_scenarios: int = SCENARIO_COUNT,
) -> pd.DataFrame:
    """Generate deterministic in-polygon OD pairs spanning 2–6 km straight-line."""
    if count_scenarios < 1:
        raise ValueError("count_scenarios must be positive.")
    rng = np.random.default_rng(seed)
    south = min(point[0] for point in PILOT_POLYGON)
    north = max(point[0] for point in PILOT_POLYGON)
    west = min(point[1] for point in PILOT_POLYGON)
    east = max(point[1] for point in PILOT_POLYGON)
    rows: list[dict[str, object]] = []
    attempts = 0
    while len(rows) < count_scenarios and attempts < 100_000:
        attempts += 1
        origin = (float(rng.uniform(south, north)), float(rng.uniform(west, east)))
        destination = (
            float(rng.uniform(south, north)),
            float(rng.uniform(west, east)),
        )
        if not (
            point_in_pilot_area(*origin)
            and point_in_pilot_area(*destination)
        ):
            continue
        distance = haversine_distance_km(*origin, *destination)
        if not 2.0 <= distance <= 6.0:
            continue
        rounded = tuple(round(value, 6) for value in (*origin, *destination))
        if any(
            tuple(
                round(value, 6)
                for value in (
                    row["origin_latitude"],
                    row["origin_longitude"],
                    row["destination_latitude"],
                    row["destination_longitude"],
                )
            )
            == rounded
            for row in rows
        ):
            continue
        rows.append(
            {
                "scenario_id": f"od_{len(rows) + 1:02d}",
                "origin_latitude": origin[0],
                "origin_longitude": origin[1],
                "destination_latitude": destination[0],
                "destination_longitude": destination[1],
                "straight_line_distance_km": distance,
                "generation_seed": seed,
                "generation_method": (
                    "seeded uniform rejection inside stations 2–6 polygon; "
                    "straight-line distance 2–6 km"
                ),
            }
        )
    if len(rows) != count_scenarios:
        raise RuntimeError("Unable to generate the requested in-polygon scenarios.")
    return pd.DataFrame(rows)


def _penalized_shortest_path(
    network: RoadNetwork,
    start_node: int,
    destination_node: int,
    mode: str,
    speed_kmh: float,
    edge_usage: Mapping[str, int],
    penalty_strength: float,
) -> tuple[str, ...] | None:
    queue: list[tuple[float, int, int]] = [(0.0, 0, start_node)]
    sequence = count(1)
    best = {start_node: 0.0}
    parent: dict[int, tuple[int, str]] = {}
    while queue:
        cost, _, node = heapq.heappop(queue)
        if cost > best.get(node, float("inf")) + 1e-12:
            continue
        if node == destination_node:
            edge_ids: list[str] = []
            while node != start_node:
                previous, edge_id = parent[node]
                edge_ids.append(edge_id)
                node = previous
            return tuple(reversed(edge_ids))
        for edge in network.outgoing_edges(node, mode):
            base = edge_duration_seconds(edge.length_m, speed_kmh)
            penalty = 1 + penalty_strength * edge_usage.get(edge.edge_id, 0)
            next_cost = cost + base * penalty
            if next_cost + 1e-12 >= best.get(edge.end_node, float("inf")):
                continue
            best[edge.end_node] = next_cost
            parent[edge.end_node] = (node, edge.edge_id)
            heapq.heappush(
                queue, (next_cost, next(sequence), edge.end_node)
            )
    return None


def _candidate_from_edges(
    network: RoadNetwork,
    edge_ids: Sequence[str],
    *,
    route_id: str,
    mode: str,
    origin: tuple[float, float],
    destination: tuple[float, float],
    origin_node: int,
    destination_node: int,
) -> CandidateRoute:
    if not edge_ids:
        raise ValueError("Candidate route requires at least one edge.")
    speed = speed_for_mode(mode)
    edges = [network.edges[edge_id] for edge_id in edge_ids]
    nodes = [origin_node]
    geometry: list[tuple[float, float]] = []
    for edge in edges:
        if edge.start_node != nodes[-1]:
            raise ValueError("Penalized route contains disconnected edges.")
        nodes.append(edge.end_node)
        if geometry and geometry[-1] != edge.geometry[0]:
            raise ValueError("Penalized route geometry is inconsistent.")
        geometry.extend(edge.geometry if not geometry else edge.geometry[1:])
    if nodes[-1] != destination_node:
        raise ValueError("Penalized route does not reach destination.")
    origin_road = network.nodes[origin_node]
    destination_road = network.nodes[destination_node]
    distance = float(sum(edge.length_m for edge in edges))
    duration = float(
        sum(edge_duration_seconds(edge.length_m, speed) for edge in edges)
    )
    return CandidateRoute(
        route_id=route_id,
        mode=mode,
        origin=origin,
        destination=destination,
        origin_node=origin_node,
        destination_node=destination_node,
        origin_snap_distance_m=1000
        * haversine_distance_km(
            *origin, origin_road.latitude, origin_road.longitude
        ),
        destination_snap_distance_m=1000
        * haversine_distance_km(
            *destination,
            destination_road.latitude,
            destination_road.longitude,
        ),
        node_ids=tuple(nodes),
        edge_ids=tuple(edge_ids),
        geometry=tuple(geometry),
        total_distance_m=distance,
        total_travel_time_seconds=duration,
    )


def generate_diverse_candidates(
    network: RoadNetwork,
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str,
    *,
    target_count: int = TARGET_CANDIDATES,
) -> list[CandidateRoute]:
    """Generate fastest plus overlap-penalized, OSM-valid alternatives."""
    if target_count < 2:
        raise ValueError("target_count must be at least two.")
    origin_node = network.nearest_node(*origin, mode)
    destination_node = network.nearest_node(*destination, mode)
    speed = speed_for_mode(mode)
    edge_usage: Counter[str] = Counter()
    candidates: list[CandidateRoute] = []
    seen: set[tuple[str, ...]] = set()
    penalty_schedule = (0.0, 0.2, 0.4, 0.75, 1.25, 2.0, 3.0, 5.0, 8.0)
    fastest_minutes: float | None = None
    attempts = 0
    while len(candidates) < target_count and attempts < 60:
        penalty = penalty_schedule[min(attempts, len(penalty_schedule) - 1)]
        attempts += 1
        edge_ids = _penalized_shortest_path(
            network,
            origin_node,
            destination_node,
            mode,
            speed,
            edge_usage,
            penalty,
        )
        if edge_ids is None:
            break
        if edge_ids in seen:
            # Increase pressure on the duplicate path before the next attempt.
            edge_usage.update(edge_ids)
            continue
        candidate = _candidate_from_edges(
            network,
            edge_ids,
            route_id=f"{mode}-{len(candidates) + 1}",
            mode=mode,
            origin=origin,
            destination=destination,
            origin_node=origin_node,
            destination_node=destination_node,
        )
        duration_minutes = candidate.total_travel_time_seconds / 60
        if fastest_minutes is None:
            fastest_minutes = duration_minutes
        if (
            duration_minutes <= MAX_ROUTE_DURATION_MINUTES
            and duration_minutes
            <= fastest_minutes + MAX_ADDITIONAL_CANDIDATE_MINUTES
        ):
            candidates.append(candidate)
            seen.add(edge_ids)
        edge_usage.update(edge_ids)
    if len(candidates) < target_count:
        for route in generate_candidate_routes(
            network,
            origin,
            destination,
            mode,
            k=target_count + 5,
        ):
            if route.edge_ids in seen:
                continue
            duration_minutes = route.total_travel_time_seconds / 60
            if fastest_minutes is None:
                fastest_minutes = duration_minutes
            if (
                duration_minutes <= MAX_ROUTE_DURATION_MINUTES
                and duration_minutes
                <= fastest_minutes + MAX_ADDITIONAL_CANDIDATE_MINUTES
            ):
                candidates.append(
                    CandidateRoute(
                        route_id=f"{mode}-{len(candidates) + 1}",
                        mode=route.mode,
                        origin=route.origin,
                        destination=route.destination,
                        origin_node=route.origin_node,
                        destination_node=route.destination_node,
                        origin_snap_distance_m=route.origin_snap_distance_m,
                        destination_snap_distance_m=route.destination_snap_distance_m,
                        node_ids=route.node_ids,
                        edge_ids=route.edge_ids,
                        geometry=route.geometry,
                        total_distance_m=route.total_distance_m,
                        total_travel_time_seconds=route.total_travel_time_seconds,
                    )
                )
                seen.add(route.edge_ids)
            if len(candidates) >= target_count:
                break
    if len(candidates) < MINIMUM_CANDIDATES:
        raise ValueError(
            f"Only {len(candidates)} diverse {mode} routes were generated."
        )
    return candidates


def edge_jaccard(first: Sequence[str], second: Sequence[str]) -> float:
    first_set, second_set = set(first), set(second)
    union = first_set | second_set
    return 1.0 if not union else len(first_set & second_set) / len(union)


def candidate_diversity_rows(
    scenario_id: str,
    routes: Sequence[CandidateRoute],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fastest = min(routes, key=lambda route: route.total_travel_time_seconds)
    route_rows = []
    for route in routes:
        overlap = edge_jaccard(route.edge_ids, fastest.edge_ids)
        route_rows.append(
            {
                "scenario_id": scenario_id,
                "mode": route.mode,
                "route_id": route.route_id,
                "is_fastest": route.route_id == fastest.route_id,
                "travel_time_minutes": route.total_travel_time_seconds / 60,
                "additional_time_vs_fastest_minutes": (
                    route.total_travel_time_seconds
                    - fastest.total_travel_time_seconds
                )
                / 60,
                "distance_m": route.total_distance_m,
                "segment_count": len(route.edge_ids),
                "edge_jaccard_with_fastest": overlap,
                "edge_difference_fraction_from_fastest": 1 - overlap,
                "geometry": json.dumps(
                    [list(point) for point in route.geometry],
                    separators=(",", ":"),
                ),
                "ordered_edge_ids": json.dumps(list(route.edge_ids)),
            }
        )
    pair_rows = []
    for first, second in combinations(routes, 2):
        pair_rows.append(
            {
                "scenario_id": scenario_id,
                "mode": first.mode,
                "route_a": first.route_id,
                "route_b": second.route_id,
                "edge_jaccard": edge_jaccard(first.edge_ids, second.edge_ids),
            }
        )
    return pd.DataFrame(route_rows), pd.DataFrame(pair_rows)


def build_feasible_shortlists(
    route_summary: pd.DataFrame,
    tolerances: Sequence[float] = TIME_TOLERANCES_MINUTES,
    *,
    shortlist_size: int = DEFAULT_SHORTLIST_SIZE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply absolute-minute constraints and expose fastest plus alternatives."""
    if shortlist_size < 1:
        raise ValueError("shortlist_size must be positive.")
    feasible_rows, shortlist_rows, decision_rows = [], [], []
    for (scenario_id, mode), group in route_summary.groupby(
        ["scenario_id", "mode"], sort=True
    ):
        fastest = group.sort_values(
            ["total_travel_time_minutes", "route_id"]
        ).iloc[0]
        fastest_time = float(fastest["total_travel_time_minutes"])
        for raw_tolerance in tolerances:
            tolerance = float(raw_tolerance)
            if tolerance < 0:
                raise ValueError("Additional-time tolerance cannot be negative.")
            maximum_time = fastest_time + tolerance
            epsilon = tolerance / fastest_time
            feasible = group.loc[
                group["total_travel_time_minutes"].le(maximum_time + 1e-9)
            ].copy()
            feasible = feasible.sort_values(
                ["predicted_exposure_index", "route_id"]
            )
            if feasible.empty:
                raise AssertionError("Fastest route must always remain feasible.")
            feasible_ids = set(feasible["route_id"])
            if fastest["route_id"] not in feasible_ids:
                raise AssertionError("Fastest route was lost from feasible set.")
            for row in group.itertuples():
                feasible_rows.append(
                    {
                        "scenario_id": scenario_id,
                        "mode": mode,
                        "delta_time_allowed_minutes": tolerance,
                        "epsilon_internal": epsilon,
                        "fastest_time_minutes": fastest_time,
                        "maximum_feasible_time_minutes": maximum_time,
                        "route_id": row.route_id,
                        "travel_time_minutes": row.total_travel_time_minutes,
                        "is_feasible": row.route_id in feasible_ids,
                    }
                )
            predicted_optimal = feasible.iloc[0]
            oracle_optimal = feasible.sort_values(
                ["oracle_exposure_index", "route_id"]
            ).iloc[0]
            oracle_denominator = float(oracle_optimal["oracle_exposure_index"])
            regret = (
                float(predicted_optimal["oracle_exposure_index"])
                - oracle_denominator
            ) / oracle_denominator
            if regret < -1e-12:
                raise AssertionError("Decision regret cannot be negative.")
            alternatives = feasible.loc[
                ~feasible["route_id"].eq(fastest["route_id"])
            ].head(shortlist_size)
            returned = pd.concat(
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
            for row in returned.itertuples():
                shortlist_rows.append(
                    {
                        "scenario_id": scenario_id,
                        "mode": mode,
                        "delta_time_allowed_minutes": tolerance,
                        "epsilon_internal": epsilon,
                        "maximum_feasible_time_minutes": maximum_time,
                        "route_id": row.route_id,
                        "rank": int(row.shortlist_rank),
                        "route_type": row.route_type,
                        "travel_time_minutes": float(
                            row.total_travel_time_minutes
                        ),
                        "additional_time_vs_fastest_minutes": float(
                            row.total_travel_time_minutes
                        )
                        - fastest_time,
                        "distance_m": float(row.total_distance_m),
                        "predicted_exposure_index": float(
                            row.predicted_exposure_index
                        ),
                        "predicted_exposure_reduction_vs_fastest": float(
                            fastest["predicted_exposure_index"]
                            - row.predicted_exposure_index
                        ),
                        "oracle_exposure_index": float(
                            row.oracle_exposure_index
                        ),
                        "oracle_exposure_reduction_vs_fastest": float(
                            fastest["oracle_exposure_index"]
                            - row.oracle_exposure_index
                        ),
                        "segment_count": int(row.segment_count),
                        "edge_jaccard_with_fastest": float(
                            row.edge_jaccard_with_fastest
                        ),
                        "edge_difference_fraction_from_fastest": float(
                            row.edge_difference_fraction_from_fastest
                        ),
                        "available_feasible_alternatives": len(feasible) - 1,
                        "requested_alternative_count": shortlist_size,
                        "fewer_than_requested_alternatives": (
                            len(alternatives) < shortlist_size
                        ),
                    }
                )
            decision_rows.append(
                {
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "delta_time_allowed_minutes": tolerance,
                    "epsilon_internal": epsilon,
                    "maximum_feasible_time_minutes": maximum_time,
                    "feasible_route_count": len(feasible),
                    "feasible_alternative_count": len(feasible) - 1,
                    "fastest_route_id": fastest["route_id"],
                    "predicted_optimal_route_id": predicted_optimal["route_id"],
                    "oracle_optimal_route_id": oracle_optimal["route_id"],
                    "predicted_optimal_travel_time_minutes": float(
                        predicted_optimal["total_travel_time_minutes"]
                    ),
                    "predicted_optimal_additional_time_minutes": float(
                        predicted_optimal["total_travel_time_minutes"]
                    )
                    - fastest_time,
                    "predicted_optimal_predicted_exposure": float(
                        predicted_optimal["predicted_exposure_index"]
                    ),
                    "predicted_optimal_oracle_exposure": float(
                        predicted_optimal["oracle_exposure_index"]
                    ),
                    "predicted_exposure_reduction_vs_fastest": float(
                        fastest["predicted_exposure_index"]
                        - predicted_optimal["predicted_exposure_index"]
                    ),
                    "oracle_exposure_reduction_vs_fastest": float(
                        fastest["oracle_exposure_index"]
                        - predicted_optimal["oracle_exposure_index"]
                    ),
                    "oracle_exposure_fastest": float(
                        fastest["oracle_exposure_index"]
                    ),
                    "oracle_exposure_oracle_optimal": oracle_denominator,
                    "decision_regret": max(0.0, float(regret)),
                    "oracle_optimal_agreement": (
                        predicted_optimal["route_id"]
                        == oracle_optimal["route_id"]
                    ),
                }
            )
    return (
        pd.DataFrame(feasible_rows),
        pd.DataFrame(shortlist_rows),
        pd.DataFrame(decision_rows),
    )


def decision_regret_summary(decisions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groupings = [("ALL", decisions)]
    groupings.extend(
        (str(tolerance), group)
        for tolerance, group in decisions.groupby(
            "delta_time_allowed_minutes", sort=True
        )
    )
    for tolerance, group in groupings:
        rows.append(
            {
                "delta_time_allowed_minutes": tolerance,
                "decisions": len(group),
                "mean_regret": float(group["decision_regret"].mean()),
                "median_regret": float(group["decision_regret"].median()),
                "maximum_regret": float(group["decision_regret"].max()),
                "zero_regret_percentage": float(
                    100 * group["decision_regret"].le(1e-12).mean()
                ),
                "oracle_optimal_agreement_percentage": float(
                    100 * group["oracle_optimal_agreement"].mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def feasibility_summary(decisions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tolerance, group in decisions.groupby(
        "delta_time_allowed_minutes", sort=True
    ):
        alternatives = group["feasible_alternative_count"]
        rows.append(
            {
                "delta_time_allowed_minutes": tolerance,
                "scenario_mode_cases": len(group),
                "no_alternative_beyond_fastest": int(alternatives.eq(0).sum()),
                "only_one_feasible_route": int(
                    group["feasible_route_count"].eq(1).sum()
                ),
                "exactly_two_feasible_routes": int(
                    group["feasible_route_count"].eq(2).sum()
                ),
                "at_least_three_feasible_routes": int(
                    group["feasible_route_count"].ge(3).sum()
                ),
                "at_least_three_feasible_alternatives": int(
                    alternatives.ge(3).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def expanded_ranking_quality(
    route_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking_rows, quality_rows = [], []
    for (scenario_id, mode), group in route_summary.groupby(
        ["scenario_id", "mode"], sort=True
    ):
        oracle = group.sort_values(
            ["oracle_exposure_index", "route_id"]
        )["route_id"].tolist()
        predicted = group.sort_values(
            ["predicted_exposure_index", "route_id"]
        )["route_id"].tolist()
        oracle_rank = {route_id: index + 1 for index, route_id in enumerate(oracle)}
        predicted_rank = {
            route_id: index + 1 for index, route_id in enumerate(predicted)
        }
        route_ids = sorted(oracle_rank)
        oracle_values = [oracle_rank[route_id] for route_id in route_ids]
        predicted_values = [predicted_rank[route_id] for route_id in route_ids]
        for route_id in route_ids:
            ranking_rows.append(
                {
                    "scenario_id": scenario_id,
                    "mode": mode,
                    "route_id": route_id,
                    "oracle_rank": oracle_rank[route_id],
                    "predicted_rank": predicted_rank[route_id],
                    "rank_shift": predicted_rank[route_id] - oracle_rank[route_id],
                }
            )
        quality_rows.append(
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
                "top_1_agreement": oracle[0] == predicted[0],
                "top_2_overlap_count": len(set(oracle[:2]) & set(predicted[:2])),
                "top_2_overlap_fraction": len(
                    set(oracle[:2]) & set(predicted[:2])
                )
                / 2,
            }
        )
    return pd.DataFrame(ranking_rows), pd.DataFrame(quality_rows)


def decide_optimization_readiness(
    decisions: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    feasibility: pd.DataFrame,
) -> OptimizationReadinessDecision:
    nontrivial = decisions.loc[
        decisions["delta_time_allowed_minutes"].gt(0)
    ]
    mean_regret = float(nontrivial["decision_regret"].mean())
    maximum_regret = float(nontrivial["decision_regret"].max())
    oracle_agreement = float(nontrivial["oracle_optimal_agreement"].mean())
    mean_spearman = float(
        ranking_quality["spearman_rank_correlation"].mean()
    )
    tolerance_five = feasibility.loc[
        feasibility["delta_time_allowed_minutes"].eq(5)
    ].iloc[0]
    three_alternative_rate = float(
        tolerance_five["at_least_three_feasible_alternatives"]
        / tolerance_five["scenario_mode_cases"]
    )
    criteria = {
        "nontrivial_mean_decision_regret": mean_regret,
        "nontrivial_maximum_decision_regret": maximum_regret,
        "nontrivial_oracle_optimal_agreement_rate": oracle_agreement,
        "expanded_mean_spearman": mean_spearman,
        "five_minute_three_alternative_availability_rate": three_alternative_rate,
        "strict_mean_regret_le_0_02": mean_regret <= 0.02,
        "strict_max_regret_le_0_10": maximum_regret <= 0.10,
        "strict_oracle_agreement_ge_0_90": oracle_agreement >= 0.90,
        "strict_mean_spearman_ge_0_80": mean_spearman >= 0.80,
        "strict_three_alternative_rate_ge_0_80": three_alternative_rate >= 0.80,
        "restricted_mean_regret_le_0_05": mean_regret <= 0.05,
        "restricted_max_regret_le_0_20": maximum_regret <= 0.20,
        "restricted_oracle_agreement_ge_0_70": oracle_agreement >= 0.70,
        "restricted_mean_spearman_ge_0_60": mean_spearman >= 0.60,
        "restricted_three_alternative_rate_ge_0_50": (
            three_alternative_rate >= 0.50
        ),
    }
    strict = all(
        criteria[key]
        for key in criteria
        if key.startswith("strict_")
    )
    restricted = all(
        criteria[key]
        for key in criteria
        if key.startswith("restricted_")
    )
    if strict:
        classification = "A. READY FOR PROTOTYPE INTEGRATION"
        rationale = "All strict decision-quality and shortlist-availability gates pass."
    elif restricted:
        classification = "B. READY WITH RESTRICTIONS"
        rationale = (
            "Offline decision quality passes restricted gates but not every "
            "strict prototype-integration gate."
        )
    else:
        classification = "C. NOT READY"
        rationale = (
            "Decision regret, ranking quality, or feasible-choice availability "
            "fails the restricted gate."
        )
    return OptimizationReadinessDecision(classification, rationale, criteria)


def _plot_outputs(
    decisions: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    feasibility: pd.DataFrame,
    output_directory: Path,
) -> None:
    tradeoff = (
        decisions.groupby(["mode", "delta_time_allowed_minutes"], as_index=False)
        .agg(
            mean_oracle_exposure_reduction=(
                "oracle_exposure_reduction_vs_fastest",
                "mean",
            ),
            mean_additional_time=(
                "predicted_optimal_additional_time_minutes",
                "mean",
            ),
        )
    )
    figure, axis = plt.subplots(figsize=(8, 5))
    for mode, group in tradeoff.groupby("mode", sort=True):
        axis.plot(
            group["delta_time_allowed_minutes"],
            group["mean_oracle_exposure_reduction"],
            marker="o",
            label=mode,
        )
    axis.set(
        xlabel="Additional travel time allowed (minutes)",
        ylabel=f"Mean oracle exposure reduction ({'(µg/m³)·min'})",
        title="Offline time-tolerance versus oracle exposure reduction",
    )
    axis.legend()
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "time_exposure_tradeoff.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 5))
    display = ranking_quality.copy()
    display["scenario_mode"] = display["scenario_id"] + "/" + display["mode"]
    axis.bar(
        display["scenario_mode"],
        display["spearman_rank_correlation"],
        color="#1565c0",
    )
    axis.axhline(0.875, color="#c62828", linestyle="--", label="Milestone 4 mean")
    axis.set(
        ylabel="Spearman predicted vs oracle",
        title="Expanded-scenario route ranking quality",
        ylim=(-1.05, 1.05),
    )
    axis.tick_params(axis="x", rotation=75, labelsize=7)
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_directory / "ranking_agreement.png", dpi=180)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    axis.stackplot(
        feasibility["delta_time_allowed_minutes"],
        feasibility["only_one_feasible_route"],
        feasibility["exactly_two_feasible_routes"],
        feasibility["at_least_three_feasible_routes"],
        labels=("1 route", "2 routes", "≥3 routes"),
        alpha=0.8,
    )
    axis.set(
        xlabel="Additional travel time allowed (minutes)",
        ylabel="Scenario/mode cases",
        title="Feasible-route availability",
    )
    axis.legend(loc="center right")
    figure.tight_layout()
    figure.savefig(output_directory / "feasible_route_availability.png", dpi=180)
    plt.close(figure)


def _markdown_table(frame: pd.DataFrame, digits: int = 4) -> str:
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _render_report(
    scenarios: pd.DataFrame,
    diversity_summary: pd.DataFrame,
    feasibility: pd.DataFrame,
    shortlist_sample: pd.DataFrame,
    decisions: pd.DataFrame,
    regret: pd.DataFrame,
    ranking_quality: pd.DataFrame,
    decision: OptimizationReadinessDecision,
) -> str:
    tolerance_tradeoff = (
        decisions.groupby(["mode", "delta_time_allowed_minutes"], as_index=False)
        .agg(
            mean_selected_additional_minutes=(
                "predicted_optimal_additional_time_minutes",
                "mean",
            ),
            mean_predicted_exposure_reduction=(
                "predicted_exposure_reduction_vs_fastest",
                "mean",
            ),
            mean_oracle_exposure_reduction=(
                "oracle_exposure_reduction_vs_fastest",
                "mean",
            ),
            oracle_optimal_agreement_rate=(
                "oracle_optimal_agreement",
                "mean",
            ),
        )
    )
    return f"""# AIRPATH-AI Milestone 5 — constrained multi-route research experiment

## Scope

This is an **offline research optimization experiment**. It does not build a
web application and must not be described as a medical or health recommendation.
User control is an absolute additional-time allowance in minutes.

## A. OD scenarios

{len(scenarios)} deterministic OD scenarios were generated with seed
{RANDOM_SEED} by uniform rejection sampling inside the validated stations 2–6
polygon, retaining straight-line separations of 2–6 km.

{_markdown_table(scenarios)}

## B. Candidate diversity

Each scenario/mode retains the true fastest route, then creates OSM-valid
alternatives by repeatedly penalizing already-used directed edges during
shortest-path search. Routes are capped at 15 additional minutes and 119 total
minutes to stay within the frozen hourly forecast horizon.

{_markdown_table(diversity_summary)}

Edge Jaccard 1 means identical edge sets; lower values indicate more distinct
alternatives. This heuristic improves diversity but does not guarantee
behaviorally distinct routes.

## C. Feasible-route availability by user tolerance

`T_max = T_fastest + delta_time_allowed_minutes`, with
`delta ∈ {{0,1,2,3,5,10}}`.

{_markdown_table(feasibility)}

Zero minutes is intentionally strict and often leaves only the fastest route.
No tolerance is altered to manufacture alternatives.

## D. Top-3 multi-route output

The output always retains the fastest route as a reference and adds up to three
distinct feasible alternatives sorted by predicted exposure. A representative
subset is shown; complete web-ready rows are in `shortlist.csv`.

{_markdown_table(shortlist_sample)}

The internal predicted-optimal route is recorded separately and is not the only
route exposed to the future user interface.

## E–G. Predicted/oracle exposure and decision regret

Predicted-optimal selections by tolerance:

{_markdown_table(tolerance_tradeoff)}

Decision regret:

{_markdown_table(regret)}

Regret is
`(oracle exposure of predicted-optimal - oracle feasible minimum) / oracle feasible minimum`.
The delta=0 case is structurally trivial when only the fastest route is feasible,
so nontrivial readiness criteria use tolerances above zero.

## H. Expanded ranking quality

{_markdown_table(ranking_quality)}

Milestone 4 mean Spearman was 0.875 over four scenario/mode cases. This expanded
experiment reports 20 cases; top-1 agreement remains an evaluation statistic,
not a recommendation.

## I–K. Mode and tolerance trade-offs

Walking accumulates a larger PM×minutes index because baseline travel time is
longer. Tables and `time_exposure_tradeoff.png` show additional minutes,
predicted reduction, and oracle reduction rather than hiding the trade-off.

The primary parameter is always absolute minutes. Epsilon may be derived as
`delta / fastest_time` internally but is not required from users.

## Feasibility failures

{_markdown_table(feasibility)}

Rows explicitly distinguish no alternative, exactly two feasible routes, and
three-or-more feasible choices for future UI handling.

## Scientific limitations

1. Exposure is a time-weighted PM2.5 proxy, not inhaled dose.
2. Target-time PM2.5 remains hourly; minute-level accuracy is unvalidated.
3. Oracle exposure is IDW-derived and not measured on roads.
4. Speeds omit traffic, signals, turns, and delay.
5. The pilot is geographically bounded.
6. Fixed/community/reference data limitations remain.
7. Alternatives are algorithmic OSM paths and can still overlap.
8. Forecast exposure magnitude error observed in Milestone 4 remains.
9. Lower predicted exposure is not a guaranteed health benefit.

Use “lower estimated PM2.5 exposure”, “lower predicted exposure”, and
“exposure-aware route”; do not claim medical protection.

## L. Prototype integration decision

### {decision.classification}

{decision.rationale}

```json
{json.dumps(dict(decision.criteria), indent=2)}
```

An A/B result permits only future prototype integration that shows the fastest
route and multiple transparent alternatives. It does not authorize a
single-route recommendation or production deployment.
"""


def generate_optimization_outputs(
    *,
    prediction_csv: str | Path = (
        "data/processed/xgboost_forecasting_predictions.csv"
    ),
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    output_directory: str | Path = "data/processed/optimization",
    report_path: str | Path = "reports/constrained_routing.md",
) -> dict[str, object]:
    scenarios = generate_od_scenarios()
    predictions = pd.read_csv(
        prediction_csv,
        parse_dates=["origin_time", "target_time"],
        low_memory=False,
    )
    observed_by_target, forecasted_by_target = _saved_station_tables(
        predictions, FORECASTING_ORIGIN
    )
    network = load_network(network_path)

    all_routes: list[CandidateRoute] = []
    route_metadata_rows: list[pd.DataFrame] = []
    pairwise_rows: list[pd.DataFrame] = []
    exposure_rows: list[dict[str, object]] = []
    segment_records = []

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
            all_routes.extend(routes)
            route_metadata, pairwise = candidate_diversity_rows(
                scenario.scenario_id, routes
            )
            route_metadata_rows.append(route_metadata)
            pairwise_rows.append(pairwise)
            metadata_lookup = route_metadata.set_index("route_id")
            for route in routes:
                segments = propagate_segment_etas(
                    network, route, ROUTE_DEPARTURE
                )
                oracle = compute_oracle_exposure(
                    scenario.scenario_id,
                    segments,
                    FORECASTING_ORIGIN,
                    observed_by_target,
                )
                predicted = compute_predicted_exposure(
                    scenario.scenario_id,
                    segments,
                    FORECASTING_ORIGIN,
                    forecasted_by_target,
                )
                segment_records.extend(record.to_dict() for record in oracle)
                segment_records.extend(record.to_dict() for record in predicted)
                summary = summarize_route_exposure(route, oracle, predicted)
                metadata = metadata_lookup.loc[route.route_id]
                summary.update(
                    {
                        "edge_jaccard_with_fastest": float(
                            metadata["edge_jaccard_with_fastest"]
                        ),
                        "edge_difference_fraction_from_fastest": float(
                            metadata["edge_difference_fraction_from_fastest"]
                        ),
                    }
                )
                exposure_rows.append(summary)

    candidate_metadata = pd.concat(route_metadata_rows, ignore_index=True)
    pairwise = pd.concat(pairwise_rows, ignore_index=True)
    route_summary = pd.DataFrame(exposure_rows)
    feasible, shortlist, decisions = build_feasible_shortlists(route_summary)
    regret = decision_regret_summary(decisions)
    feasibility = feasibility_summary(decisions)
    ranking_rows, ranking_quality = expanded_ranking_quality(route_summary)
    decision = decide_optimization_readiness(
        decisions, ranking_quality, feasibility
    )

    diversity_summary = (
        pairwise.groupby(["scenario_id", "mode"], as_index=False)
        .agg(
            candidate_count=("route_a", lambda values: len(set(values)) + 1),
            mean_pairwise_edge_jaccard=("edge_jaccard", "mean"),
            maximum_pairwise_edge_jaccard=("edge_jaccard", "max"),
            minimum_pairwise_edge_jaccard=("edge_jaccard", "min"),
        )
    )
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    scenarios.to_csv(output_directory / "od_scenarios.csv", index=False)
    candidate_metadata.to_csv(
        output_directory / "candidate_routes.csv", index=False
    )
    pairwise.to_csv(
        output_directory / "route_diversity_pairwise.csv", index=False
    )
    diversity_summary.to_csv(
        output_directory / "route_diversity_summary.csv", index=False
    )
    route_summary.to_csv(
        output_directory / "candidate_route_exposure.csv", index=False
    )
    pd.DataFrame(segment_records).to_csv(
        output_directory / "segment_exposure.csv", index=False
    )
    feasible.to_csv(output_directory / "feasible_route_sets.csv", index=False)
    shortlist.to_csv(output_directory / "shortlist.csv", index=False)
    decisions.to_csv(output_directory / "selected_routes.csv", index=False)
    regret.to_csv(output_directory / "decision_regret.csv", index=False)
    feasibility.to_csv(
        output_directory / "feasibility_summary.csv", index=False
    )
    ranking_rows.to_csv(
        output_directory / "expanded_route_ranking.csv", index=False
    )
    ranking_quality.to_csv(
        output_directory / "ranking_quality.csv", index=False
    )
    (output_directory / "readiness_decision.json").write_text(
        json.dumps(asdict(decision), indent=2), encoding="utf-8"
    )
    _plot_outputs(decisions, ranking_quality, feasibility, output_directory)

    shortlist_sample = shortlist.loc[
        shortlist["delta_time_allowed_minutes"].isin((0.0, 3.0, 10.0))
    ].head(24)
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_report(
            scenarios,
            diversity_summary,
            feasibility,
            shortlist_sample,
            decisions,
            regret,
            ranking_quality,
            decision,
        ),
        encoding="utf-8",
    )
    return {
        "scenarios": scenarios,
        "candidate_metadata": candidate_metadata,
        "pairwise_diversity": pairwise,
        "diversity_summary": diversity_summary,
        "route_summary": route_summary,
        "feasible": feasible,
        "shortlist": shortlist,
        "decisions": decisions,
        "regret": regret,
        "feasibility": feasibility,
        "ranking_rows": ranking_rows,
        "ranking_quality": ranking_quality,
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
        "--output-directory", default="data/processed/optimization"
    )
    parser.add_argument("--report", default="reports/constrained_routing.md")
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    outputs = generate_optimization_outputs(
        prediction_csv=arguments.predictions,
        network_path=arguments.network,
        output_directory=arguments.output_directory,
        report_path=arguments.report,
    )
    print(outputs["feasibility"].to_string(index=False))
    print(outputs["regret"].to_string(index=False))
    print(outputs["decision"])


if __name__ == "__main__":
    main()
