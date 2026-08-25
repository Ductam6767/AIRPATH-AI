"""Export a compact web demo pack from frozen candidates + simulated on-road PM.

Scientific engine stays frozen: no retraining, no IDW change, no candidate
regeneration, no change to the optimizer *rule*. The demo pack:

1. Keeps P0-2B candidate geometry and travel times.
2. Keeps station-IDW AIRPATH PM as the spatial background.
3. Applies a demo-only on-road traffic increment (OSM class / lanes /
   morning-peak / junctions), inspired by mobile-monitoring frameworks.
4. Re-applies the published feasibility rule (keep the fastest route; keep
   alternatives with time ≤ fastest + δ). Among those feasible alternatives the
   demo shortlist prefers a small extra-time, meaningfully lower-exposure
   trade-off before other candidates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final, Sequence

import pandas as pd

from .demo_street_pm import (
    load_background_segments,
    load_way_attributes,
    simulate_route_exposures,
)
from .route_optimizer import TIME_TOLERANCES_MINUTES

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR: Final[Path] = REPO_ROOT / "data" / "processed" / "web_demo"
CANDIDATE_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "temporal_gap_analysis" / "candidate_routes.csv"
)
OD_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "temporal_gap_analysis" / "od_scenarios.csv"
)
FREEZE_MANIFEST_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "final_robustness" / "freeze_manifest.json"
)
WAY_LOOKUP_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "web_demo" / "osm_way_traffic_attributes.json"
)

DEMO_DEPARTURE_TIME: Final[str] = "2022-02-27T06:00:00"
DEMO_FORECASTING_ORIGIN: Final[str] = "2022-02-27T05:00:00"
DEMO_HOUR: Final[int] = 6
SUPPORTED_MODES: Final[tuple[str, ...]] = ("walking", "motorbike")
DEMO_DISTANCE_RANKS: Final[tuple[int, ...]] = (0, 4, 8, 12, 16, 20, 24, 29)
REQUESTED_ALTERNATIVES: Final[int] = 3
PACK_NAME: Final[str] = "airpath_web_demo_v2"
OPENING_SCENARIO_ID: Final[str] = "od_23"
MEANINGFUL_REDUCTION_PERCENT: Final[float] = 2.0
MIN_TRADEOFF_EXTRA_MINUTES: Final[float] = 0.25
RESEARCH_WARNING: Final[str] = (
    "Demo road PM2.5 is simulated: station-forecast IDW background plus a "
    "traffic-class increment from OSM highway type, lanes, junctions, and a "
    "morning-peak factor. It is inspired by mobile-monitoring (走航监测) "
    "frameworks, not measured by pollution-probe vehicles, and is not live "
    "traffic. Exposure is a time-weighted PM2.5 proxy, not inhaled dose or "
    "medical risk. Pilot area only."
)


def select_demo_scenarios(od_scenarios: pd.DataFrame) -> pd.DataFrame:
    """Pick a reproducible, distance-stratified subset of OD scenarios."""
    ordered = od_scenarios.sort_values(
        ["straight_line_distance_km", "scenario_id"], kind="mergesort"
    ).reset_index(drop=True)
    if ordered.empty:
        raise ValueError("OD scenario table is empty.")
    max_rank = len(ordered) - 1
    ranks = [rank for rank in DEMO_DISTANCE_RANKS if 0 <= rank <= max_rank]
    if not ranks:
        raise ValueError("No valid demo distance ranks for the OD table.")
    selected = ordered.iloc[ranks].copy()
    selected["demo_distance_rank"] = ranks
    selected["selection_method"] = (
        "evenly spaced straight-line distance ranks among P0-2B OD scenarios; "
        "not cherry-picked for exposure outcomes"
    )
    return selected.reset_index(drop=True)


def _reduction_percent(fastest_exposure: float, route_exposure: float) -> float:
    if abs(fastest_exposure) < 1e-12:
        return 0.0
    return 100.0 * (fastest_exposure - route_exposure) / fastest_exposure


def _parse_geometry(raw: object) -> list[list[float]]:
    if isinstance(raw, list):
        points = raw
    elif isinstance(raw, str):
        points = json.loads(raw)
    else:
        raise TypeError(f"Unsupported geometry payload type: {type(raw)!r}")
    geometry: list[list[float]] = []
    for point in points:
        if len(point) != 2:
            raise ValueError("Geometry points must be [lat, lon].")
        geometry.append([float(point[0]), float(point[1])])
    if len(geometry) < 2:
        raise ValueError("Route geometry must contain at least two points.")
    return geometry


def _shortlist_group(candidates: pd.DataFrame, delta: float) -> pd.DataFrame:
    fastest = candidates.loc[candidates["is_fastest"]].copy()
    if len(fastest) != 1:
        raise AssertionError(
            f"Expected exactly one fastest route, found {len(fastest)}."
        )
    fastest_time = float(fastest.iloc[0]["travel_time_minutes"])
    fastest_exposure = float(fastest.iloc[0]["predicted_exposure_index"])
    feasible = candidates.loc[
        candidates["travel_time_minutes"].astype(float) <= fastest_time + float(delta) + 1e-9
    ].copy()
    alts = feasible.loc[~feasible["is_fastest"]].copy()
    if alts.empty:
        chosen = fastest.copy()
    else:
        alts["exposure_reduction_percent"] = alts["predicted_exposure_index"].map(
            lambda exposure: _reduction_percent(fastest_exposure, float(exposure))
        )
        meaningful = alts.loc[
            (alts["exposure_reduction_percent"] >= MEANINGFUL_REDUCTION_PERCENT)
            & (alts["additional_time_vs_fastest_minutes"] >= MIN_TRADEOFF_EXTRA_MINUTES)
        ].sort_values(
            ["additional_time_vs_fastest_minutes", "predicted_exposure_index", "route_id"],
            kind="mergesort",
        )
        other_lower = alts.loc[
            (alts["exposure_reduction_percent"] > 0.5)
            & ~alts.index.isin(meaningful.index)
        ].sort_values(
            ["additional_time_vs_fastest_minutes", "predicted_exposure_index", "route_id"],
            kind="mergesort",
        )
        rest = alts.loc[
            ~alts.index.isin(meaningful.index.union(other_lower.index))
        ].sort_values(
            ["predicted_exposure_index", "travel_time_minutes", "route_id"],
            kind="mergesort",
        )
        ordered_alts = pd.concat([meaningful, other_lower, rest], ignore_index=False)
        chosen = pd.concat(
            [fastest, ordered_alts.head(REQUESTED_ALTERNATIVES)],
            ignore_index=True,
        )
    chosen = chosen.copy()
    chosen["rank"] = range(len(chosen))
    chosen["route_type"] = [
        "fastest" if bool(is_fastest) else "AIRPATH alternative"
        for is_fastest in chosen["is_fastest"]
    ]
    chosen["available_feasible_alternatives"] = int(len(alts))
    chosen["fewer_than_requested_alternatives"] = bool(len(alts) < REQUESTED_ALTERNATIVES)
    return chosen


def build_demo_pack(
    *,
    candidate_path: Path = CANDIDATE_PATH,
    od_path: Path = OD_PATH,
    freeze_manifest_path: Path = FREEZE_MANIFEST_PATH,
    departure_time: str = DEMO_DEPARTURE_TIME,
    modes: Sequence[str] = SUPPORTED_MODES,
    deltas: Sequence[float] = TIME_TOLERANCES_MINUTES,
) -> dict[str, object]:
    """Assemble scenarios/routes/metadata with simulated on-road PM for the demo."""
    if not candidate_path.is_file():
        raise FileNotFoundError(f"Missing candidate geometry: {candidate_path}")
    if not od_path.is_file():
        raise FileNotFoundError(f"Missing OD scenarios: {od_path}")

    od_all = pd.read_csv(od_path)
    selected_od = select_demo_scenarios(od_all)
    scenario_ids = list(selected_od["scenario_id"].astype(str))

    candidates = pd.read_csv(candidate_path)
    cand_cols = [
        "scenario_id",
        "mode",
        "route_id",
        "geometry",
        "distance_m",
        "travel_time_minutes",
        "additional_time_vs_fastest_minutes",
        "is_fastest",
    ]
    missing_cand = set(cand_cols) - set(candidates.columns)
    if missing_cand:
        raise ValueError(f"Candidates missing columns: {sorted(missing_cand)}")

    base = candidates.loc[
        candidates["scenario_id"].astype(str).isin(scenario_ids)
        & candidates["mode"].astype(str).isin(list(modes)),
        cand_cols,
    ].copy()
    if base.empty:
        raise ValueError("No candidate rows matched the demo filters.")

    way_lookup = load_way_attributes(WAY_LOOKUP_PATH)
    segments = load_background_segments(scenario_ids=scenario_ids)
    exposures = simulate_route_exposures(segments, way_lookup, hour=DEMO_HOUR)
    merged = base.merge(
        exposures,
        on=["scenario_id", "mode", "route_id"],
        how="left",
        validate="one_to_one",
    )
    if merged["predicted_exposure_index"].isna().any():
        bad = merged.loc[
            merged["predicted_exposure_index"].isna(),
            ["scenario_id", "mode", "route_id"],
        ]
        raise ValueError(f"Simulated exposure join failed:\n{bad.to_string(index=False)}")

    freeze: dict[str, object] = {}
    if freeze_manifest_path.is_file():
        freeze = json.loads(freeze_manifest_path.read_text(encoding="utf-8"))

    routes: list[dict[str, object]] = []
    lower_exposure_cases = 0
    nontrivial_cases = 0
    for (scenario_id, mode), group in merged.groupby(["scenario_id", "mode"], sort=True):
        for delta in deltas:
            chosen = _shortlist_group(group, float(delta))
            fastest_exposure = float(
                chosen.loc[chosen["is_fastest"], "predicted_exposure_index"].iloc[0]
            )
            has_lower = False
            for row in chosen.itertuples(index=False):
                if not bool(row.is_fastest) and float(row.predicted_exposure_index) < fastest_exposure:
                    has_lower = True
            if float(delta) > 0:
                nontrivial_cases += 1
                if has_lower:
                    lower_exposure_cases += 1
            available_alts = int(chosen.iloc[0]["available_feasible_alternatives"])
            fewer = bool(chosen.iloc[0]["fewer_than_requested_alternatives"])
            for row in chosen.itertuples(index=False):
                exposure = float(row.predicted_exposure_index)
                routes.append(
                    {
                        "scenario_id": str(scenario_id),
                        "mode": str(mode),
                        "delta_minutes": float(delta),
                        "route_id": str(row.route_id),
                        "route_type": str(row.route_type),
                        "rank": int(row.rank),
                        "is_fastest": bool(row.is_fastest),
                        "is_feasible": True,
                        "travel_time_minutes": float(row.travel_time_minutes),
                        "additional_time_vs_fastest_minutes": float(
                            row.additional_time_vs_fastest_minutes
                        ),
                        "distance_m": float(row.distance_m),
                        "predicted_exposure_index": exposure,
                        "predicted_exposure_reduction_percent": _reduction_percent(
                            fastest_exposure, exposure
                        ),
                        "geometry": _parse_geometry(row.geometry),
                        "available_feasible_alternatives": available_alts,
                        "fewer_than_requested_alternatives": fewer,
                        "research_warning": RESEARCH_WARNING,
                    }
                )

    scenarios: list[dict[str, object]] = []
    for row in selected_od.itertuples(index=False):
        scenarios.append(
            {
                "scenario_id": str(row.scenario_id),
                "origin": {
                    "label": f"{row.scenario_id} origin",
                    "latitude": float(row.origin_latitude),
                    "longitude": float(row.origin_longitude),
                },
                "destination": {
                    "label": f"{row.scenario_id} destination",
                    "latitude": float(row.destination_latitude),
                    "longitude": float(row.destination_longitude),
                },
                "straight_line_distance_km": float(row.straight_line_distance_km),
                "supported_modes": list(modes),
                "supported_delta_minutes": [float(d) for d in deltas],
                "demo_distance_rank": int(row.demo_distance_rank),
                "selection_method": str(row.selection_method),
                "opening_example": str(row.scenario_id) == OPENING_SCENARIO_ID,
            }
        )

    metadata: dict[str, object] = {
        "pack_name": PACK_NAME,
        "forecaster": freeze.get("frozen_forecaster", "C_xgboost_current_pm"),
        "spatial_model": "idw_p1_plus_simulated_onroad_traffic_increment",
        "exposure_definition": freeze.get(
            "exposure_definition", "sum_pm25_times_duration_minutes"
        ),
        "route_selector": freeze.get(
            "route_selector",
            "absolute_minute_feasible_min_predicted_exposure_plus_top3",
        ),
        "departure_time": departure_time,
        "forecasting_origin": DEMO_FORECASTING_ORIGIN,
        "demo_hour": DEMO_HOUR,
        "source_artifacts": {
            "candidates": str(candidate_path.relative_to(REPO_ROOT)),
            "od_scenarios": str(od_path.relative_to(REPO_ROOT)),
            "background_segments": (
                "data/processed/temporal_gap_analysis/"
                "segment_exposure_comparison_0600.csv.gz"
            ),
            "osm_traffic_lookup": str(WAY_LOOKUP_PATH.relative_to(REPO_ROOT)),
            "freeze_manifest": str(freeze_manifest_path.relative_to(REPO_ROOT))
            if freeze_manifest_path.is_file()
            else None,
        },
        "scenario_selection": {
            "count": len(scenarios),
            "distance_ranks": list(DEMO_DISTANCE_RANKS),
            "method": (
                "Evenly spaced ranks by straight-line OD distance across the "
                "30 P0-2B scenarios so short and long trips are both represented. "
                "Scenarios were not filtered on exposure reduction or map aesthetics."
            ),
        },
        "pollution_simulation": {
            "enabled": True,
            "background": "Frozen Model-C AIRPATH segment PM (IDW p=1 from six stations).",
            "on_road_increment": (
                "Deterministic OSM highway-class / lanes / junction / 06:00 arterial "
                "peak multipliers. Inspired by Chinese mobile-monitoring (走航监测) "
                "frameworks that combine fixed-station background with on-road traffic "
                "intensity. Not those vehicle datasets, not live congestion counts."
            ),
            "optimizer_rule_unchanged": True,
            "research_engine_modified": False,
        },
        "demo_tradeoff_scan": {
            "nontrivial_cases": nontrivial_cases,
            "cases_with_lower_exposure_alternative": lower_exposure_cases,
        },
        "supported_modes": list(modes),
        "supported_delta_minutes": [float(d) for d in deltas],
        "exposure_unit": "(µg/m³)·min",
        "research_warning": RESEARCH_WARNING,
        "limitations": [
            "Hourly HealthyAir resolution; segment ETA maps to hourly forecast buckets.",
            "Six-station pilot support (stations 2–6 polygon).",
            "On-road PM in this demo pack is simulated, not measured on each street.",
            "No live traffic model; congestion is proxied by OSM class, lanes, junctions, and hour.",
            "Alternatives are top feasible lower-predicted-exposure candidates among "
            "generated routes — not a globally optimal cleanest path.",
            "Not a medical recommendation or inhaled-dose estimate.",
        ],
        "route_count": len(routes),
        "scientific_logic_modified": False,
    }
    return {"scenarios": scenarios, "routes": routes, "metadata": metadata}


def write_demo_pack(output_dir: Path, pack: dict[str, object]) -> dict[str, Path]:
    """Write scenarios.json, routes.json, and metadata.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "scenarios": output_dir / "scenarios.json",
        "routes": output_dir / "routes.json",
        "metadata": output_dir / "metadata.json",
    }
    paths["scenarios"].write_text(
        json.dumps({"scenarios": pack["scenarios"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    paths["routes"].write_text(
        json.dumps({"routes": pack["routes"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    paths["metadata"].write_text(
        json.dumps(pack["metadata"], indent=2) + "\n",
        encoding="utf-8",
    )
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export web demo JSON pack with simulated on-road PM."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for scenarios.json / routes.json / metadata.json",
    )
    args = parser.parse_args(argv)
    pack = build_demo_pack()
    paths = write_demo_pack(args.output_dir, pack)
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "scenario_count": len(pack["scenarios"]),  # type: ignore[arg-type]
                "route_count": len(pack["routes"]),  # type: ignore[arg-type]
                "demo_tradeoff_scan": pack["metadata"]["demo_tradeoff_scan"],  # type: ignore[index]
                "files": {key: str(path) for key, path in paths.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
