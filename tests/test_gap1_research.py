"""Gap 1 Direction-A exhibit: frozen tables only, no simulated street PM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app, load_demo_pack, load_gap1_exhibit
from src.gap1_research_export import build_gap1_exhibit, write_gap1_exhibit

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO_ROOT / "data" / "processed" / "web_demo"
EXHIBIT_PATH = REPO_ROOT / "data" / "processed" / "gap1_research" / "exhibit.json"


@pytest.fixture(scope="module")
def client() -> TestClient:
    load_demo_pack.cache_clear()
    load_gap1_exhibit.cache_clear()
    app = create_app(DEMO_DIR)
    with TestClient(app) as test_client:
        yield test_client
    load_demo_pack.cache_clear()
    load_gap1_exhibit.cache_clear()


def test_build_gap1_exhibit_uses_frozen_tables_not_demo_pm() -> None:
    exhibit = build_gap1_exhibit()
    assert exhibit["uses_simulated_onroad_pm"] is False
    assert exhibit["scientific_logic_modified"] is False
    assert exhibit["spatial_model"] == "idw_p1"
    assert exhibit["forecaster"] == "C_xgboost_current_pm"
    assert "MIXED/WEAK" in exhibit["freeze_gap1_conclusion"]
    assert exhibit["p0_2a"]["nontrivial_selection_difference_rate"] == pytest.approx(
        0.06333333333333334
    )
    assert exhibit["p0_2a"]["mean_spearman_static_vs_airpath"] == pytest.approx(
        0.9924603174603174
    )
    assert exhibit["p0_2b"]["nontrivial_selection_difference_rate"] == pytest.approx(
        0.013333333333333334
    )
    assert exhibit["p0_2b"]["gap1_conclusion_changed_vs_p0_2a"] is False
    proof = exhibit["how_to_prove_rare"]
    assert proof["p0_2a"]["differ_count"] == 19
    assert proof["p0_2a"]["nontrivial_count"] == 300
    assert proof["p0_2b"]["differ_count"] == 20
    assert proof["p0_2b"]["nontrivial_count"] == 1500
    peak = exhibit["peak_hour_with_current_data"]
    assert "congested" in peak["what_is_not_identifiable"].lower()
    for panel in (exhibit["p0_2a"], exhibit["p0_2b"]):
        for row in panel["representative_disagreements"]:
            assert row["delta_minutes"] == 5.0
            assert row["static_selected_route_id"] != row["airpath_selected_route_id"]
    assert "PM2.5_road" not in exhibit["available_substitution"]
    forbidden = " ".join(exhibit["paper_claim_forbidden"]).lower()
    assert "street d" in forbidden
    assert "simulated" in forbidden


def test_research_gap1_endpoint(client: TestClient) -> None:
    response = client.get("/research/gap1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["uses_simulated_onroad_pm"] is False
    assert payload["pack_name"] == "airpath_gap1_direction_a_v1"
    assert "MIXED/WEAK" in payload["freeze_gap1_conclusion"]
    assert payload["worked_example"]["hour_used"] == "07:00"


def test_root_lists_gap1(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["research_gap1"] == "/research/gap1"


def test_load_gap1_exhibit_rejects_simulated_pm(tmp_path: Path) -> None:
    exhibit = build_gap1_exhibit()
    exhibit["uses_simulated_onroad_pm"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(exhibit), encoding="utf-8")
    load_gap1_exhibit.cache_clear()
    with pytest.raises(ValueError, match="simulated"):
        load_gap1_exhibit(str(path))
    load_gap1_exhibit.cache_clear()


def test_write_gap1_exhibit_roundtrip(tmp_path: Path) -> None:
    exhibit = build_gap1_exhibit()
    out = write_gap1_exhibit(tmp_path / "exhibit.json", exhibit)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["uses_simulated_onroad_pm"] is False
    assert EXHIBIT_PATH.is_file()
