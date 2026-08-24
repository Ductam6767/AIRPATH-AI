"""Transparent constant-speed segment ETA propagation for candidate routes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final, Mapping, Protocol, Sequence

import numpy as np
import pandas as pd

from .road_network import RoadEdge, RoadNetwork, validate_mode
from .spatial_estimation import haversine_distance_km


DEFAULT_MODE_SPEED_KMH: Final[dict[str, float]] = {
    "walking": 5.0,
    "motorbike": 25.0,
}


class RouteLike(Protocol):
    route_id: str
    mode: str
    node_ids: Sequence[int]
    edge_ids: Sequence[str]
    total_distance_m: float
    total_travel_time_seconds: float


@dataclass(frozen=True)
class SegmentETA:
    """One ordered edge and its baseline passage timestamps."""

    route_id: str
    segment_index: int
    edge_id: str
    start_node: int
    end_node: int
    road_type: str
    direction: str
    mode: str
    segment_geometry: tuple[tuple[float, float], ...]
    representative_latitude: float
    representative_longitude: float
    segment_duration_seconds: float
    entry_elapsed_seconds: float
    cumulative_elapsed_seconds: float
    entry_timestamp: pd.Timestamp
    target_arrival_timestamp: pd.Timestamp
    estimated_arrival_timestamp: pd.Timestamp

    def spatial_target(self) -> dict[str, object]:
        """Return the exact future input contract for spatial PM2.5 estimation."""
        return {
            "latitude": self.representative_latitude,
            "longitude": self.representative_longitude,
            "target_time": self.target_arrival_timestamp,
        }

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["segment_geometry"] = [
            list(point) for point in self.segment_geometry
        ]
        for key in (
            "entry_timestamp",
            "target_arrival_timestamp",
            "estimated_arrival_timestamp",
        ):
            payload[key] = payload[key].isoformat()
        return payload


def speed_for_mode(mode: str, speed_kmh: float | None = None) -> float:
    validate_mode(mode)
    speed = DEFAULT_MODE_SPEED_KMH[mode] if speed_kmh is None else float(speed_kmh)
    if not np.isfinite(speed) or speed <= 0:
        raise ValueError("Mode speed must be a positive finite value in km/h.")
    return speed


def edge_duration_seconds(length_m: float, speed_kmh: float) -> float:
    length = float(length_m)
    speed = float(speed_kmh)
    if not np.isfinite(length) or length < 0:
        raise ValueError("Edge length must be a non-negative finite value.")
    if not np.isfinite(speed) or speed <= 0:
        raise ValueError("Mode speed must be a positive finite value in km/h.")
    return length / (speed * 1000 / 3600)


def _geometry_midpoint(
    geometry: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    if len(geometry) < 2:
        raise ValueError("Segment geometry requires at least two coordinates.")
    lengths = [
        haversine_distance_km(*start, *end) * 1000
        for start, end in zip(geometry, geometry[1:])
    ]
    total = sum(lengths)
    if total <= 0:
        return tuple(map(float, geometry[0]))
    target = total / 2
    elapsed = 0.0
    for (start, end), length in zip(zip(geometry, geometry[1:]), lengths):
        if elapsed + length >= target:
            fraction = (target - elapsed) / length
            return (
                float(start[0] + fraction * (end[0] - start[0])),
                float(start[1] + fraction * (end[1] - start[1])),
            )
        elapsed += length
    return tuple(map(float, geometry[-1]))


def _normalise_departure_time(departure_time: object) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(departure_time)
    except (TypeError, ValueError) as error:
        raise ValueError("departure_time must be a valid exact timestamp.") from error
    if pd.isna(timestamp):
        raise ValueError("departure_time must not be missing.")
    return timestamp


def propagate_segment_etas(
    network: RoadNetwork,
    route: RouteLike,
    departure_time: object,
    *,
    speed_kmh: float | None = None,
) -> list[SegmentETA]:
    """Propagate constant-speed ETA to each segment midpoint and endpoint.

    `target_arrival_timestamp` is the estimated midpoint passage time used by
    the future spatial PM2.5 interface. `estimated_arrival_timestamp` is the
    segment-end time, and `cumulative_elapsed_seconds` is measured to that end.
    """
    validate_mode(route.mode)
    departure = _normalise_departure_time(departure_time)
    speed = speed_for_mode(route.mode, speed_kmh)
    if not route.edge_ids:
        raise ValueError("A route must contain at least one edge.")
    if len(route.node_ids) != len(route.edge_ids) + 1:
        raise ValueError("Route node/edge counts are inconsistent.")

    cumulative = 0.0
    segments: list[SegmentETA] = []
    for segment_index, edge_id in enumerate(route.edge_ids, start=1):
        if edge_id not in network.edges:
            raise ValueError(f"Unknown route edge: {edge_id}")
        edge: RoadEdge = network.edges[edge_id]
        expected_start = int(route.node_ids[segment_index - 1])
        expected_end = int(route.node_ids[segment_index])
        if (edge.start_node, edge.end_node) != (expected_start, expected_end):
            raise ValueError("Route edge order does not match its node sequence.")
        if not edge.allows(route.mode):
            raise ValueError(f"Edge {edge_id} is not traversable by {route.mode}.")
        duration = edge_duration_seconds(edge.length_m, speed)
        entry_elapsed = cumulative
        cumulative += duration
        midpoint_elapsed = entry_elapsed + duration / 2
        midpoint = _geometry_midpoint(edge.geometry)
        segments.append(
            SegmentETA(
                route_id=route.route_id,
                segment_index=segment_index,
                edge_id=edge.edge_id,
                start_node=edge.start_node,
                end_node=edge.end_node,
                road_type=edge.road_type,
                direction=edge.direction,
                mode=route.mode,
                segment_geometry=edge.geometry,
                representative_latitude=midpoint[0],
                representative_longitude=midpoint[1],
                segment_duration_seconds=duration,
                entry_elapsed_seconds=entry_elapsed,
                cumulative_elapsed_seconds=cumulative,
                entry_timestamp=departure
                + pd.to_timedelta(entry_elapsed, unit="s"),
                target_arrival_timestamp=departure
                + pd.to_timedelta(midpoint_elapsed, unit="s"),
                estimated_arrival_timestamp=departure
                + pd.to_timedelta(cumulative, unit="s"),
            )
        )
    return segments


def validate_segment_etas(
    route: RouteLike,
    segments: Sequence[SegmentETA],
    *,
    tolerance_seconds: float = 1e-6,
) -> None:
    """Raise if connectivity, monotonicity, or total-time invariants fail."""
    if len(segments) != len(route.edge_ids):
        raise ValueError("Segment ETA count differs from route edge count.")
    for index, segment in enumerate(segments):
        if segment.edge_id != route.edge_ids[index]:
            raise ValueError("Segment ETA edge order differs from route.")
        if segment.segment_duration_seconds < 0:
            raise ValueError("Segment duration cannot be negative.")
        if index:
            previous = segments[index - 1]
            if segment.start_node != previous.end_node:
                raise ValueError("Segment ETA sequence is disconnected.")
            if (
                segment.cumulative_elapsed_seconds
                < previous.cumulative_elapsed_seconds
                or segment.target_arrival_timestamp
                < previous.target_arrival_timestamp
                or segment.estimated_arrival_timestamp
                < previous.estimated_arrival_timestamp
            ):
                raise ValueError("Segment ETA sequence must be monotonic.")
    duration_sum = sum(segment.segment_duration_seconds for segment in segments)
    if abs(duration_sum - route.total_travel_time_seconds) > tolerance_seconds:
        raise ValueError("Route total time differs from segment-duration sum.")
    if abs(
        segments[-1].cumulative_elapsed_seconds - route.total_travel_time_seconds
    ) > tolerance_seconds:
        raise ValueError("Final cumulative ETA differs from route total time.")


def spatial_target_records(
    segments: Sequence[SegmentETA],
) -> list[dict[str, object]]:
    """Prepare segment X/T records without calling the spatial estimator."""
    return [
        {
            "route_id": segment.route_id,
            "segment_index": segment.segment_index,
            "edge_id": segment.edge_id,
            **segment.spatial_target(),
        }
        for segment in segments
    ]
