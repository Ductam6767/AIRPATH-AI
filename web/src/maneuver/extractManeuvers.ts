import {
  angleDiffDeg,
  bearingDeg,
  cumulativeDistances,
  distanceM,
  pointAlongRoute,
} from './geo'
import type { Maneuver, TurnDirection } from './types'

/** Short window: HCMC hẻm legs are often 12–30 m. */
const LOOK_SHORT_M = 14
/** Longer window: dense OSM vertices on a wide arterial corner. */
const LOOK_LONG_M = 36
const MIN_SAMPLE_M = 5
const MIN_TURN_DEG = 32
/** Keep the strongest same-direction hit on one corner. */
const PEAK_RADIUS_M = 20
/** Merge leftover same-direction hits on one vertex cluster. */
const MERGE_SAME_M = 14
/** Collapse opposite OSM kinks that sit on the same vertex cluster. */
const MERGE_OPPOSITE_M = 8

/**
 * Navigation bearings: 0° north, +90° east.
 * Positive angleDiff (clockwise) is a right turn for the traveler.
 */
export function classifyTurn(deltaDeg: number): TurnDirection {
  if (deltaDeg > MIN_TURN_DEG) return 'right'
  if (deltaDeg < -MIN_TURN_DEG) return 'left'
  return 'straight'
}

export function turnDeltaAt(
  geometry: [number, number][],
  distanceAlongM: number,
  lookM: number = LOOK_SHORT_M,
): number | null {
  const cum = cumulativeDistances(geometry)
  const routeLen = cum[cum.length - 1] ?? 0
  if (routeLen < MIN_SAMPLE_M * 2) return null
  const at = Math.min(Math.max(distanceAlongM, 0), routeLen)
  const back = Math.min(lookM, at)
  const fwd = Math.min(lookM, routeLen - at)
  if (back < MIN_SAMPLE_M || fwd < MIN_SAMPLE_M) return null
  const a = pointAlongRoute(geometry, at - back)
  const b = pointAlongRoute(geometry, at)
  const c = pointAlongRoute(geometry, at + fwd)
  if (!a || !b || !c) return null
  if (distanceM(a, b) < MIN_SAMPLE_M || distanceM(b, c) < MIN_SAMPLE_M) return null
  return angleDiffDeg(bearingDeg(a, b), bearingDeg(b, c))
}

/** Prefer the short alley window when it already shows a real turn. */
export function cornerDeltaAt(
  geometry: [number, number][],
  distanceAlongM: number,
): number | null {
  const short = turnDeltaAt(geometry, distanceAlongM, LOOK_SHORT_M)
  const long = turnDeltaAt(geometry, distanceAlongM, LOOK_LONG_M)
  if (short != null && Math.abs(short) >= MIN_TURN_DEG) return short
  if (long != null && Math.abs(long) >= MIN_TURN_DEG) return long
  return short ?? long
}

function instructionFor(turn: TurnDirection, distanceM: number): string {
  const d = Math.round(distanceM)
  if (turn === 'left') return `In ${d} m, turn left`
  if (turn === 'right') return `In ${d} m, turn right`
  if (turn === 'arrive') return 'Arrive at destination'
  return `Continue for ${d} m`
}

function peakHits(
  hits: { distanceM: number; delta: number; turn: TurnDirection; lat: number; lon: number }[],
): typeof hits {
  return hits.filter((hit, i) => {
    const mag = Math.abs(hit.delta)
    for (let j = 0; j < hits.length; j += 1) {
      if (j === i) continue
      const other = hits[j]!
      if (Math.abs(other.distanceM - hit.distanceM) >= PEAK_RADIUS_M) continue
      if (other.turn !== hit.turn) continue
      const otherMag = Math.abs(other.delta)
      if (otherMag > mag) return false
      if (otherMag === mag && j < i) return false
    }
    return true
  })
}

function mergeHits(
  hits: { distanceM: number; delta: number; turn: TurnDirection; lat: number; lon: number }[],
): typeof hits {
  const merged: typeof hits = []
  for (const hit of hits) {
    const last = merged[merged.length - 1]
    if (!last) {
      merged.push(hit)
      continue
    }
    const gap = hit.distanceM - last.distanceM
    const same = hit.turn === last.turn
    if (same && gap < MERGE_SAME_M) {
      if (Math.abs(hit.delta) > Math.abs(last.delta)) merged[merged.length - 1] = hit
      continue
    }
    if (!same && gap < MERGE_OPPOSITE_M) {
      if (Math.abs(hit.delta) > Math.abs(last.delta)) merged[merged.length - 1] = hit
      continue
    }
    merged.push(hit)
  }
  return merged
}

/**
 * Extract coarse maneuvers from a frozen route polyline ([lat, lon][]).
 * Short look-ahead keeps left/right correct on tight hẻm zigzags; a longer
 * window still catches a single wide arterial corner with dense OSM vertices.
 */
export function extractManeuvers(geometry: [number, number][]): Maneuver[] {
  if (geometry.length < 2) return []

  const cum = cumulativeDistances(geometry)
  const routeLen = cum[cum.length - 1] ?? 0
  const hits: { distanceM: number; delta: number; turn: TurnDirection; lat: number; lon: number }[] =
    []

  for (let i = 1; i < geometry.length - 1; i += 1) {
    const at = cum[i]!
    const delta = cornerDeltaAt(geometry, at)
    if (delta == null) continue
    const turn = classifyTurn(delta)
    if (turn === 'straight') continue
    const [lat, lon] = geometry[i]!
    hits.push({ distanceM: at, delta, turn, lat, lon })
  }

  const merged = mergeHits(peakHits(hits))

  const maneuvers: Maneuver[] = merged.map((hit, index) => ({
    id: `m${index}`,
    index,
    distanceFromStartM: hit.distanceM,
    turn: hit.turn,
    instruction: instructionFor(hit.turn, 0),
    lat: hit.lat,
    lon: hit.lon,
  }))

  const last = geometry[geometry.length - 1]!
  maneuvers.push({
    id: `m${maneuvers.length}`,
    index: maneuvers.length,
    distanceFromStartM: routeLen,
    turn: 'arrive',
    instruction: instructionFor('arrive', 0),
    lat: last[0],
    lon: last[1],
  })

  return maneuvers
}

/** Next maneuver ahead of `distanceAlongRouteM`, or null if past end. */
export function nextManeuver(
  maneuvers: Maneuver[],
  distanceAlongRouteM: number,
): Maneuver | null {
  for (const m of maneuvers) {
    if (m.distanceFromStartM >= distanceAlongRouteM - 0.5) return m
  }
  return maneuvers[maneuvers.length - 1] ?? null
}

/** Last left/right already reached along the route. */
export function lastPassedTurn(
  maneuvers: Maneuver[],
  distanceAlongRouteM: number,
): Maneuver | null {
  let last: Maneuver | null = null
  for (const m of maneuvers) {
    if (m.turn !== 'left' && m.turn !== 'right') continue
    if (m.distanceFromStartM <= distanceAlongRouteM + 0.05) last = m
  }
  return last
}

/** Distance remaining to maneuver point along route (m). */
export function distanceToManeuver(
  maneuver: Maneuver,
  distanceAlongRouteM: number,
): number {
  return Math.max(0, maneuver.distanceFromStartM - distanceAlongRouteM)
}
