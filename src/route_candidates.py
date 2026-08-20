"""Mode-specific K-shortest candidate routes over the pilot OSM graph."""

from __future__ import annotations

import heapq
from dataclasses import asdict, dataclass
from itertools import count
from typing import Mapping, Sequence

from .eta_engine import edge_duration_seconds, speed_for_mode
from .road_network import RoadEdge, RoadNetwork, ensure_supported_location, validate_mode
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
