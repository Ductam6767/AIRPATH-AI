"""Reproducible OpenStreetMap road network for the HealthyAir pilot area."""

from __future__ import annotations

import argparse
import gzip
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Iterable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .spatial_estimation import STATION_BY_ID, haversine_distance_km


OSM_SOURCE_URL: Final[str] = "https://www.openstreetmap.org"
DEFAULT_OVERPASS_URL: Final[str] = "https://overpass-api.de/api/interpreter"
OSM_LICENSE: Final[str] = "OpenStreetMap contributors, ODbL 1.0"
MODES: Final[tuple[str, str]] = ("walking", "motorbike")

# The validated Milestone 3A support polygon is the convex hull of stations 2–6.
# Station 6 lies inside the hull, so the boundary vertices are 2, 3, 4, and 5.
PILOT_STATION_IDS: Final[tuple[int, ...]] = (2, 3, 4, 5, 6)
PILOT_POLYGON: Final[tuple[tuple[float, float], ...]] = (
    (STATION_BY_ID[2].latitude, STATION_BY_ID[2].longitude),
    (STATION_BY_ID[3].latitude, STATION_BY_ID[3].longitude),
    (STATION_BY_ID[4].latitude, STATION_BY_ID[4].longitude),
    (STATION_BY_ID[5].latitude, STATION_BY_ID[5].longitude),
)

WALKING_HIGHWAYS: Final[frozenset[str]] = frozenset(
    {
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "unclassified",
        "residential",
        "living_street",
        "service",
        "pedestrian",
        "footway",
        "path",
        "steps",
        "cycleway",
    }
)
MOTORBIKE_HIGHWAYS: Final[frozenset[str]] = frozenset(
    {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "unclassified",
        "residential",
        "living_street",
        "service",
    }
)
QUERY_HIGHWAYS: Final[frozenset[str]] = WALKING_HIGHWAYS | MOTORBIKE_HIGHWAYS
DENIED_ACCESS: Final[frozenset[str]] = frozenset({"no", "private"})
ALLOWED_ACCESS: Final[frozenset[str]] = frozenset(
    {"yes", "designated", "permissive", "official"}
)


class UnsupportedAreaError(ValueError):
    """Raised when a route endpoint is outside the validated pilot polygon."""


@dataclass(frozen=True)
class RoadNode:
    node_id: int
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RoadEdge:
    edge_id: str
    osm_way_id: int
    start_node: int
    end_node: int
    geometry: tuple[tuple[float, float], ...]
    length_m: float
    road_type: str
    name: str | None
    direction: str
    osm_oneway: str | None
    walking_allowed: bool
    motorbike_allowed: bool
    surface: str | None
    maxspeed: str | None

    def allows(self, mode: str) -> bool:
        validate_mode(mode)
        return self.walking_allowed if mode == "walking" else self.motorbike_allowed


