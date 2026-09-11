"""Bake demo-nav junction / lane / bridge cues from frozen candidates + OSM.

Does not regenerate candidates, IDW, or the optimizer. Output is a sidecar
JSON keyed by scenario/mode/route_id so the web app can overlay diagrams.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .demo_street_pm import load_way_attributes, parse_lane_count, way_id_from_edge_id
from .web_demo_export import (
    CANDIDATE_PATH,
    DEFAULT_OUTPUT_DIR,
    OD_PATH,
    select_demo_scenarios,
)

EARTH_RADIUS_M = 6_371_000
MIN_TURN_DEG = 32
LOOK_M = 18
WIDE_LANES = 4
LANE_LEAD_M = 15
ROUNDABOUT_CLUSTER_M = 22
ARM_BIN_DEG = 36.0
BRIDGE_SNAP_M = 12
BRIDGE_CLUSTER_M = 140
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    h = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dλ = lon2 - lon1
    y = math.sin(dλ) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dλ)
    return math.degrees(math.atan2(y, x))


def angle_diff_deg(frm: float, to: float) -> float:
    return (to - frm + 540) % 360 - 180


def cumulative_m(geometry: list[tuple[float, float]]) -> list[float]:
    out = [0.0]
    for i in range(1, len(geometry)):
        out.append(out[-1] + haversine_m(geometry[i - 1], geometry[i]))
    return out


def point_along(
    geometry: list[tuple[float, float]], distance_m: float
) -> tuple[float, float]:
    if not geometry:
        raise ValueError("empty geometry")
    if len(geometry) == 1 or distance_m <= 0:
        return geometry[0]
    cum = cumulative_m(geometry)
    if distance_m >= cum[-1]:
        return geometry[-1]
    for i in range(1, len(cum)):
        if cum[i] >= distance_m:
            span = cum[i] - cum[i - 1]
            t = 0.0 if span <= 0 else (distance_m - cum[i - 1]) / span
            a, b = geometry[i - 1], geometry[i]
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    return geometry[-1]


def classify_turn(delta: float) -> str | None:
    if delta > MIN_TURN_DEG:
        return "right"
    if delta < -MIN_TURN_DEG:
        return "left"
    return None


def turn_at(geometry: list[tuple[float, float]], at_m: float) -> str | None:
    cum = cumulative_m(geometry)
    route_len = cum[-1] if cum else 0.0
    if route_len < 12:
        return None
    at = min(max(at_m, 0.0), route_len)
    back = min(LOOK_M, at)
    fwd = min(LOOK_M, route_len - at)
    if back < 5 or fwd < 5:
        return None
    a = point_along(geometry, at - back)
    b = point_along(geometry, at)
    c = point_along(geometry, at + fwd)
    if haversine_m(a, b) < 5 or haversine_m(b, c) < 5:
        return None
    return classify_turn(angle_diff_deg(bearing_deg(a, b), bearing_deg(b, c)))


def parse_geometry(raw: str) -> list[tuple[float, float]]:
    return [(float(lat), float(lon)) for lat, lon in ast.literal_eval(raw)]


def parse_edges(raw: str) -> list[str]:
    return [str(edge) for edge in ast.literal_eval(raw)]


def runs(flags: list[bool]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j < len(flags) and flags[j]:
            j += 1
        out.append((i, j))
        i = j
    return out


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    )


def heading_ccw_sweep(h0: float, h1: float) -> float:
    """Degrees traveled circulating CCW (island on the left, Vietnam RHT)."""
    return (h0 - h1) % 360


def quantize_bearing(deg: float, bin_deg: float = ARM_BIN_DEG) -> int:
    n = max(1, int(round(360.0 / bin_deg)))
    return int(round((deg % 360) / bin_deg) % n)


def exit_from_sweep(sweep: float, arm_count: int) -> int:
    """Map CCW ring travel onto evenly spaced exits (1 = first right in VN RHT)."""
    n = max(3, min(7, arm_count))
    span = sweep if sweep >= 35 else 90.0
    step = 360.0 / n
    return max(1, min(n - 1, int(span / step + 0.35)))


def infer_exit(entry_bearing: float, exit_bearing: float, arm_count: int) -> int:
    """Fallback when only approach/leave bearings are available."""
    return exit_from_sweep(heading_ccw_sweep(entry_bearing, exit_bearing), arm_count)


def collect_roundabout_arms(
    clusters: list[dict[str, Any]],
) -> None:
    """Count real arms from routes on the same island; draw them evenly."""
    originals = [
        (
            cluster["entry_bearing"] % 360,
            cluster["exit_bearing"] % 360,
            cluster["center"],
        )
        for cluster in clusters
    ]
    for cluster in clusters:
        bears: list[float] = [
            cluster["entry_bearing"] % 360,
            cluster["exit_bearing"] % 360,
        ]
        for entry, leave, center in originals:
            if haversine_m(cluster["center"], center) > ROUNDABOUT_CLUSTER_M:
                continue
            bears.extend([entry, leave])
        bins: dict[int, list[float]] = {}
        for bearing in bears:
            key = quantize_bearing(bearing)
            bins.setdefault(key, []).append(bearing)
        n = max(3, min(7, len(bins)))
        cluster["arms"] = n
        sweep = float(
            cluster.get("sweep_deg")
            or heading_ccw_sweep(cluster["entry_bearing"], cluster["exit_bearing"])
        )
        if sweep < 35:
            sweep = 90.0
        cluster["sweep_deg"] = round(sweep, 1)
        cluster["exit"] = exit_from_sweep(sweep, n)
        cluster["arm_deg"] = [int(i * 360 / n) for i in range(n)]


def roundabout_cues_for_route(
    geometry: list[tuple[float, float]],
    edges: list[str],
    way_lookup: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    flags = [
        way_lookup.get(way_id_from_edge_id(edge), {}).get("junction") == "roundabout"
        for edge in edges
    ]
    cum = cumulative_m(geometry)
    cues: list[dict[str, Any]] = []
    for start, end in runs(flags):
        pts = geometry[start : end + 1]
        if len(pts) < 2:
            continue
        center = centroid(pts)
        entry_pt = geometry[max(0, start - 1)]
        exit_pt = geometry[min(len(geometry) - 1, end)]
        entry_bearing = bearing_deg(entry_pt, geometry[start])
        leave_a = geometry[max(start, end - 2)]
        leave_b = geometry[min(len(geometry) - 1, end)]
        exit_bearing = bearing_deg(leave_a, leave_b)
        ring_a = geometry[start]
        ring_b = geometry[min(end, start + 1)]
        ring_start_h = bearing_deg(ring_a, ring_b)
        ring_end_h = exit_bearing
        sweep = heading_ccw_sweep(ring_start_h, ring_end_h)
        cues.append(
            {
                "kind": "roundabout",
                "lat": round(center[0], 7),
                "lng": round(center[1], 7),
                "center": center,
                "entry_bearing": entry_bearing,
                "exit_bearing": exit_bearing,
                "sweep_deg": round(sweep, 1),
                "at_hint_m": cum[start],
            }
        )
    return cues


def lane_cues_for_route(
    geometry: list[tuple[float, float]],
    edges: list[str],
    way_lookup: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    lanes = [
        parse_lane_count(way_lookup.get(way_id_from_edge_id(edge), {}).get("lanes"))
        for edge in edges
    ]
    wide = [count is not None and count >= WIDE_LANES for count in lanes]
    cum = cumulative_m(geometry)
    cues: list[dict[str, Any]] = []
    for start, end in runs(wide):
        count = max(lanes[i] or WIDE_LANES for i in range(start, end))
        turn_m = None
        turn = None
        search_from = max(0.0, cum[start] - 8)
        search_to = min(cum[-1], cum[min(end, len(cum) - 1)] + 55)
        step = 6.0
        at = search_from
        while at <= search_to:
            hit = turn_at(geometry, at)
            if hit in {"left", "right"}:
                turn = hit
                turn_m = at
                break
            at += step
        if turn is None or turn_m is None:
            continue
        lead = max(cum[start], turn_m - LANE_LEAD_M)
        pt = point_along(geometry, lead)
        target = 0 if turn == "left" else max(0, int(count) - 1)
        cues.append(
            {
                "kind": "lane",
                "lat": round(pt[0], 7),
                "lng": round(pt[1], 7),
                "lanes": int(count),
                "turn": turn,
                "target": target,
            }
        )
    return cues


OVERPASS_CACHE = Path("/tmp/airpath-overpass-grade.json")


def fetch_overpass_grade() -> dict[str, Any] | None:
    if OVERPASS_CACHE.is_file():
        try:
            cached = json.loads(OVERPASS_CACHE.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and isinstance(cached.get("elements"), list):
                return cached
        except json.JSONDecodeError:
            pass
    south, west, north, east = 10.746, 106.617, 10.816, 106.701
    query = (
        "[out:json][timeout:90];\n"
        "(\n"
        f'  way["highway"]["bridge"]({south},{west},{north},{east});\n'
        f'  way["highway"]["tunnel"]({south},{west},{north},{east});\n'
        ");\n"
        "out tags geom;"
    )
    last_error: Exception | None = None
    for url in OVERPASS_MIRRORS:
        try:
            request = Request(
                url,
                data=urlencode({"data": query}).encode("utf-8"),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "AIRPATH-AI-research-prototype/guidance-cues",
                },
                method="POST",
            )
            with urlopen(request, timeout=120) as response:
                payload = json.load(response)
            if isinstance(payload, dict) and isinstance(payload.get("elements"), list):
                OVERPASS_CACHE.write_text(
                    json.dumps(payload), encoding="utf-8"
                )
                return payload
        except Exception as exc:  # noqa: BLE001 — fallback to geometry heuristic
            last_error = exc
            continue
    print(f"overpass unavailable ({last_error})")
    return None


def index_grade_ways(
    payload: dict[str, Any] | None,
) -> tuple[set[str], set[str], list[dict[str, Any]]]:
    bridges: set[str] = set()
    tunnels: set[str] = set()
    geoms: list[dict[str, Any]] = []
    if not payload:
        return bridges, tunnels, geoms
    for element in payload.get("elements", []):
        if not isinstance(element, dict) or element.get("type") != "way":
            continue
        way_id = str(element.get("id"))
        tags = element.get("tags") or {}
        geometry = element.get("geometry") or []
        pts = [
            (float(node["lat"]), float(node["lon"]))
            for node in geometry
            if isinstance(node, dict) and "lat" in node and "lon" in node
        ]
        is_bridge = bool(tags.get("bridge"))
        is_tunnel = bool(tags.get("tunnel"))
        if is_bridge:
            bridges.add(way_id)
        if is_tunnel:
            tunnels.add(way_id)
        if pts and (is_bridge or is_tunnel):
            geoms.append(
                {
                    "way_id": way_id,
                    "relation": "under" if is_tunnel and not is_bridge else "over",
                    "pts": pts,
                    "center": centroid(pts),
                }
            )
    return bridges, tunnels, geoms


def nearest_on_route(
    geometry: list[tuple[float, float]], target: tuple[float, float]
) -> tuple[float, tuple[float, float]]:
    best_d = float("inf")
    best_pt = geometry[0]
    best_m = 0.0
    cum = cumulative_m(geometry)
    for i, pt in enumerate(geometry):
        d = haversine_m(pt, target)
        if d < best_d:
            best_d = d
            best_pt = pt
            best_m = cum[i]
    return best_m, best_pt


def route_uses_way(edges: list[str], way_id: str) -> bool:
    return any(way_id_from_edge_id(edge) == way_id for edge in edges)


def heading_along(
    geometry: list[tuple[float, float]], index: int
) -> float:
    i = min(max(index, 0), len(geometry) - 2)
    return bearing_deg(geometry[i], geometry[i + 1])


def feature_heading(pts: list[tuple[float, float]]) -> float:
    if len(pts) < 2:
        return 0.0
    mid = len(pts) // 2
    return bearing_deg(pts[max(0, mid - 1)], pts[min(len(pts) - 1, mid)])


def cluster_bridge_cues(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clustered: list[dict[str, Any]] = []
    for cue in cues:
        pt = (float(cue["lat"]), float(cue["lng"]))
        merged = False
        for prev in clustered:
            other = (float(prev["lat"]), float(prev["lng"]))
            if haversine_m(pt, other) <= BRIDGE_CLUSTER_M:
                if prev["relation"] == "over" or cue["relation"] == "over":
                    prev["relation"] = "over"
                merged = True
                break
        if not merged:
            clustered.append(cue)
    return clustered


def bridge_cues_for_route(
    geometry: list[tuple[float, float]],
    edges: list[str],
    bridges: set[str],
    tunnels: set[str],
    grade_geoms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    seen: list[tuple[float, float]] = []

    def add(pt: tuple[float, float], relation: str) -> None:
        for prev in seen:
            if haversine_m(prev, pt) < BRIDGE_CLUSTER_M:
                return
        seen.append(pt)
        cues.append(
            {
                "kind": "bridge",
                "lat": round(pt[0], 7),
                "lng": round(pt[1], 7),
                "relation": relation,
            }
        )

    for i, edge in enumerate(edges):
        way_id = way_id_from_edge_id(edge)
        if way_id in tunnels:
            add(centroid([geometry[i], geometry[i + 1]]), "under")
        elif way_id in bridges:
            add(centroid([geometry[i], geometry[i + 1]]), "over")

    cum = cumulative_m(geometry)
    for feature in grade_geoms:
        if route_uses_way(edges, feature["way_id"]):
            continue
        at_m, pt = nearest_on_route(geometry, feature["center"])
        if haversine_m(pt, feature["center"]) > BRIDGE_SNAP_M:
            continue
        # Parallel frontage roads sit next to flyovers; keep only crossings.
        idx = min(
            range(len(geometry) - 1),
            key=lambda i: abs(cum[i] - at_m),
        )
        route_h = heading_along(geometry, idx)
        other_h = feature_heading(feature["pts"])
        skew = abs(angle_diff_deg(route_h, other_h))
        if min(skew, 180 - skew) < 38:
            continue
        add(pt, "under")
    return cluster_bridge_cues(cues)


def segment_intersection(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> tuple[float, float] | None:
    def to_xy(p: tuple[float, float]) -> tuple[float, float]:
        return (p[1] * 111_320 * math.cos(math.radians(p[0])), p[0] * 110_540)

    ax, ay = to_xy(a1)
    bx, by = to_xy(a2)
    cx, cy = to_xy(b1)
    dx, dy = to_xy(b2)
    den = (ax - bx) * (cy - dy) - (ay - by) * (cx - dx)
    if abs(den) < 1e-9:
        return None
    t = ((ax - cx) * (cy - dy) - (ay - cy) * (cx - dx)) / den
    u = ((ax - cx) * (ay - by) - (ay - cy) * (ax - bx)) / den
    if t <= 0.08 or t >= 0.92 or u <= 0.08 or u >= 0.92:
        return None
    lat = a1[0] + t * (a2[0] - a1[0])
    lon = a1[1] + t * (a2[1] - a1[1])
    return (lat, lon)


def geometric_bridge_fallback(
    routes: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """If OSM bridge tags are missing, treat proper polyline crossings as grade-separated."""
    extra: dict[str, list[dict[str, Any]]] = {row["key"]: [] for row in routes}
    for i, a in enumerate(routes):
        ga = a["geometry"]
        for b in routes[i + 1 :]:
            if a["scenario_id"] == b["scenario_id"] and a["mode"] == b["mode"]:
                # Same OD/mode family: crossings are usually shared junctions.
                continue
            gb = b["geometry"]
            for ia in range(len(ga) - 1):
                if haversine_m(ga[ia], ga[ia + 1]) < 8:
                    continue
                for ib in range(len(gb) - 1):
                    if haversine_m(gb[ib], gb[ib + 1]) < 8:
                        continue
                    hit = segment_intersection(ga[ia], ga[ia + 1], gb[ib], gb[ib + 1])
                    if hit is None:
                        continue
                    near_a = min(haversine_m(hit, ga[ia]), haversine_m(hit, ga[ia + 1]))
                    near_b = min(haversine_m(hit, gb[ib]), haversine_m(hit, gb[ib + 1]))
                    if near_a < 10 or near_b < 10:
                        continue
                    extra[a["key"]].append(
                        {
                            "kind": "bridge",
                            "lat": round(hit[0], 7),
                            "lng": round(hit[1], 7),
                            "relation": "over",
                        }
                    )
                    extra[b["key"]].append(
                        {
                            "kind": "bridge",
                            "lat": round(hit[0], 7),
                            "lng": round(hit[1], 7),
                            "relation": "under",
                        }
                    )
    return extra


def route_key(scenario_id: str, mode: str, route_id: str) -> str:
    return f"{scenario_id}|{mode}|{route_id}"


def public_cue(raw: dict[str, Any]) -> dict[str, Any]:
    if raw["kind"] == "roundabout":
        out = {
            "kind": "roundabout",
            "lat": raw["lat"],
            "lng": raw["lng"],
            "exit": int(raw["exit"]),
            "arms": int(raw["arms"]),
            "arm_deg": [int(v) for v in raw["arm_deg"]],
        }
        if raw.get("sweep_deg") is not None:
            out["sweep_deg"] = int(round(float(raw["sweep_deg"])))
        return out
    if raw["kind"] == "lane":
        return {
            "kind": "lane",
            "lat": raw["lat"],
            "lng": raw["lng"],
            "lanes": int(raw["lanes"]),
            "turn": raw["turn"],
            "target": int(raw["target"]),
        }
    return {
        "kind": "bridge",
        "lat": raw["lat"],
        "lng": raw["lng"],
        "relation": raw["relation"],
    }


def build_cues(
    *,
    candidate_path: Path = CANDIDATE_PATH,
    od_path: Path = OD_PATH,
    output_path: Path | None = None,
) -> dict[str, Any]:
    od = select_demo_scenarios(pd.read_csv(od_path))
    demo_ids = [str(sid) for sid in od["scenario_id"].tolist()]
    candidates = pd.read_csv(candidate_path)
    demo = candidates.loc[candidates["scenario_id"].astype(str).isin(demo_ids)].copy()
    way_lookup = load_way_attributes()
    unique = demo.drop_duplicates(["scenario_id", "mode", "route_id"])

    overpass = fetch_overpass_grade()
    bridges, tunnels, grade_geoms = index_grade_ways(overpass)

    routes: list[dict[str, Any]] = []
    all_roundabouts: list[dict[str, Any]] = []
    for row in unique.itertuples(index=False):
        scenario_id = str(row.scenario_id)
        mode = str(row.mode)
        route_id = str(row.route_id)
        geometry = parse_geometry(str(row.geometry))
        edges = parse_edges(str(row.ordered_edge_ids))
        key = route_key(scenario_id, mode, route_id)
        rbs = roundabout_cues_for_route(geometry, edges, way_lookup)
        for cue in rbs:
            cue["_key"] = key
            all_roundabouts.append(cue)
        routes.append(
            {
                "key": key,
                "scenario_id": scenario_id,
                "mode": mode,
                "route_id": route_id,
                "geometry": geometry,
                "edges": edges,
                "roundabouts": rbs,
                "lanes": lane_cues_for_route(geometry, edges, way_lookup),
                "bridges": bridge_cues_for_route(
                    geometry, edges, bridges, tunnels, grade_geoms
                ),
            }
        )

    collect_roundabout_arms(all_roundabouts)

    if not bridges and not tunnels:
        extra = geometric_bridge_fallback(routes)
        for row in routes:
            if row["bridges"]:
                continue
            row["bridges"] = extra.get(row["key"], [])[:4]

    by_route: dict[str, list[dict[str, Any]]] = {}
    for row in routes:
        cues = [public_cue(c) for c in row["roundabouts"]]
        cues.extend(row["lanes"])
        cues.extend(row["bridges"])
        by_route[row["key"]] = cues

    payload = {
        "purpose": (
            "Demo navigation diagrams for roundabouts, lane changes, and "
            "bridges. OSM tags + frozen candidate geometry. Not live routing."
        ),
        "source": "OpenStreetMap contributors, ODbL 1.0",
        "trigger_m": {"roundabout": 10, "lane": 15, "bridge": 20, "hud": 20},
        "overpass_used": bool(overpass),
        "bridge_way_count": len(bridges),
        "tunnel_way_count": len(tunnels),
        "routes": by_route,
    }
    dest = output_path or (DEFAULT_OUTPUT_DIR / "guidance_cues.json")
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {"roundabout": 0, "lane": 0, "bridge": 0}
    for cues in by_route.values():
        for cue in cues:
            counts[str(cue["kind"])] += 1
    print(
        f"wrote {dest} routes={len(by_route)} "
        f"roundabouts={counts['roundabout']} lanes={counts['lane']} "
        f"bridges={counts['bridge']} overpass={bool(overpass)}"
    )
    return payload


def rebuild_roundabout_sidecar(
    *,
    candidate_path: Path = CANDIDATE_PATH,
    od_path: Path = OD_PATH,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Rewrite roundabout fields only. Keeps baked lane/bridge cues (no Overpass)."""
    dest = output_path or (DEFAULT_OUTPUT_DIR / "guidance_cues.json")
    existing = json.loads(dest.read_text(encoding="utf-8"))
    od = select_demo_scenarios(pd.read_csv(od_path))
    demo_ids = [str(sid) for sid in od["scenario_id"].tolist()]
    candidates = pd.read_csv(candidate_path)
    demo = candidates.loc[candidates["scenario_id"].astype(str).isin(demo_ids)].copy()
    way_lookup = load_way_attributes()
    unique = demo.drop_duplicates(["scenario_id", "mode", "route_id"])

    all_roundabouts: list[dict[str, Any]] = []
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in unique.itertuples(index=False):
        scenario_id = str(row.scenario_id)
        mode = str(row.mode)
        route_id = str(row.route_id)
        geometry = parse_geometry(str(row.geometry))
        edges = parse_edges(str(row.ordered_edge_ids))
        key = route_key(scenario_id, mode, route_id)
        rbs = roundabout_cues_for_route(geometry, edges, way_lookup)
        for cue in rbs:
            cue["_key"] = key
            all_roundabouts.append(cue)
        by_key[key] = rbs

    collect_roundabout_arms(all_roundabouts)
    routes = existing.setdefault("routes", {})
    for key, rbs in by_key.items():
        rest = [c for c in routes.get(key, []) if c.get("kind") != "roundabout"]
        routes[key] = [public_cue(c) for c in rbs] + rest

    dest.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    count = sum(
        1
        for cues in routes.values()
        for cue in cues
        if cue.get("kind") == "roundabout"
    )
    print(f"updated roundabouts={count} routes={len(by_key)} -> {dest}")
    return existing


if __name__ == "__main__":
    import sys

    if "--roundabouts-only" in sys.argv:
        rebuild_roundabout_sidecar()
    else:
        build_cues()
