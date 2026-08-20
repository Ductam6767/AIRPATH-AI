"""Mode-specific K-shortest candidate routes over the pilot OSM graph."""

from __future__ import annotations

import heapq
import gzip
import io
import json
from dataclasses import asdict, dataclass
from itertools import count
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .eta_engine import (
    DEFAULT_MODE_SPEED_KMH,
    edge_duration_seconds,
    propagate_segment_etas,
    spatial_target_records,
    speed_for_mode,
    validate_segment_etas,
)
from .road_network import (
    MODES,
    PILOT_POLYGON,
    RoadNetwork,
    ensure_supported_location,
    load_network,
    road_type_counts,
    validate_mode,
)
from .spatial_estimation import STATION_BY_ID
from .spatial_estimation import haversine_distance_km


class RouteNotFoundError(ValueError):
    """Raised when two supported locations are disconnected for a mode."""


@dataclass(frozen=True)
class CandidateRoute:
    route_id: str
    mode: str
    origin: tuple[float, float]
    destination: tuple[float, float]
    origin_node: int
    destination_node: int
    origin_snap_distance_m: float
    destination_snap_distance_m: float
    node_ids: tuple[int, ...]
    edge_ids: tuple[str, ...]
    geometry: tuple[tuple[float, float], ...]
    total_distance_m: float
    total_travel_time_seconds: float

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["origin"] = list(self.origin)
        payload["destination"] = list(self.destination)
        payload["node_ids"] = list(self.node_ids)
        payload["edge_ids"] = list(self.edge_ids)
        payload["geometry"] = [list(point) for point in self.geometry]
        return payload


@dataclass(frozen=True)
class _Path:
    node_ids: tuple[int, ...]
    edge_ids: tuple[str, ...]
    cost_seconds: float


def _shortest_path(
    network: RoadNetwork,
    start_node: int,
    destination_node: int,
    mode: str,
    speed_kmh: float,
    *,
    banned_edge_ids: frozenset[str] = frozenset(),
    banned_node_ids: frozenset[int] = frozenset(),
) -> _Path | None:
    if start_node in banned_node_ids or destination_node in banned_node_ids:
        return None
    if start_node == destination_node:
        return _Path((start_node,), (), 0.0)

    queue: list[
        tuple[float, int, int, tuple[str, ...], tuple[int, ...]]
    ] = []
    sequence = count()
    heapq.heappush(queue, (0.0, next(sequence), start_node, (), (start_node,)))
    best_cost: dict[int, float] = {start_node: 0.0}

    while queue:
        cost, _, node_id, edge_ids, node_ids = heapq.heappop(queue)
        if cost > best_cost.get(node_id, float("inf")) + 1e-12:
            continue
        if node_id == destination_node:
            return _Path(node_ids, edge_ids, cost)
        for edge in network.outgoing_edges(node_id, mode):
            if edge.edge_id in banned_edge_ids:
                continue
            next_node = edge.end_node
            if next_node in banned_node_ids or next_node in node_ids:
                continue
            next_cost = cost + edge_duration_seconds(edge.length_m, speed_kmh)
            if next_cost + 1e-12 >= best_cost.get(next_node, float("inf")):
                continue
            best_cost[next_node] = next_cost
            heapq.heappush(
                queue,
                (
                    next_cost,
                    next(sequence),
                    next_node,
                    edge_ids + (edge.edge_id,),
                    node_ids + (next_node,),
                ),
            )
    return None


def _route_geometry(
    network: RoadNetwork,
    edge_ids: Sequence[str],
) -> tuple[tuple[float, float], ...]:
    if not edge_ids:
        return ()
    geometry: list[tuple[float, float]] = []
    previous_end: int | None = None
    for edge_id in edge_ids:
        edge = network.edges[edge_id]
        if previous_end is not None and edge.start_node != previous_end:
            raise ValueError("Route edge order is disconnected.")
        if geometry and geometry[-1] != edge.geometry[0]:
            raise ValueError("Ordered edge geometries do not share endpoints.")
        geometry.extend(edge.geometry if not geometry else edge.geometry[1:])
        previous_end = edge.end_node
    return tuple(geometry)


