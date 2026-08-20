from datetime import datetime, timezone

import pandas as pd
import pytest

from src.eta_engine import (
    DEFAULT_MODE_SPEED_KMH,
    propagate_segment_etas,
    spatial_target_records,
    validate_segment_etas,
)
from src.road_network import (
    PILOT_POLYGON,
    RoadEdge,
    RoadNetwork,
    RoadNode,
    UnsupportedAreaError,
    build_network_from_overpass,
    load_network,
    point_in_pilot_area,
    save_network,
)
from src.route_candidates import generate_candidate_routes
from src.spatial_estimation import haversine_distance_km


def _edge(
    edge_id: str,
    start: RoadNode,
    end: RoadNode,
    *,
    walking: bool = True,
    motorbike: bool = True,
) -> RoadEdge:
    return RoadEdge(
        edge_id=edge_id,
        osm_way_id=int(edge_id.split("-")[0]),
        start_node=start.node_id,
        end_node=end.node_id,
        geometry=(
            (start.latitude, start.longitude),
            (end.latitude, end.longitude),
        ),
        length_m=1000
        * haversine_distance_km(
            start.latitude,
            start.longitude,
            end.latitude,
            end.longitude,
        ),
        road_type="residential",
        name=None,
        direction="forward",
        osm_oneway=None,
        walking_allowed=walking,
        motorbike_allowed=motorbike,
        surface=None,
        maxspeed=None,
    )


def _five_route_network() -> tuple[RoadNetwork, tuple[float, float], tuple[float, float]]:
    # All synthetic graph coordinates are inside the real stations 2–6 hull.
    nodes = {
        1: RoadNode(1, 10.775, 106.645),
        2: RoadNode(2, 10.790, 106.648),
        3: RoadNode(3, 10.787, 106.655),
        4: RoadNode(4, 10.784, 106.662),
        5: RoadNode(5, 10.781, 106.669),
        6: RoadNode(6, 10.778, 106.676),
        7: RoadNode(7, 10.790, 106.685),
    }
    edges = {}
    edge_number = 1
    for intermediate in range(2, 7):
        first = _edge(f"{edge_number}-a", nodes[1], nodes[intermediate])
        edge_number += 1
        second = _edge(f"{edge_number}-b", nodes[intermediate], nodes[7])
        edge_number += 1
        edges[first.edge_id] = first
        edges[second.edge_id] = second
    network = RoadNetwork(nodes, edges, {"fixture": True})
    origin = (nodes[1].latitude, nodes[1].longitude)
    destination = (nodes[7].latitude, nodes[7].longitude)
    return network, origin, destination


def test_pilot_boundary_and_unsupported_area() -> None:
    assert all(point_in_pilot_area(*point) for point in PILOT_POLYGON)
    assert point_in_pilot_area(10.79, 106.67)
    assert not point_in_pilot_area(10.87, 106.796)

    network, _, destination = _five_route_network()
    with pytest.raises(UnsupportedAreaError, match="outside"):
        generate_candidate_routes(
            network,
            (10.87, 106.796),
            destination,
            "walking",
        )


def test_overpass_conversion_applies_mode_and_oneway_rules() -> None:
    payload = {
        "osm3s": {"timestamp_osm_base": "2026-08-20T00:00:00Z"},
        "elements": [
            {
                "type": "way",
                "id": 100,
                "nodes": [1, 2],
                "geometry": [
                    {"lat": 10.78, "lon": 106.65},
                    {"lat": 10.78, "lon": 106.66},
                ],
                "tags": {"highway": "footway"},
            },
            {
                "type": "way",
                "id": 200,
                "nodes": [2, 3],
                "geometry": [
                    {"lat": 10.78, "lon": 106.66},
                    {"lat": 10.78, "lon": 106.67},
                ],
                "tags": {"highway": "residential", "oneway": "yes"},
            },
            {
                "type": "way",
                "id": 300,
                "nodes": [3, 4],
                "geometry": [
                    {"lat": 10.78, "lon": 106.67},
                    {"lat": 10.78, "lon": 106.68},
                ],
                "tags": {
                    "highway": "service",
                    "access": "private",
                },
            },
        ],
    }
    network = build_network_from_overpass(
        payload,
        retrieval_time=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )

    footway_edges = [
        edge for edge in network.edges.values() if edge.osm_way_id == 100
    ]
    assert len(footway_edges) == 2
    assert all(edge.walking_allowed for edge in footway_edges)
    assert not any(edge.motorbike_allowed for edge in footway_edges)

    residential = {
        edge.direction: edge
        for edge in network.edges.values()
        if edge.osm_way_id == 200
    }
    assert residential["forward"].motorbike_allowed
    assert residential["forward"].walking_allowed
    assert not residential["reverse"].motorbike_allowed
    assert residential["reverse"].walking_allowed
    assert not any(edge.osm_way_id == 300 for edge in network.edges.values())


