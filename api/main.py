"""Thin FastAPI demo backend for frozen AIRPATH-AI web prototype data."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Sequence

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_DEMO_DIR: Final[Path] = REPO_ROOT / "data" / "processed" / "web_demo"
SUPPORTED_MODES: Final[frozenset[str]] = frozenset({"walking", "motorbike"})
LOCAL_DEV_ORIGINS: Final[tuple[str, ...]] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def parse_allowed_origins(raw: str | None) -> list[str]:
    """Parse AIRPATH_ALLOWED_ORIGINS. Wildcard * is ignored, never allow-all."""
    if raw is None or not raw.strip():
        return list(LOCAL_DEV_ORIGINS)
    origins: list[str] = []
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if not origin or origin == "*":
            continue
        origins.append(origin)
    return origins


class Coordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    latitude: float
    longitude: float


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    origin: Coordinate
    destination: Coordinate
    straight_line_distance_km: float
    supported_modes: list[str]
    supported_delta_minutes: list[float]
    demo_distance_rank: int
    selection_method: str


class ScenariosResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenarios: list[Scenario]


class RouteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str
    route_type: str
    rank: int
    is_fastest: bool
    is_feasible: bool = True
    travel_time_minutes: float
    additional_time_vs_fastest_minutes: float
    predicted_exposure_index: float
    predicted_exposure_reduction_percent: float
    distance_m: float
    geometry: list[list[float]]
    available_feasible_alternatives: int | None = None
    fewer_than_requested_alternatives: bool | None = None
    research_warning: str | None = None


class RoutesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    mode: str
    delta_minutes: float
    fastest_route: RouteRecord
    alternatives: list[RouteRecord]
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    demo_pack: str


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Demo pack file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_demo_pack(demo_dir: str | None = None) -> dict[str, Any]:
    """Load self-contained demo JSON once (no research-engine execution)."""
    root = Path(demo_dir) if demo_dir else DEFAULT_DEMO_DIR
    scenarios_payload = _load_json(root / "scenarios.json")
    routes_payload = _load_json(root / "routes.json")
    metadata = _load_json(root / "metadata.json")
    scenarios = scenarios_payload.get("scenarios")
    routes = routes_payload.get("routes")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios.json must contain a non-empty scenarios list.")
    if not isinstance(routes, list) or not routes:
        raise ValueError("routes.json must contain a non-empty routes list.")
    by_scenario = {str(item["scenario_id"]): item for item in scenarios}
    index: dict[tuple[str, str, float], list[dict[str, Any]]] = {}
    for route in routes:
        key = (
            str(route["scenario_id"]),
            str(route["mode"]),
            float(route["delta_minutes"]),
        )
        index.setdefault(key, []).append(route)
    for key, group in index.items():
        group.sort(key=lambda row: (int(row["rank"]), str(row["route_id"])))
        fastest = [row for row in group if row.get("is_fastest") or row.get("route_type") == "fastest"]
        if len(fastest) != 1:
            raise ValueError(f"Demo pack integrity error for {key}: fastest count={len(fastest)}")
    return {
        "demo_dir": str(root),
        "scenarios": scenarios,
        "scenario_by_id": by_scenario,
        "routes_index": index,
        "metadata": metadata,
    }


def create_app(
    demo_dir: Path | None = None,
    *,
    allowed_origins: Sequence[str] | None = None,
) -> FastAPI:
    """Application factory so tests can point at a temporary demo pack."""
    app = FastAPI(
        title="AIRPATH-AI Demo API",
        description=(
            "Thin read-only API over the frozen Model-C web demo pack. "
            "Does not retrain models, run IDW, or optimize routes."
        ),
        version="0.1.0",
    )
    origins = (
        list(allowed_origins)
        if allowed_origins is not None
        else parse_allowed_origins(os.environ.get("AIRPATH_ALLOWED_ORIGINS"))
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # Demo static sites get unpredictable *.onrender.com hosts. Not "*".
        allow_origin_regex=r"https://[a-z0-9.-]+\.onrender\.com",
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
    )
    resolved_dir = str(demo_dir) if demo_dir is not None else None

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "airpath-demo-api",
            "health": "/health",
            "note": "This is the API, not the map UI. Open the Static Site URL.",
        }

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        pack = load_demo_pack(resolved_dir)
        return HealthResponse(
            status="ok",
            service="airpath-demo-api",
            demo_pack=str(pack["metadata"].get("pack_name", "unknown")),
        )

    @app.get("/demo/scenarios", response_model=ScenariosResponse)
    def demo_scenarios() -> ScenariosResponse:
        pack = load_demo_pack(resolved_dir)
        return ScenariosResponse(scenarios=pack["scenarios"])

    @app.get("/demo/routes", response_model=RoutesResponse)
    def demo_routes(
        scenario_id: str = Query(..., min_length=1, description="Demo OD scenario id"),
        mode: str = Query(..., min_length=1, description="walking or motorbike"),
        delta_minutes: float = Query(
            ...,
            description="Maximum extra minutes vs fastest route",
        ),
    ) -> RoutesResponse:
        pack = load_demo_pack(resolved_dir)
        scenario_by_id: dict[str, Any] = pack["scenario_by_id"]
        metadata: dict[str, Any] = dict(pack["metadata"])

        if scenario_id not in scenario_by_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "unknown_scenario_id",
                    "message": f"Unknown scenario_id '{scenario_id}'.",
                    "available_scenario_ids": sorted(scenario_by_id),
                },
            )

        mode_normalized = mode.strip().lower()
        scenario = scenario_by_id[scenario_id]
        supported_modes = {str(m).lower() for m in scenario.get("supported_modes", [])}
        if mode_normalized not in SUPPORTED_MODES or mode_normalized not in supported_modes:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_mode",
                    "message": (
                        f"Unsupported mode '{mode}'. "
                        f"Use one of: {sorted(supported_modes)}."
                    ),
                    "supported_modes": sorted(supported_modes),
                },
            )

        supported_deltas = [float(d) for d in scenario.get("supported_delta_minutes", [])]
        try:
            delta_value = float(delta_minutes)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "malformed_query",
                    "message": "delta_minutes must be a number.",
                },
            ) from exc

        matched_delta = next(
            (d for d in supported_deltas if abs(d - delta_value) < 1e-9),
            None,
        )
        if matched_delta is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_delta_minutes",
                    "message": (
                        f"Unsupported delta_minutes={delta_value}. "
                        f"Supported values: {supported_deltas}."
                    ),
                    "supported_delta_minutes": supported_deltas,
                },
            )

        key = (scenario_id, mode_normalized, float(matched_delta))
        routes_index: dict[tuple[str, str, float], list[dict[str, Any]]] = pack[
            "routes_index"
        ]
        group = routes_index.get(key)
        if not group:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "route_request_outside_demo_dataset",
                    "message": (
                        "No frozen demo routes for "
                        f"scenario_id={scenario_id}, mode={mode_normalized}, "
                        f"delta_minutes={matched_delta}."
                    ),
                },
            )

        fastest_raw = next(
            row
            for row in group
            if row.get("is_fastest") or row.get("route_type") == "fastest"
        )
        alternatives_raw = [
            row
            for row in group
            if not (row.get("is_fastest") or row.get("route_type") == "fastest")
        ]

        def to_public_route(row: dict[str, Any]) -> RouteRecord:
            return RouteRecord(
                route_id=str(row["route_id"]),
                route_type=str(row["route_type"]),
                rank=int(row["rank"]),
                is_fastest=bool(row["is_fastest"]),
                is_feasible=bool(row.get("is_feasible", True)),
                travel_time_minutes=float(row["travel_time_minutes"]),
                additional_time_vs_fastest_minutes=float(
                    row["additional_time_vs_fastest_minutes"]
                ),
                predicted_exposure_index=float(row["predicted_exposure_index"]),
                predicted_exposure_reduction_percent=float(
                    row["predicted_exposure_reduction_percent"]
                ),
                distance_m=float(row["distance_m"]),
                geometry=row["geometry"],
                available_feasible_alternatives=(
                    int(row["available_feasible_alternatives"])
                    if row.get("available_feasible_alternatives") is not None
                    else None
                ),
                fewer_than_requested_alternatives=(
                    bool(row["fewer_than_requested_alternatives"])
                    if row.get("fewer_than_requested_alternatives") is not None
                    else None
                ),
                research_warning=row.get("research_warning"),
            )

        response_metadata = {
            "pack_name": metadata.get("pack_name"),
            "forecaster": metadata.get("forecaster"),
            "spatial_model": metadata.get("spatial_model"),
            "exposure_definition": metadata.get("exposure_definition"),
            "exposure_unit": metadata.get("exposure_unit"),
            "departure_time": metadata.get("departure_time"),
            "forecasting_origin": metadata.get("forecasting_origin"),
            "research_warning": metadata.get("research_warning"),
            "available_feasible_alternatives": fastest_raw.get(
                "available_feasible_alternatives"
            ),
            "fewer_than_requested_alternatives": fastest_raw.get(
                "fewer_than_requested_alternatives"
            ),
            "alternative_count": len(alternatives_raw),
            "empty_alternatives_message": (
                None
                if alternatives_raw
                else (
                    "No lower-exposure alternative was found within your time limit."
                )
            ),
        }
        return RoutesResponse(
            scenario_id=scenario_id,
            mode=mode_normalized,
            delta_minutes=float(matched_delta),
            fastest_route=to_public_route(fastest_raw),
            alternatives=[to_public_route(row) for row in alternatives_raw],
            metadata=response_metadata,
        )

    return app


app = create_app()