def _candidate_from_path(
    network: RoadNetwork,
    path: _Path,
    *,
    route_number: int,
    mode: str,
    speed_kmh: float,
    origin: tuple[float, float],
    destination: tuple[float, float],
    origin_node: int,
    destination_node: int,
) -> CandidateRoute:
    edges = [network.edges[edge_id] for edge_id in path.edge_ids]
    origin_road_node = network.nodes[origin_node]
    destination_road_node = network.nodes[destination_node]
    return CandidateRoute(
        route_id=f"{mode}-{route_number}",
        mode=mode,
        origin=origin,
        destination=destination,
        origin_node=origin_node,
        destination_node=destination_node,
        origin_snap_distance_m=1000
        * haversine_distance_km(
            origin[0],
            origin[1],
            origin_road_node.latitude,
            origin_road_node.longitude,
        ),
        destination_snap_distance_m=1000
        * haversine_distance_km(
            destination[0],
            destination[1],
            destination_road_node.latitude,
            destination_road_node.longitude,
        ),
        node_ids=path.node_ids,
        edge_ids=path.edge_ids,
        geometry=_route_geometry(network, path.edge_ids),
        total_distance_m=float(sum(edge.length_m for edge in edges)),
        total_travel_time_seconds=float(
            sum(edge_duration_seconds(edge.length_m, speed_kmh) for edge in edges)
        ),
    )


def _path_from_edges(network: RoadNetwork, edge_ids: Sequence[str]) -> _Path:
    if not edge_ids:
        raise ValueError("A candidate route requires at least one edge.")
    edges = [network.edges[edge_id] for edge_id in edge_ids]
    nodes = [edges[0].start_node]
    total_seconds = 0.0
    for edge in edges:
        if edge.start_node != nodes[-1]:
            raise ValueError("Candidate path edges are disconnected.")
        nodes.append(edge.end_node)
        total_seconds += edge.length_m
    # `cost_seconds` is replaced by the caller because this helper is speed agnostic.
    return _Path(tuple(nodes), tuple(edge_ids), total_seconds)


def k_shortest_paths(
    network: RoadNetwork,
    start_node: int,
    destination_node: int,
    mode: str,
    *,
    k: int = 5,
    speed_kmh: float | None = None,
) -> list[_Path]:
    """Yen-style loopless K-shortest paths with deterministic tie-breaking."""
    validate_mode(mode)
    if k <= 0:
        raise ValueError("k must be positive.")
    speed = speed_for_mode(mode, speed_kmh)
    first = _shortest_path(
        network, start_node, destination_node, mode, speed
    )
    if first is None or not first.edge_ids:
        return []
    accepted = [first]
    accepted_keys = {first.edge_ids}
    candidates: list[tuple[float, float, tuple[str, ...], _Path]] = []
    candidate_keys: set[tuple[str, ...]] = set()

    while len(accepted) < k:
        previous = accepted[-1]
        for spur_index in range(len(previous.node_ids) - 1):
            root_nodes = previous.node_ids[: spur_index + 1]
            root_edges = previous.edge_ids[:spur_index]
            banned_edges: set[str] = set()
            for accepted_path in accepted:
                if (
                    accepted_path.node_ids[: spur_index + 1] == root_nodes
                    and len(accepted_path.edge_ids) > spur_index
                ):
                    banned_edges.add(accepted_path.edge_ids[spur_index])
            spur = _shortest_path(
                network,
                root_nodes[-1],
                destination_node,
                mode,
                speed,
                banned_edge_ids=frozenset(banned_edges),
                banned_node_ids=frozenset(root_nodes[:-1]),
            )
            if spur is None:
                continue
            edge_ids = root_edges + spur.edge_ids
            if edge_ids in accepted_keys or edge_ids in candidate_keys:
                continue
            path = _path_from_edges(network, edge_ids)
            cost = sum(
                edge_duration_seconds(network.edges[edge_id].length_m, speed)
                for edge_id in edge_ids
            )
            path = _Path(path.node_ids, path.edge_ids, cost)
            distance = sum(network.edges[edge_id].length_m for edge_id in edge_ids)
            heapq.heappush(candidates, (cost, distance, edge_ids, path))
            candidate_keys.add(edge_ids)
        if not candidates:
            break
        _, _, edge_ids, selected = heapq.heappop(candidates)
        candidate_keys.discard(edge_ids)
        accepted.append(selected)
        accepted_keys.add(selected.edge_ids)
    return accepted