def test_restricted_conditional_directional_and_barrier_access_is_conservative() -> None:
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 5,
                "lat": 10.78,
                "lon": 106.68,
                "tags": {"barrier": "bollard"},
            },
            {
                "type": "way",
                "id": 400,
                "nodes": [1, 2],
                "geometry": [
                    {"lat": 10.78, "lon": 106.64},
                    {"lat": 10.78, "lon": 106.65},
                ],
                "tags": {"highway": "service", "access": "destination"},
            },
            {
                "type": "way",
                "id": 500,
                "nodes": [2, 3],
                "geometry": [
                    {"lat": 10.78, "lon": 106.65},
                    {"lat": 10.78, "lon": 106.66},
                ],
                "tags": {
                    "highway": "residential",
                    "motorcycle:conditional": "no @ (Mo-Fr)",
                },
            },
            {
                "type": "way",
                "id": 600,
                "nodes": [3, 4],
                "geometry": [
                    {"lat": 10.78, "lon": 106.66},
                    {"lat": 10.78, "lon": 106.67},
                ],
                "tags": {
                    "highway": "residential",
                    "motorcycle:backward": "no",
                },
            },
            {
                "type": "way",
                "id": 700,
                "nodes": [4, 5],
                "geometry": [
                    {"lat": 10.78, "lon": 106.67},
                    {"lat": 10.78, "lon": 106.68},
                ],
                "tags": {"highway": "residential"},
            },
        ]
    }
    network = build_network_from_overpass(payload)

    assert not any(edge.osm_way_id == 400 for edge in network.edges.values())
    conditional = [
        edge for edge in network.edges.values() if edge.osm_way_id == 500
    ]
    assert conditional and all(edge.walking_allowed for edge in conditional)
    assert not any(edge.motorbike_allowed for edge in conditional)
    directional = {
        edge.direction: edge
        for edge in network.edges.values()
        if edge.osm_way_id == 600
    }
    assert directional["forward"].motorbike_allowed
    assert not directional["reverse"].motorbike_allowed
    barrier = [
        edge for edge in network.edges.values() if edge.osm_way_id == 700
    ]
    assert barrier and all(edge.walking_allowed for edge in barrier)
    assert not any(edge.motorbike_allowed for edge in barrier)


def test_network_round_trip_preserves_edges(tmp_path) -> None:
    network, _, _ = _five_route_network()
    path = tmp_path / "network.json.gz"

    save_network(network, path)
    restored = load_network(path)

    assert restored.nodes == network.nodes
    assert restored.edges == network.edges
    assert restored.mode_counts("walking") == network.mode_counts("walking")


def test_k_candidate_routes_are_connected_ordered_and_geometrically_consistent() -> None:
    network, origin, destination = _five_route_network()
    routes = generate_candidate_routes(
        network, origin, destination, "walking", k=5
    )

    assert len(routes) == 5
    assert len({route.edge_ids for route in routes}) == 5
    for route in routes:
        assert len(route.node_ids) == len(route.edge_ids) + 1
        assert route.node_ids[0] == route.origin_node
        assert route.node_ids[-1] == route.destination_node
        assert route.total_distance_m > 0
        assert route.total_travel_time_seconds > 0
        for index, edge_id in enumerate(route.edge_ids):
            edge = network.edges[edge_id]
            assert edge.start_node == route.node_ids[index]
            assert edge.end_node == route.node_ids[index + 1]
            assert route.geometry[index] == edge.geometry[0]
        assert route.geometry[-1] == network.edges[route.edge_ids[-1]].geometry[-1]


def test_segment_eta_invariants_and_spatial_target_contract() -> None:
    network, origin, destination = _five_route_network()
    route = generate_candidate_routes(
        network, origin, destination, "walking", k=1
    )[0]
    departure = pd.Timestamp("2026-08-20 08:00:00+07:00")

    segments = propagate_segment_etas(network, route, departure)
    validate_segment_etas(route, segments)
    targets = spatial_target_records(segments)

    assert [segment.segment_index for segment in segments] == [1, 2]
    assert all(segment.segment_duration_seconds >= 0 for segment in segments)
    assert [segment.cumulative_elapsed_seconds for segment in segments] == sorted(
        segment.cumulative_elapsed_seconds for segment in segments
    )
    assert [segment.target_arrival_timestamp for segment in segments] == sorted(
        segment.target_arrival_timestamp for segment in segments
    )
    assert sum(segment.segment_duration_seconds for segment in segments) == pytest.approx(
        route.total_travel_time_seconds
    )
    assert set(targets[0]) == {
        "route_id",
        "segment_index",
        "edge_id",
        "latitude",
        "longitude",
        "target_time",
    }
    assert targets[0]["target_time"] == segments[0].target_arrival_timestamp


def test_walking_and_motorbike_have_different_baseline_etas() -> None:
    network, origin, destination = _five_route_network()
    walking = generate_candidate_routes(
        network, origin, destination, "walking", k=1
    )[0]
    motorbike = generate_candidate_routes(
        network, origin, destination, "motorbike", k=1
    )[0]

    assert walking.total_distance_m == pytest.approx(motorbike.total_distance_m)
    assert walking.total_travel_time_seconds > motorbike.total_travel_time_seconds
    assert (
        walking.total_travel_time_seconds / motorbike.total_travel_time_seconds
        == pytest.approx(
            DEFAULT_MODE_SPEED_KMH["motorbike"]
            / DEFAULT_MODE_SPEED_KMH["walking"]
        )
    )


def test_mode_configuration_and_car_rejection() -> None:
    network, origin, destination = _five_route_network()
    standard = generate_candidate_routes(
        network, origin, destination, "walking", k=1
    )[0]
    faster = generate_candidate_routes(
        network,
        origin,
        destination,
        "walking",
        k=1,
        speed_kmh=10,
    )[0]

    assert faster.total_travel_time_seconds == pytest.approx(
        standard.total_travel_time_seconds / 2
    )
    with pytest.raises(ValueError, match="car is unsupported"):
        generate_candidate_routes(network, origin, destination, "car", k=1)
