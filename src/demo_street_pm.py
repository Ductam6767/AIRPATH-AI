"""Demo-only simulated on-road PM2.5 layer.

The frozen research engine still estimates road PM2.5 by IDW p=1 from six
stations. That field is spatially smooth, so feasible alternatives almost never
beat the fastest route on predicted exposure.

This module is used only when packaging the web demo. It keeps the station IDW
value as the *background*, then applies a deterministic on-road increment from
OSM traffic class — the same two-layer idea used in Chinese mobile-monitoring
(走航监测) studies (background from fixed stations, extra pollution on busy
roads). It does **not** ingest those Chinese vehicle datasets.

Traffic volume and congestion are not observed live. They are proxied by:
- OSM `highway` class (arterials > residential > footway)
- extra lanes
- junction tags
- a modest morning-peak factor at 06:00 on arterials

Simulated segment PM = background_IDW × road_factor × lane_factor
    × peak_factor × junction_factor
Route exposure remains Σ PM × duration_minutes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Mapping

import pandas as pd

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_WAY_LOOKUP: Final[Path] = (
    REPO_ROOT / "data" / "processed" / "web_demo" / "osm_way_traffic_attributes.json"
)
DEFAULT_SEGMENT_PATH: Final[Path] = (
    REPO_ROOT
    / "data"
    / "processed"
    / "temporal_gap_analysis"
    / "segment_exposure_comparison_0600.csv.gz"
)

# Relative to urban-background IDW. Illustrative, not calibrated to HCMC counts.
ROAD_CLASS_FACTOR: Final[dict[str, float]] = {
    "motorway": 1.55,
    "motorway_link": 1.50,
    "trunk": 1.50,
    "trunk_link": 1.45,
    "primary": 1.45,
    "primary_link": 1.38,
    "secondary": 1.28,
    "secondary_link": 1.22,
    "tertiary": 1.12,
    "tertiary_link": 1.08,
    "unclassified": 1.04,
    "residential": 0.90,
    "living_street": 0.86,
    "service": 0.88,
    "pedestrian": 0.82,
    "footway": 0.80,
    "path": 0.80,
    "cycleway": 0.80,
    "steps": 0.78,
}
ARTERIAL_HIGHWAYS: Final[frozenset[str]] = frozenset(
    {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
    }
)
PM_MIN: Final[float] = 1.0
PM_MAX: Final[float] = 500.0


def parse_lane_count(raw: str | None) -> int | None:
    if not raw:
        return None
    token = str(raw).split(";")[0].split("|")[0].strip()
    try:
        value = int(float(token))
    except ValueError:
        return None
    return value if value > 0 else None


def lane_factor(lanes: int | None) -> float:
    if lanes is None:
        return 1.0
    if lanes >= 6:
        return 1.10
    if lanes >= 4:
        return 1.06
    if lanes >= 3:
        return 1.03
    return 1.0


def peak_factor(hour: int, highway: str) -> float:
    """Congestion proxy from clock time × arterial class. Not live traffic."""
    if highway not in ARTERIAL_HIGHWAYS:
        return 1.0
    if hour in {7, 8, 17, 18}:
        return 1.20
    if hour in {6, 9, 16, 19}:
        return 1.12
    return 1.04


def junction_factor(junction: str | None) -> float:
    if junction:
        return 1.06
    return 1.0


def road_class_factor(highway: str | None) -> float:
    if not highway:
        return 1.0
    return float(ROAD_CLASS_FACTOR.get(highway, 1.0))


def simulate_segment_pm(
    background_pm25: float,
    *,
    highway: str | None,
    lanes: int | None = None,
    hour: int = 6,
    junction: str | None = None,
) -> float:
    """Scale station-interpolated PM by simulated on-road traffic intensity."""
    background = float(background_pm25)
    if not pd.notna(background) or background < 0:
        raise ValueError("background_pm25 must be a non-negative finite number.")
    simulated = (
        background
        * road_class_factor(highway)
        * lane_factor(lanes)
        * peak_factor(hour, highway or "")
        * junction_factor(junction)
    )
    return float(min(PM_MAX, max(PM_MIN, simulated)))


def load_way_attributes(path: Path = DEFAULT_WAY_LOOKUP) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing OSM traffic-class lookup for the demo simulation: {path}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    ways = payload.get("ways")
    if not isinstance(ways, dict):
        raise ValueError("OSM lookup file must contain a 'ways' object.")
    return {str(way_id): dict(tags) for way_id, tags in ways.items()}


def way_id_from_edge_id(edge_id: str) -> str:
    return str(edge_id).split(":")[0]


def attributes_for_edge(
    edge_id: str, way_lookup: Mapping[str, Mapping[str, str]]
) -> dict[str, str]:
    return dict(way_lookup.get(way_id_from_edge_id(edge_id), {}))


def load_background_segments(
    *,
    scenario_ids: list[str],
    path: Path = DEFAULT_SEGMENT_PATH,
) -> pd.DataFrame:
    """Station-IDW (AIRPATH) segment PM and duration at the demo departure."""
    columns = [
        "scenario_id",
        "route_id",
        "mode",
        "pipeline_mode",
        "segment_id",
        "segment_duration_minutes",
        "pm25_estimate",
    ]
    frame = pd.read_csv(path, usecols=columns)
    selected = frame.loc[
        (frame["pipeline_mode"] == "airpath_arrival_time_exposure")
        & (frame["scenario_id"].astype(str).isin(scenario_ids))
    ].copy()
    if selected.empty:
        raise ValueError("No AIRPATH segment rows matched the demo scenarios.")
    return selected


def simulate_route_exposures(
    segments: pd.DataFrame,
    way_lookup: Mapping[str, Mapping[str, str]],
    *,
    hour: int = 6,
) -> pd.DataFrame:
    """Return one simulated exposure index per scenario/mode/route."""
    if segments.empty:
        raise ValueError("Segment table is empty.")
    highways: list[str | None] = []
    lane_counts: list[int | None] = []
    junctions: list[str | None] = []
    simulated_pm: list[float] = []
    for row in segments.itertuples(index=False):
        tags = attributes_for_edge(str(row.segment_id), way_lookup)
        highway = tags.get("highway")
        lanes = parse_lane_count(tags.get("lanes"))
        junction = tags.get("junction")
        highways.append(highway)
        lane_counts.append(lanes)
        junctions.append(junction)
        simulated_pm.append(
            simulate_segment_pm(
                float(row.pm25_estimate),
                highway=highway,
                lanes=lanes,
                hour=hour,
                junction=junction,
            )
        )
    working = segments.copy()
    working["simulated_pm25"] = simulated_pm
    working["exposure_contribution"] = (
        working["simulated_pm25"] * working["segment_duration_minutes"].astype(float)
    )
    working["background_contribution"] = (
        working["pm25_estimate"].astype(float)
        * working["segment_duration_minutes"].astype(float)
    )
    return working.groupby(["scenario_id", "mode", "route_id"], as_index=False).agg(
        predicted_exposure_index=("exposure_contribution", "sum"),
        background_exposure_index=("background_contribution", "sum"),
        mean_simulated_pm25=("simulated_pm25", "mean"),
        mean_background_pm25=("pm25_estimate", "mean"),
    )