def generate_candidate_routes(
    network: RoadNetwork,
    origin: tuple[float, float],
    destination: tuple[float, float],
    mode: str,
    *,
    k: int = 5,
    speed_kmh: float | None = None,
) -> list[CandidateRoute]:
    """Generate distance/time-only alternatives; no PM2.5 ranking is applied."""
    validate_mode(mode)
    ensure_supported_location(*origin)
    ensure_supported_location(*destination)
    if origin == destination:
        raise ValueError("Origin and destination must differ.")
    speed = speed_for_mode(mode, speed_kmh)
    origin_node = network.nearest_node(*origin, mode)
    destination_node = network.nearest_node(*destination, mode)
    if origin_node == destination_node:
        raise ValueError("Origin and destination snap to the same road node.")
    paths = k_shortest_paths(
        network,
        origin_node,
        destination_node,
        mode,
        k=k,
        speed_kmh=speed,
    )
    if not paths:
        raise RouteNotFoundError(
            f"No connected {mode} route exists inside the supported pilot network."
        )
    return [
        _candidate_from_path(
            network,
            path,
            route_number=index,
            mode=mode,
            speed_kmh=speed,
            origin=origin,
            destination=destination,
            origin_node=origin_node,
            destination_node=destination_node,
        )
        for index, path in enumerate(paths, start=1)
    ]


def route_summary(routes: Sequence[CandidateRoute]) -> list[dict[str, object]]:
    return [
        {
            "route_id": route.route_id,
            "mode": route.mode,
            "edge_count": len(route.edge_ids),
            "total_distance_m": route.total_distance_m,
            "total_travel_time_seconds": route.total_travel_time_seconds,
            "origin_snap_distance_m": route.origin_snap_distance_m,
            "destination_snap_distance_m": route.destination_snap_distance_m,
        }
        for route in routes
    ]


EXAMPLE_ORIGIN = (
    STATION_BY_ID[6].latitude,
    STATION_BY_ID[6].longitude,
)
EXAMPLE_DESTINATION = (
    STATION_BY_ID[5].latitude,
    STATION_BY_ID[5].longitude,
)
EXAMPLE_DEPARTURE_TIME = pd.Timestamp("2026-08-20 08:00:00+07:00")


def _save_json_gzip(payload: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw_handle, mtime=0
        ) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8") as handle:
                json.dump(
                    payload, handle, separators=(",", ":"), sort_keys=True
                )


def _plot_network_overview(network: RoadNetwork, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 7))
    drawn_segments: set[tuple[int, int]] = set()
    for edge in network.edges.values():
        segment_key = tuple(sorted((edge.start_node, edge.end_node)))
        if segment_key in drawn_segments:
            continue
        drawn_segments.add(segment_key)
        axis.plot(
            [point[1] for point in edge.geometry],
            [point[0] for point in edge.geometry],
            color="#7f8c8d",
            alpha=0.22,
            linewidth=0.25,
        )
    closed_polygon = PILOT_POLYGON + PILOT_POLYGON[:1]
    axis.plot(
        [point[1] for point in closed_polygon],
        [point[0] for point in closed_polygon],
        color="#c62828",
        linewidth=1.6,
        label="Validated stations 2–6 convex hull",
    )
    for station_id in (2, 3, 4, 5, 6):
        station = STATION_BY_ID[station_id]
        axis.scatter(
            station.longitude,
            station.latitude,
            color="#0d47a1",
            s=35,
            zorder=3,
        )
        axis.annotate(
            f"S{station_id}",
            (station.longitude, station.latitude),
            xytext=(4, 4),
            textcoords="offset points",
        )
    axis.set(
        xlabel="Longitude (°E)",
        ylabel="Latitude (°N)",
        title="Processed OpenStreetMap pilot road network",
    )
    axis.legend(loc="best")
    axis.grid(alpha=0.15)
    figure.text(
        0.01,
        0.01,
        "© OpenStreetMap contributors, ODbL 1.0",
        fontsize=8,
    )
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def _plot_candidate_routes(
    routes_by_mode: dict[str, list[CandidateRoute]],
    output_path: Path,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True)
    colors = ("#1565c0", "#ef6c00", "#2e7d32", "#6a1b9a", "#c62828")
    for axis, mode in zip(axes, MODES):
        for color, route in zip(colors, routes_by_mode[mode]):
            axis.plot(
                [point[1] for point in route.geometry],
                [point[0] for point in route.geometry],
                color=color,
                linewidth=1.5,
                alpha=0.85,
                label=f"{route.route_id}: {route.total_distance_m / 1000:.2f} km",
            )
        axis.scatter(
            [EXAMPLE_ORIGIN[1], EXAMPLE_DESTINATION[1]],
            [EXAMPLE_ORIGIN[0], EXAMPLE_DESTINATION[0]],
            color=["black", "#d50000"],
            s=50,
            zorder=4,
        )
        axis.annotate("A / S6", (EXAMPLE_ORIGIN[1], EXAMPLE_ORIGIN[0]))
        axis.annotate("B / S5", (EXAMPLE_DESTINATION[1], EXAMPLE_DESTINATION[0]))
        axis.set_title(
            f"{mode.title()} candidates "
            f"({DEFAULT_MODE_SPEED_KMH[mode]:g} km/h baseline)"
        )
        axis.set_xlabel("Longitude (°E)")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=7)
    axes[0].set_ylabel("Latitude (°N)")
    figure.suptitle("K=5 distance/time-only route alternatives (no PM2.5 ranking)")
    figure.text(
        0.01,
        0.01,
        "© OpenStreetMap contributors, ODbL 1.0",
        fontsize=8,
    )
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def _markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    display = frame.copy()
    numeric = display.select_dtypes(include="number").columns
    display[numeric] = display[numeric].round(digits)
    return display.to_markdown(index=False)