@dataclass
class RoadNetwork:
    """Directed segment graph with mode-specific traversability."""

    nodes: dict[int, RoadNode]
    edges: dict[str, RoadEdge]
    metadata: dict[str, object]

    def __post_init__(self) -> None:
        self._adjacency: dict[str, dict[int, list[str]]] = {
            mode: {} for mode in MODES
        }
        for edge_id, edge in self.edges.items():
            for mode in MODES:
                if edge.allows(mode):
                    self._adjacency[mode].setdefault(edge.start_node, []).append(
                        edge_id
                    )
        for mode in MODES:
            for edge_ids in self._adjacency[mode].values():
                edge_ids.sort()

    def outgoing_edges(self, node_id: int, mode: str) -> tuple[RoadEdge, ...]:
        validate_mode(mode)
        return tuple(
            self.edges[edge_id]
            for edge_id in self._adjacency[mode].get(int(node_id), [])
        )

    def nearest_node(self, latitude: float, longitude: float, mode: str) -> int:
        """Snap an in-polygon location to the nearest mode-traversable node."""
        validate_mode(mode)
        ensure_supported_location(latitude, longitude)
        routable_nodes = set(self._adjacency[mode])
        routable_nodes.update(
            self.edges[edge_id].end_node
            for edge_ids in self._adjacency[mode].values()
            for edge_id in edge_ids
        )
        if not routable_nodes:
            raise ValueError(f"Road network has no traversable nodes for {mode}.")
        return min(
            routable_nodes,
            key=lambda node_id: (
                haversine_distance_km(
                    latitude,
                    longitude,
                    self.nodes[node_id].latitude,
                    self.nodes[node_id].longitude,
                ),
                node_id,
            ),
        )

    def mode_counts(self, mode: str) -> dict[str, int]:
        validate_mode(mode)
        mode_edges = [edge for edge in self.edges.values() if edge.allows(mode)]
        mode_nodes = {
            node_id
            for edge in mode_edges
            for node_id in (edge.start_node, edge.end_node)
        }
        return {"nodes": len(mode_nodes), "directed_edges": len(mode_edges)}

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": self.metadata,
            "nodes": [asdict(node) for node in self.nodes.values()],
            "edges": [
                {
                    **asdict(edge),
                    "geometry": [list(point) for point in edge.geometry],
                }
                for edge in self.edges.values()
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "RoadNetwork":
        node_rows = payload.get("nodes")
        edge_rows = payload.get("edges")
        if not isinstance(node_rows, list) or not isinstance(edge_rows, list):
            raise ValueError("Road network payload requires node and edge lists.")
        nodes = {
            int(row["node_id"]): RoadNode(
                node_id=int(row["node_id"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
            )
            for row in node_rows
            if isinstance(row, dict)
        }
        edges: dict[str, RoadEdge] = {}
        for row in edge_rows:
            if not isinstance(row, dict):
                continue
            edge = RoadEdge(
                edge_id=str(row["edge_id"]),
                osm_way_id=int(row["osm_way_id"]),
                start_node=int(row["start_node"]),
                end_node=int(row["end_node"]),
                geometry=tuple(
                    (float(point[0]), float(point[1]))
                    for point in row["geometry"]
                ),
                length_m=float(row["length_m"]),
                road_type=str(row["road_type"]),
                name=None if row.get("name") is None else str(row["name"]),
                direction=str(row["direction"]),
                osm_oneway=(
                    None
                    if row.get("osm_oneway") is None
                    else str(row["osm_oneway"])
                ),
                walking_allowed=bool(row["walking_allowed"]),
                motorbike_allowed=bool(row["motorbike_allowed"]),
                surface=(
                    None if row.get("surface") is None else str(row["surface"])
                ),
                maxspeed=(
                    None if row.get("maxspeed") is None else str(row["maxspeed"])
                ),
            )
            edges[edge.edge_id] = edge
        return cls(nodes=nodes, edges=edges, metadata=dict(payload.get("metadata", {})))


def validate_mode(mode: str) -> None:
    if mode not in MODES:
        raise ValueError("mode must be 'walking' or 'motorbike'; car is unsupported.")


def _point_on_segment(
    latitude: float,
    longitude: float,
    start: tuple[float, float],
    end: tuple[float, float],
    tolerance: float = 1e-10,
) -> bool:
    cross = (longitude - start[1]) * (end[0] - start[0]) - (
        latitude - start[0]
    ) * (end[1] - start[1])
    if abs(cross) > tolerance:
        return False
    return (
        min(start[0], end[0]) - tolerance
        <= latitude
        <= max(start[0], end[0]) + tolerance
        and min(start[1], end[1]) - tolerance
        <= longitude
        <= max(start[1], end[1]) + tolerance
    )


def point_in_pilot_area(latitude: float, longitude: float) -> bool:
    """Boundary-inclusive ray-casting test against the validated convex hull."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return False
    polygon = PILOT_POLYGON
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        if _point_on_segment(latitude, longitude, start, end):
            return True
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current[0] > latitude) != (previous[0] > latitude):
            crossing_longitude = (
                (previous[1] - current[1])
                * (latitude - current[0])
                / (previous[0] - current[0])
                + current[1]
            )
            if longitude < crossing_longitude:
                inside = not inside
        previous = current
    return inside


def ensure_supported_location(latitude: float, longitude: float) -> None:
    if not point_in_pilot_area(float(latitude), float(longitude)):
        raise UnsupportedAreaError(
            "Origin/destination is outside the validated HealthyAir stations "
            "2–6 pilot polygon; city-wide routing is unsupported."
        )


def _mode_access(tags: Mapping[str, str], mode: str) -> bool:
    validate_mode(mode)
    highway = tags.get("highway", "")
    allowed_highways = (
        WALKING_HIGHWAYS if mode == "walking" else MOTORBIKE_HIGHWAYS
    )
    if highway not in allowed_highways:
        return False

    mode_keys = (
        ("foot",)
        if mode == "walking"
        else ("motorcycle", "motor_vehicle", "vehicle")
    )
    for key in mode_keys:
        value = tags.get(key)
        if value in DENIED_ACCESS:
            return False
        if value in ALLOWED_ACCESS:
            return True
    return tags.get("access") not in DENIED_ACCESS


def _oneway_value(tags: Mapping[str, str], mode: str) -> str:
    if mode == "walking":
        return tags.get("oneway:foot", "no").lower()
    value = (
        tags.get("oneway:motorcycle")
        or tags.get("oneway:motor_vehicle")
        or tags.get("oneway")
    )
    if value is None and (
        tags.get("junction") == "roundabout"
        or tags.get("highway") in {"motorway", "motorway_link"}
    ):
        value = "yes"
    return (value or "no").lower()


def _direction_access(tags: Mapping[str, str], mode: str) -> tuple[bool, bool]:
    """Return allowed (OSM way direction, reverse direction)."""
    if not _mode_access(tags, mode):
        return False, False
    oneway = _oneway_value(tags, mode)
    if oneway in {"yes", "true", "1"}:
        return True, False
    if oneway == "-1":
        return False, True
    return True, True


def overpass_query() -> str:
    polygon = " ".join(f"{lat:.8f} {lon:.8f}" for lat, lon in PILOT_POLYGON)
    highway_pattern = "|".join(sorted(QUERY_HIGHWAYS))
    return (
        '[out:json][timeout:180];\n'
        f'way["highway"~"^({highway_pattern})$"](poly:"{polygon}");\n'
        "out body geom;"
    )


def retrieve_overpass(
    endpoint: str = DEFAULT_OVERPASS_URL,
    *,
    timeout_seconds: int = 240,
) -> dict[str, object]:
    """Retrieve a small bounded OSM highway extract through Overpass QL."""
    query = overpass_query()
    request = Request(
        endpoint,
        data=urlencode({"data": query}).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "AIRPATH-AI-research-prototype/3B",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise ValueError("Overpass response did not contain an elements list.")
    return payload


def _segment_supported(
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    return (
        point_in_pilot_area(*start)
        and point_in_pilot_area(*end)
        and point_in_pilot_area(*midpoint)
    )


def build_network_from_overpass(
    payload: Mapping[str, object],
    *,
    retrieval_time: datetime | None = None,
) -> RoadNetwork:
    """Convert Overpass ways into directed, mode-labelled OSM segments."""
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise ValueError("Overpass payload requires an elements list.")
    nodes: dict[int, RoadNode] = {}
    edges: dict[str, RoadEdge] = {}
    retained_way_ids: set[int] = set()

    for element in elements:
        if not isinstance(element, dict) or element.get("type") != "way":
            continue
        tags = {
            str(key): str(value)
            for key, value in dict(element.get("tags", {})).items()
        }
        walking_forward, walking_reverse = _direction_access(tags, "walking")
        motorbike_forward, motorbike_reverse = _direction_access(tags, "motorbike")
        if not any(
            (
                walking_forward,
                walking_reverse,
                motorbike_forward,
                motorbike_reverse,
            )
        ):
            continue
        node_ids = element.get("nodes")
        geometry = element.get("geometry")
        if not isinstance(node_ids, list) or not isinstance(geometry, list):
            continue
        if len(node_ids) != len(geometry) or len(node_ids) < 2:
            continue
        way_id = int(element["id"])
        for segment_index in range(len(node_ids) - 1):
            start_id = int(node_ids[segment_index])
            end_id = int(node_ids[segment_index + 1])
            start_geometry = geometry[segment_index]
            end_geometry = geometry[segment_index + 1]
            if not isinstance(start_geometry, dict) or not isinstance(
                end_geometry, dict
            ):
                continue
            start = (
                float(start_geometry["lat"]),
                float(start_geometry["lon"]),
            )
            end = (float(end_geometry["lat"]), float(end_geometry["lon"]))
            if start_id == end_id or start == end or not _segment_supported(start, end):
                continue
            length_m = 1000 * haversine_distance_km(*start, *end)
            if length_m <= 0:
                continue
            nodes[start_id] = RoadNode(start_id, *start)
            nodes[end_id] = RoadNode(end_id, *end)
            common = {
                "osm_way_id": way_id,
                "length_m": length_m,
                "road_type": tags["highway"],
                "name": tags.get("name"),
                "osm_oneway": tags.get("oneway"),
                "surface": tags.get("surface"),
                "maxspeed": tags.get("maxspeed"),
            }
            if walking_forward or motorbike_forward:
                edge_id = f"{way_id}:{segment_index}:f"
                edges[edge_id] = RoadEdge(
                    edge_id=edge_id,
                    start_node=start_id,
                    end_node=end_id,
                    geometry=(start, end),
                    direction="forward",
                    walking_allowed=walking_forward,
                    motorbike_allowed=motorbike_forward,
                    **common,
                )
            if walking_reverse or motorbike_reverse:
                edge_id = f"{way_id}:{segment_index}:r"
                edges[edge_id] = RoadEdge(
                    edge_id=edge_id,
                    start_node=end_id,
                    end_node=start_id,
                    geometry=(end, start),
                    direction="reverse",
                    walking_allowed=walking_reverse,
                    motorbike_allowed=motorbike_reverse,
                    **common,
                )
            retained_way_ids.add(way_id)

    used_node_ids = {
        node_id
        for edge in edges.values()
        for node_id in (edge.start_node, edge.end_node)
    }
    nodes = {node_id: nodes[node_id] for node_id in sorted(used_node_ids)}
    edges = {edge_id: edges[edge_id] for edge_id in sorted(edges)}
    if not edges:
        raise ValueError("No traversable OSM segments remained after pilot filtering.")

    osm3s = payload.get("osm3s", {})
    osm_timestamp = (
        osm3s.get("timestamp_osm_base")
        if isinstance(osm3s, dict)
        else None
    )
    retrieved_at = retrieval_time or datetime.now(timezone.utc)
    metadata: dict[str, object] = {
        "source": OSM_SOURCE_URL,
        "license": OSM_LICENSE,
        "retrieval_method": "Overpass API, bounded Overpass QL highway query",
        "overpass_endpoint": DEFAULT_OVERPASS_URL,
        "osm_snapshot_timestamp": osm_timestamp,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "coordinate_system": "WGS84 geographic coordinates (EPSG:4326)",
        "pilot_station_ids": list(PILOT_STATION_IDS),
        "pilot_polygon_lat_lon": [list(point) for point in PILOT_POLYGON],
        "query": overpass_query(),
        "retained_osm_ways": len(retained_way_ids),
        "nodes": len(nodes),
        "directed_edges": len(edges),
        "walking_highway_types": sorted(WALKING_HIGHWAYS),
        "motorbike_highway_types": sorted(MOTORBIKE_HIGHWAYS),
        "filter_note": (
            "Segments require endpoints and midpoint inside the stations 2–6 "
            "convex hull. access/foot/motorcycle/motor_vehicle/vehicle and "
            "mode-specific oneway tags are applied. Turn restrictions and "
            "conditional restrictions are not interpreted."
        ),
    }
    return RoadNetwork(nodes=nodes, edges=edges, metadata=metadata)


def save_network(network: RoadNetwork, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if output_path.suffix == ".gz" else open
    with opener(output_path, "wt", encoding="utf-8") as handle:
        json.dump(network.to_dict(), handle, separators=(",", ":"), sort_keys=True)


def load_network(path: str | Path) -> RoadNetwork:
    input_path = Path(path)
    opener = gzip.open if input_path.suffix == ".gz" else open
    with opener(input_path, "rt", encoding="utf-8") as handle:
        return RoadNetwork.from_dict(json.load(handle))


def save_metadata(network: RoadNetwork, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(network.metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def download_and_process_network(
    output_directory: str | Path = "data/processed/road_network",
    *,
    endpoint: str = DEFAULT_OVERPASS_URL,
) -> RoadNetwork:
    output_directory = Path(output_directory)
    payload = retrieve_overpass(endpoint)
    network = build_network_from_overpass(payload)
    network.metadata["overpass_endpoint"] = endpoint
    save_network(network, output_directory / "healthyair_pilot_osm.json.gz")
    save_metadata(output_directory / "metadata.json", network)
    return network


def road_type_counts(network: RoadNetwork, mode: str) -> dict[str, int]:
    validate_mode(mode)
    counts: dict[str, int] = {}
    for edge in network.edges.values():
        if edge.allows(mode):
            counts[edge.road_type] = counts.get(edge.road_type, 0) + 1
    return dict(sorted(counts.items()))


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-directory", default="data/processed/road_network"
    )
    parser.add_argument("--overpass-url", default=DEFAULT_OVERPASS_URL)
    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()
    network = download_and_process_network(
        arguments.output_directory, endpoint=arguments.overpass_url
    )
    print(
        json.dumps(
            {
                "nodes": len(network.nodes),
                "directed_edges": len(network.edges),
                **{
                    mode: network.mode_counts(mode)
                    for mode in MODES
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
