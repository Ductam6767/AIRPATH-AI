import {
  angleDiffDeg,
  bearingDeg,
  cumulativeDistances,
  distanceM,
  pointAlongRoute,
} from './geo'
import type { Maneuver, TurnDirection } from './types'

/** Heading change sampled over this inbound/outbound window. */
const LOOK_M = 50
const MIN_SAMPLE_M = 14
const MIN_TURN_DEG = 32
const MERGE_M = 55

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
  lookM: number = LOOK_M,
): number | null {
  const cum = cumulativeDistances(geometry)
  const routeLen = cum[cum.length - 1] ?? 0
  if (routeLen < lookM) return null
  const at = Math.min(Math.max(distanceAlongM, 0), routeLen)
  const a = pointAlongRoute(geometry, Math.max(0, at - lookM))
  const b = pointAlongRoute(geometry, at)
  const c = pointAlongRoute(geometry, Math.min(routeLen, at + lookM))
  if (!a || !b || !c) return null
  if (distanceM(a, b) < MIN_SAMPLE_M || distanceM(b, c) < MIN_SAMPLE_M) return null
  return angleDiffDeg(bearingDeg(a, b), bearingDeg(b, c))
}

function instructionFor(turn: TurnDirection, distanceM: number): string {
  const d = Math.round(distanceM)
  if (turn === 'left') return `In ${d} m, turn left`
  if (turn === 'right') return `In ${d} m, turn right`
  if (turn === 'arrive') return 'Arrive at destination'
  return `Continue for ${d} m`
}

/**
 * Extract coarse maneuvers from a frozen route polyline ([lat, lon][]).
 * Incoming/outgoing headings use a 50 m window so dense OSM vertices do not
 * skip the corner the rider actually sees, or pick the following opposite turn.
 */
export function extractManeuvers(geometry: [number, number][]): Maneuver[] {
  if (geometry.length < 2) return []

  const cum = cumulativeDistances(geometry)
  const routeLen = cum[cum.length - 1] ?? 0
  const hits: { distanceM: number; delta: number; turn: TurnDirection; lat: number; lon: number }[] =
    []

  for (let i = 1; i < geometry.length - 1; i += 1) {
    const at = cum[i]!
    const delta = turnDeltaAt(geometry, at)
    if (delta == null) continue
    const turn = classifyTurn(delta)
    if (turn === 'straight') continue
    const [lat, lon] = geometry[i]!
    hits.push({ distanceM: at, delta, turn, lat, lon })
  }

  const merged: typeof hits = []
  for (const hit of hits) {
    const last = merged[merged.length - 1]
    if (last && Math.abs(hit.distanceM - last.distanceM) < MERGE_M) {
      if (Math.abs(hit.delta) > Math.abs(last.delta)) merged[merged.length - 1] = hit
    } else {
      merged.push(hit)
    }
  }

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

/** Distance remaining to maneuver point along route (m). */
export function distanceToManeuver(
  maneuver: Maneuver,
  distanceAlongRouteM: number,
): number {
  return Math.max(0, maneuver.distanceFromStartM - distanceAlongRouteM)
}
