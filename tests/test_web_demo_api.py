"""Tests for frozen web-demo export packaging and thin FastAPI demo API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app, load_demo_pack
from src.web_demo_export import (
    DEMO_DEPARTURE_TIME,
    build_demo_pack,
    select_demo_scenarios,
    write_demo_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "data" / "processed" / "web_demo"
OD_PATH = REPO_ROOT / "data" / "processed" / "temporal_gap_analysis" / "od_scenarios.csv"


@pytest.fixture(scope="module")
def client() -> TestClient:
    load_demo_pack.cache_clear()
    app = create_app(DEMO_DIR)
    with TestClient(app) as test_client:
        yield test_client
    load_demo_pack.cache_clear()


def test_demo_pack_files_exist() -> None:
    assert (DEMO_DIR / "scenarios.json").is_file()
    assert (DEMO_DIR / "routes.json").is_file()
    assert (DEMO_DIR / "metadata.json").is_file()


def test_scenario_selection_is_distance_stratified() -> None:
    import pandas as pd

    od = pd.read_csv(OD_PATH)
    selected = select_demo_scenarios(od)
    assert len(selected) == 8
    distances = selected["straight_line_distance_km"].tolist()
    assert distances == sorted(distances)
    assert selected["scenario_id"].is_unique


def test_build_demo_pack_uses_model_c_and_geometry() -> None:
    pack = build_demo_pack()
    metadata = pack["metadata"]
    assert metadata["forecaster"] == "C_xgboost_current_pm"
    assert metadata["spatial_model"] == "idw_p1"
    assert metadata["departure_time"] == DEMO_DEPARTURE_TIME
    assert metadata["scientific_logic_modified"] is False
    routes = pack["routes"]
    assert len(routes) > 0
    sample = routes[0]
    assert isinstance(sample["geometry"], list)
    assert len(sample["geometry"]) >= 2
    assert len(sample["geometry"][0]) == 2
    assert "predicted_exposure_reduction_percent" in sample
    assert sample["is_feasible"] is True


def test_write_demo_pack_roundtrip(tmp_path: Path) -> None:
    pack = build_demo_pack()
    paths = write_demo_pack(tmp_path, pack)
    scenarios = json.loads(paths["scenarios"].read_text(encoding="utf-8"))
    routes = json.loads(paths["routes"].read_text(encoding="utf-8"))
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert len(scenarios["scenarios"]) == 8
    assert len(routes["routes"]) == len(pack["routes"])
    assert metadata["pack_name"] == "airpath_web_demo_v1"


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "airpath-demo-api"
    assert payload["demo_pack"] == "airpath_web_demo_v1"


def test_demo_scenarios(client: TestClient) -> None:
    response = client.get("/demo/scenarios")
    assert response.status_code == 200
    payload = response.json()
    assert "scenarios" in payload
    assert len(payload["scenarios"]) == 8
    first = payload["scenarios"][0]
    assert {"scenario_id", "origin", "destination", "supported_modes", "supported_delta_minutes"} <= set(
        first
    )
    assert first["supported_modes"] == ["walking", "motorbike"]
    assert 0.0 in first["supported_delta_minutes"]


def test_valid_route_request(client: TestClient) -> None:
    scenarios = client.get("/demo/scenarios").json()["scenarios"]
    scenario_id = scenarios[0]["scenario_id"]
    response = client.get(
        "/demo/routes",
        params={"scenario_id": scenario_id, "mode": "walking", "delta_minutes": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "scenario_id",
        "mode",
        "delta_minutes",
        "fastest_route",
        "alternatives",
        "metadata",
    }
    fastest = payload["fastest_route"]
    assert fastest["is_fastest"] is True
    assert fastest["route_type"] == "fastest"
    assert fastest["rank"] == 0
    assert fastest["additional_time_vs_fastest_minutes"] == pytest.approx(0.0)
    for key in (
        "route_id",
        "travel_time_minutes",
        "predicted_exposure_index",
        "predicted_exposure_reduction_percent",
        "distance_m",
        "geometry",
    ):
        assert key in fastest
    assert isinstance(fastest["geometry"], list)
    assert len(fastest["geometry"][0]) == 2
    assert isinstance(payload["alternatives"], list)
    assert len(payload["alternatives"]) <= 3
    for alt in payload["alternatives"]:
        assert alt["is_fastest"] is False
        assert alt["rank"] >= 1


def test_invalid_scenario(client: TestClient) -> None:
    response = client.get(
        "/demo/routes",
        params={"scenario_id": "od_missing", "mode": "walking", "delta_minutes": 5},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error"] == "unknown_scenario_id"


def test_invalid_mode(client: TestClient) -> None:
    scenario_id = client.get("/demo/scenarios").json()["scenarios"][0]["scenario_id"]
    response = client.get(
        "/demo/routes",
        params={"scenario_id": scenario_id, "mode": "car", "delta_minutes": 5},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_mode"


def test_invalid_delta(client: TestClient) -> None:
    scenario_id = client.get("/demo/scenarios").json()["scenarios"][0]["scenario_id"]
    response = client.get(
        "/demo/routes",
        params={"scenario_id": scenario_id, "mode": "motorbike", "delta_minutes": 7},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_delta_minutes"


def test_malformed_query_missing_params(client: TestClient) -> None:
    response = client.get("/demo/routes", params={"scenario_id": "od_01", "mode": "walking"})
    assert response.status_code == 422


def test_fastest_route_always_present(client: TestClient) -> None:
    scenarios = client.get("/demo/scenarios").json()["scenarios"]
    for scenario in scenarios[:3]:
        for mode in ("walking", "motorbike"):
            for delta in (0, 3, 10):
                response = client.get(
                    "/demo/routes",
                    params={
                        "scenario_id": scenario["scenario_id"],
                        "mode": mode,
                        "delta_minutes": delta,
                    },
                )
                assert response.status_code == 200
                payload = response.json()
                assert payload["fastest_route"]["is_fastest"] is True
                assert payload["fastest_route"]["route_type"] == "fastest"


def test_zero_minute_tolerance_may_have_no_alternatives(client: TestClient) -> None:
    scenarios = client.get("/demo/scenarios").json()["scenarios"]
    found_empty = False
    for scenario in scenarios:
        for mode in ("walking", "motorbike"):
            response = client.get(
                "/demo/routes",
                params={
                    "scenario_id": scenario["scenario_id"],
                    "mode": mode,
                    "delta_minutes": 0,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["fastest_route"]["is_fastest"] is True
            if not payload["alternatives"]:
                found_empty = True
                assert payload["metadata"]["empty_alternatives_message"]
    assert found_empty, "Expected at least one +0 case with no alternatives"


def test_geometry_format(client: TestClient) -> None:
    scenario_id = client.get("/demo/scenarios").json()["scenarios"][0]["scenario_id"]
    payload = client.get(
        "/demo/routes",
        params={"scenario_id": scenario_id, "mode": "motorbike", "delta_minutes": 10},
    ).json()
    for route in [payload["fastest_route"], *payload["alternatives"]]:
        geometry = route["geometry"]
        assert isinstance(geometry, list)
        assert len(geometry) >= 2
        for point in geometry[:5]:
            assert len(point) == 2
            lat, lon = point
            assert 10.0 < lat < 11.5
            assert 106.0 < lon < 107.5


def test_response_schema_stability(client: TestClient) -> None:
    scenario_id = client.get("/demo/scenarios").json()["scenarios"][0]["scenario_id"]
    payload = client.get(
        "/demo/routes",
        params={"scenario_id": scenario_id, "mode": "walking", "delta_minutes": 2},
    ).json()
    route_keys = {
        "route_id",
        "route_type",
        "rank",
        "is_fastest",
        "is_feasible",
        "travel_time_minutes",
        "additional_time_vs_fastest_minutes",
        "predicted_exposure_index",
        "predicted_exposure_reduction_percent",
        "distance_m",
        "geometry",
        "available_feasible_alternatives",
        "fewer_than_requested_alternatives",
        "research_warning",
    }
    assert route_keys <= set(payload["fastest_route"])
    # Internal model artifacts must not leak.
    leaked = {"perturbation_scale", "oracle_exposure_index", "model", "booster"}
    assert leaked.isdisjoint(payload["fastest_route"])
    assert leaked.isdisjoint(payload["metadata"])


def test_parse_allowed_origins_defaults_to_local_vite() -> None:
    from api.main import LOCAL_DEV_ORIGINS, parse_allowed_origins

    assert parse_allowed_origins(None) == list(LOCAL_DEV_ORIGINS)
    assert parse_allowed_origins("") == list(LOCAL_DEV_ORIGINS)


def test_parse_allowed_origins_splits_and_ignores_wildcard() -> None:
    from api.main import parse_allowed_origins

    origins = parse_allowed_origins(
        "https://airpath-frontend.onrender.com, http://localhost:5173, *"
    )
    assert origins == [
        "https://airpath-frontend.onrender.com",
        "http://localhost:5173",
    ]
    assert "*" not in parse_allowed_origins("*")


def test_cors_allows_configured_origin() -> None:
    load_demo_pack.cache_clear()
    app = create_app(
        DEMO_DIR,
        allowed_origins=["https://airpath-frontend.example"],
    )
    with TestClient(app) as test_client:
        response = test_client.get(
            "/health",
            headers={"Origin": "https://airpath-frontend.example"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "https://airpath-frontend.example"
        )
        denied = test_client.get(
            "/health",
            headers={"Origin": "https://evil.example"},
        )
        assert denied.headers.get("access-control-allow-origin") is None
        onrender = test_client.get(
            "/health",
            headers={"Origin": "https://airpath-api-ii.onrender.com"},
        )
        assert (
            onrender.headers.get("access-control-allow-origin")
            == "https://airpath-api-ii.onrender.com"
        )
        root = test_client.get("/")
        assert root.status_code == 200
        assert root.json()["health"] == "/health"
    load_demo_pack.cache_clear()