def _render_report(
    network: RoadNetwork,
    route_summary_frame: pd.DataFrame,
    segment_frame: pd.DataFrame,
) -> str:
    metadata = network.metadata
    mode_count_rows = [
        {"mode": mode, **network.mode_counts(mode)}
        for mode in MODES
    ]
    road_rows = [
        {
            "mode": mode,
            "road_type": road_type,
            "directed_edges": edge_count,
        }
        for mode in MODES
        for road_type, edge_count in road_type_counts(network, mode).items()
    ]
    example_segments = pd.concat(
        [
            segment_frame.loc[
                segment_frame["route_id"].eq("motorbike-1")
            ].head(8),
            segment_frame.loc[
                segment_frame["route_id"].eq("motorbike-1")
            ].tail(2),
        ]
    )
    segment_columns = [
        "segment_index",
        "edge_id",
        "start_node",
        "end_node",
        "segment_duration_seconds",
        "cumulative_elapsed_seconds",
        "target_arrival_timestamp",
        "estimated_arrival_timestamp",
        "representative_latitude",
        "representative_longitude",
    ]
    return f"""# AIRPATH-AI Milestone 3B — road network and segment ETA foundation

## Scope

This milestone builds only the bounded road/route/ETA bridge needed for future
`PM2.5(X, T)` calls. It does **not** query PM2.5, calculate exposure, optimize
routes, recommend a route, estimate traffic, or build a web application.

## A–B. Pilot network size and graph representation

The network is restricted to the Milestone 3A convex hull of HealthyAir stations
2–6 (approximately 54.9 km²). It contains **{len(network.nodes):,} OSM vertices**
and **{len(network.edges):,} directed segment records** before selecting a mode.

{_markdown_table(pd.DataFrame(mode_count_rows), 0)}

Nodes are OSM road vertices. Directed edges are consecutive OSM way-node
segments and retain geometry, haversine length, `highway` type, way ID, name,
surface, maxspeed text when available, OSM direction, and walking/motorbike
traversability. The graph is not collapsed to one route polyline.

## Data source and reproducibility

- Source: [OpenStreetMap](https://www.openstreetmap.org), © OpenStreetMap
  contributors, ODbL 1.0.
- Retrieval: bounded Overpass QL query through `{metadata.get("overpass_endpoint")}`.
- OSM database timestamp: **{metadata.get("osm_snapshot_timestamp")}**.
- Retrieval timestamp: **{metadata.get("retrieved_at_utc")}**.
- CRS: **WGS84 geographic coordinates, EPSG:4326**.
- Retained ways: **{int(metadata.get("retained_osm_ways", 0)):,}**.
- Filter profile: **{metadata.get("filter_rule_version")}**.
- AOI checksum: `{metadata.get("pilot_polygon_sha256")}`.
- Canonical Overpass-response checksum:
  `{metadata.get("overpass_response_sha256")}`.
- Reproducible query and polygon are saved in
  `data/processed/road_network/metadata.json`.

The query uses the polygon's enclosing bounding box to avoid missing ways that
cross its boundary; local filtering then retains only segments whose endpoints
and midpoint lie in the validated polygon. General, directional, and
mode-specific `access`, `foot`, `vehicle`, `motor_vehicle`, and `motorcycle`
restrictions are applied. Restricted/end-access and unknown explicit values are
excluded from through-routing. Ways with unevaluated conditional access are
excluded conservatively. Barrier nodes are applied by mode. Vehicle oneway
direction is respected for motorbikes; ordinary vehicle oneway tags do not
restrict walking unless a specific pedestrian-direction tag says so.

## C. Supported road types

{_markdown_table(pd.DataFrame(road_rows), 0)}

Walking excludes motorways/trunks and honors explicit pedestrian prohibitions.
Motorbike excludes footways, paths, pedestrian ways, cycleways, and steps and
honors explicit motorcycle/motor-vehicle prohibitions. OSM tagging is incomplete,
so “allowed” means not clearly prohibited by the retained tags; it is not a
guarantee of current legal or physical access. The declared allow-list is a
conservative research profile, not a complete Vietnam legal-access model.

## D–E. Baseline travel-time assumptions

| Mode | Configurable default | Interpretation |
|---|---:|---|
| Walking | **5 km/h** | Constant ordinary walking baseline |
| Motorbike | **25 km/h** | Constant urban research-prototype baseline |

For each edge, `duration = length / mode_speed`. These assumptions are explicit
in `DEFAULT_MODE_SPEED_KMH` and can be overridden per call. They do not use live
traffic, signals, intersection delay, congestion, slope, or user behavior and
must not be presented as real-world ETA accuracy.

## F. Candidate-route generation

`generate_candidate_routes()` snaps supported endpoints to the nearest
mode-traversable nodes and applies a deterministic loopless Yen-style K-shortest
path algorithm. Edge cost is constant-speed travel time; with one fixed speed
per mode this is equivalent to distance ranking. `K=5` is used. No air-quality
value enters generation or ranking.

## G. Example candidates

The reproducible example travels from station 6 (A) to station 5 (B), with both
coordinates inside the pilot polygon.

{_markdown_table(route_summary_frame, 3)}

The five alternatives can differ only slightly because OSM contains parallel
carriageways and dense short vertices. They are algorithmic alternatives, not
claims of five materially distinct traveler choices.

## H. Segment-level ETA example

Departure is **{EXAMPLE_DEPARTURE_TIME.isoformat()}**. The following rows show
the first eight and final two segments of motorbike route 1:

{_markdown_table(example_segments[segment_columns], 6)}

For each segment:

- `entry_timestamp` is arrival at its start node;
- `target_arrival_timestamp` is estimated passage at its geometry midpoint;
- `estimated_arrival_timestamp` is arrival at its end node;
- `cumulative_elapsed_seconds` is measured through the segment end.

All route/segment records are saved under `data/processed/road_network/`.

## I. Validation

`tests/test_road_network_eta.py` verifies:

- pilot-boundary rejection;
- mode and oneway filtering;
- network serialization;
- five distinct connected route edge sequences;
- ordered edges and consistent geometry;
- non-negative durations;
- monotonic elapsed times and timestamps;
- route total time equals the segment-duration sum;
- walking and motorbike produce different baseline ETAs;
- unsupported car mode is rejected.

The real OSM station-6-to-station-5 example also produces five routes for each
supported mode. This is an implementation sanity check, not validation against
observed journeys.

## J. Known limitations

1. OSM is volunteered and changes over time; tags can be incomplete or stale.
2. Turn-restriction relations are not yet interpreted; ways with relevant
   unevaluated conditional access are excluded rather than guessed.
3. Endpoints are snapped to road nodes; connector walking/riding time is
   reported as snap distance but not added to route duration.
4. Constant speeds omit traffic, signals, turns, slope, surface effects, and
   intersection delay.
5. K-shortest alternatives may overlap heavily and are not diversity-optimized.
6. Every OSM shape vertex is a graph node, so routes contain many short segments.
7. The network boundary is a scientific-support boundary, not an administrative
   service area or guarantee of spatial PM2.5 accuracy.
8. Exact second-level ETAs do not imply minute-level PM2.5 observations or
   predictions; current HealthyAir support remains hourly.

## K. Route-to-spatial interface

`spatial_target_records(segment_etas)` returns one record per ordered segment:

```python
{{
    "route_id": ...,
    "segment_index": ...,
    "edge_id": ...,
    "latitude": representative_midpoint_latitude,
    "longitude": representative_midpoint_longitude,
    "target_time": estimated_midpoint_passage_timestamp,
}}
```

These fields are structurally compatible with:

```python
estimate_pm25(latitude, longitude, target_time, station_values)
```

Milestone 3B deliberately does not call that function and does not source
`station_values`.

## L. Recommended next milestone

The next milestone should integrate **forecasted station values at each segment
target time** with the existing spatial estimator and quantify compounded
forecast-plus-spatial error. Exposure aggregation or route recommendation should
begin only after its temporal alignment, uncertainty propagation, and pilot-area
boundary behavior are validated.
"""


