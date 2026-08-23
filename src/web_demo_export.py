"""Export a compact frozen Model-C web demo pack (no scientific recompute).

Reads P0-3 unperturbed shortlists (perturbation_scale=1.0) and joins
P0-2B candidate geometry. Does not retrain models, run IDW, or re-optimize
routes — it only packages already-frozen research outputs for the demo API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final, Sequence

import pandas as pd

from .route_optimizer import TIME_TOLERANCES_MINUTES

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR: Final[Path] = REPO_ROOT / "data" / "processed" / "web_demo"
SHORTLIST_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "final_robustness" / "perturbed_shortlists.csv"
)
CANDIDATE_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "temporal_gap_analysis" / "candidate_routes.csv"
)
OD_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "temporal_gap_analysis" / "od_scenarios.csv"
)
FREEZE_MANIFEST_PATH: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "final_robustness" / "freeze_manifest.json"
)

# Representative demo departure from the P0-2B / P0-3 panel.
DEMO_DEPARTURE_TIME: Final[str] = "2022-02-27T06:00:00"
DEMO_FORECASTING_ORIGIN: Final[str] = "2022-02-27T05:00:00"
SUPPORTED_MODES: Final[tuple[str, ...]] = ("walking", "motorbike")
# Evenly spaced distance ranks among the 30 P0-2B OD pairs (sorted by km).
DEMO_DISTANCE_RANKS: Final[tuple[int, ...]] = (0, 4, 8, 12, 16, 20, 24, 29)
RESEARCH_WARNING: Final[str] = (
    "PM2.5 values are forecast-based spatial estimates derived from an hourly "
    "monitoring network. Exposure is a time-weighted PM2.5 proxy, not a direct "
    "measure of inhaled dose or health risk. Road-level PM2.5 is estimated "
    "(IDW p=1 over six stations), not measured. Pilot area only; no live traffic."
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


def build_demo_pack(
    *,
    shortlist_path: Path = SHORTLIST_PATH,
    candidate_path: Path = CANDIDATE_PATH,
    od_path: Path = OD_PATH,
    freeze_manifest_path: Path = FREEZE_MANIFEST_PATH,
    departure_time: str = DEMO_DEPARTURE_TIME,
    modes: Sequence[str] = SUPPORTED_MODES,
    deltas: Sequence[float] = TIME_TOLERANCES_MINUTES,
) -> dict[str, object]:
    """Assemble scenarios/routes/metadata from frozen Model-C artifacts."""
    if not shortlist_path.is_file():
        raise FileNotFoundError(f"Missing frozen shortlist: {shortlist_path}")
    if not candidate_path.is_file():
        raise FileNotFoundError(f"Missing candidate geometry: {candidate_path}")
    if not od_path.is_file():
        raise FileNotFoundError(f"Missing OD scenarios: {od_path}")

    od_all = pd.read_csv(od_path)
    selected_od = select_demo_scenarios(od_all)
    scenario_ids = list(selected_od["scenario_id"].astype(str))

    shortlist = pd.read_csv(shortlist_path)
    required_shortlist = {
        "perturbation_scale",
        "departure_time",
        "scenario_id",
        "mode",
        "delta_time_allowed_minutes",
        "route_id",
        "rank",
        "route_type",
        "travel_time_minutes",
        "predicted_exposure_index",
        "available_feasible_alternatives",
        "fewer_than_requested_alternatives",
    }
    missing = required_shortlist - set(shortlist.columns)
    if missing:
        raise ValueError(f"Shortlist missing columns: {sorted(missing)}")

    base = shortlist.loc[
        (shortlist["perturbation_scale"].astype(float) == 1.0)
        & (shortlist["departure_time"].astype(str) == departure_time)
        & (shortlist["scenario_id"].astype(str).isin(scenario_ids))
        & (shortlist["mode"].astype(str).isin(list(modes)))
        & (shortlist["delta_time_allowed_minutes"].astype(float).isin([float(d) for d in deltas]))
    ].copy()
    if base.empty:
        raise ValueError("No unperturbed shortlist rows matched the demo filters.")

    candidates = pd.read_csv(candidate_path)
    cand_cols = [
        "scenario_id",
        "mode",
        "route_id",
        "geometry",
        "distance_m",
        "additional_time_vs_fastest_minutes",
        "is_fastest",
    ]
    missing_cand = set(cand_cols) - set(candidates.columns)
    if missing_cand:
        raise ValueError(f"Candidates missing columns: {sorted(missing_cand)}")

    merged = base.merge(
        candidates[cand_cols],
        on=["scenario_id", "mode", "route_id"],
        how="left",
        validate="many_to_one",
    )
    if merged["geometry"].isna().any():
        bad = merged.loc[merged["geometry"].isna(), ["scenario_id", "mode", "route_id"]]
        raise ValueError(f"Geometry join failed for rows:\n{bad.to_string(index=False)}")

    freeze: dict[str, object] = {}
    if freeze_manifest_path.is_file():
        freeze = json.loads(freeze_manifest_path.read_text(encoding="utf-8"))

    routes: list[dict[str, object]] = []
    for (scenario_id, mode, delta), group in merged.groupby(
        ["scenario_id", "mode", "delta_time_allowed_minutes"], sort=True
    ):
        fastest_rows = group.loc[group["route_type"].astype(str) == "fastest"]
        if len(fastest_rows) != 1:
            raise AssertionError(
                f"Expected exactly one fastest route for "
                f"{scenario_id}/{mode}/+{delta}, found {len(fastest_rows)}."
            )
        fastest_exposure = float(fastest_rows.iloc[0]["predicted_exposure_index"])
        ordered = group.sort_values(["rank", "route_id"], kind="mergesort")
        available_alts = int(ordered.iloc[0]["available_feasible_alternatives"])
        fewer = bool(ordered.iloc[0]["fewer_than_requested_alternatives"])
        for row in ordered.itertuples(index=False):
            exposure = float(row.predicted_exposure_index)
            is_fastest = str(row.route_type) == "fastest" or bool(row.is_fastest)
            routes.append(
                {
                    "scenario_id": str(scenario_id),
                    "mode": str(mode),
                    "delta_minutes": float(delta),
                    "route_id": str(row.route_id),
                    "route_type": str(row.route_type),
                    "rank": int(row.rank),
                    "is_fastest": bool(is_fastest),
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
            }
        )

    metadata: dict[str, object] = {
        "pack_name": "airpath_web_demo_v1",
        "forecaster": freeze.get("frozen_forecaster", "C_xgboost_current_pm"),
        "spatial_model": freeze.get("spatial_model", "idw_p1"),
        "exposure_definition": freeze.get(
            "exposure_definition", "sum_pm25_times_duration_minutes"
        ),
        "route_selector": freeze.get(
            "route_selector",
            "absolute_minute_feasible_min_predicted_exposure_plus_top3",
        ),
        "departure_time": departure_time,
        "forecasting_origin": DEMO_FORECASTING_ORIGIN,
        "source_artifacts": {
            "shortlist": str(shortlist_path.relative_to(REPO_ROOT)),
            "shortlist_filter": "perturbation_scale == 1.0 (unperturbed Model C)",
            "candidates": str(candidate_path.relative_to(REPO_ROOT)),
            "od_scenarios": str(od_path.relative_to(REPO_ROOT)),
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
        "supported_modes": list(modes),
        "supported_delta_minutes": [float(d) for d in deltas],
        "exposure_unit": "(µg/m³)·min",
        "research_warning": RESEARCH_WARNING,
        "limitations": [
            "Hourly HealthyAir resolution; segment ETA maps to hourly forecast buckets.",
            "Six-station pilot support (stations 2–6 polygon); road PM2.5 is estimated.",
            "No road-level ground-truth PM2.5.",
            "Constant-speed ETA; no live traffic.",
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
        description="Export frozen Model-C web demo JSON pack (packaging only)."
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
                "files": {key: str(path) for key, path in paths.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