def generate_milestone_outputs(
    network_path: str | Path = (
        "data/processed/road_network/healthyair_pilot_osm.json.gz"
    ),
    *,
    processed_directory: str | Path = "data/processed/road_network",
    report_root: str | Path = "reports",
    k: int = 5,
    departure_time: object = EXAMPLE_DEPARTURE_TIME,
) -> dict[str, object]:
    """Generate reproducible real-network routes, ETAs, figures, and report."""
    network = load_network(network_path)
    processed_directory = Path(processed_directory)
    report_root = Path(report_root)
    table_directory = report_root / "tables"
    figure_directory = report_root / "figures"
    processed_directory.mkdir(parents=True, exist_ok=True)
    table_directory.mkdir(parents=True, exist_ok=True)
    figure_directory.mkdir(parents=True, exist_ok=True)

    routes_by_mode = {
        mode: generate_candidate_routes(
            network,
            EXAMPLE_ORIGIN,
            EXAMPLE_DESTINATION,
            mode,
            k=k,
        )
        for mode in MODES
    }
    if any(len(routes) < k for routes in routes_by_mode.values()):
        raise RouteNotFoundError("The real pilot example did not produce K routes.")

    all_routes = [
        route for mode in MODES for route in routes_by_mode[mode]
    ]
    all_segments = []
    for route in all_routes:
        segments = propagate_segment_etas(network, route, departure_time)
        validate_segment_etas(route, segments)
        all_segments.extend(segments)
    route_rows = route_summary(all_routes)
    segment_rows = [segment.to_dict() for segment in all_segments]
    target_rows = spatial_target_records(all_segments)

    _save_json_gzip(
        [route.to_dict() for route in all_routes],
        processed_directory / "example_candidate_routes.json.gz",
    )
    _save_json_gzip(
        segment_rows,
        processed_directory / "example_segment_etas.json.gz",
    )
    _save_json_gzip(
        [
            {
                **row,
                "target_time": pd.Timestamp(row["target_time"]).isoformat(),
            }
            for row in target_rows
        ],
        processed_directory / "example_spatial_targets.json.gz",
    )
    route_frame = pd.DataFrame(route_rows)
    segment_frame = pd.DataFrame(segment_rows)
    route_frame.to_csv(
        table_directory / "road_network_example_routes.csv", index=False
    )
    segment_frame.to_csv(
        table_directory / "road_network_segment_eta_example.csv", index=False
    )
    _plot_network_overview(
        network, figure_directory / "road_network_pilot.png"
    )
    _plot_candidate_routes(
        routes_by_mode, figure_directory / "road_network_candidate_routes.png"
    )
    (report_root / "road_network_eta.md").write_text(
        _render_report(network, route_frame, segment_frame),
        encoding="utf-8",
    )
    return {
        "network": network,
        "routes_by_mode": routes_by_mode,
        "routes": all_routes,
        "segments": all_segments,
        "route_summary": route_frame,
        "segment_table": segment_frame,
        "spatial_targets": target_rows,
    }
