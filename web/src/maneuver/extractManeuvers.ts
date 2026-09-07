import { angleDiffDeg, bearingDeg, cumulativeDistances } from './geo'
import type { Maneuver, TurnDirection } from './types'

const MIN_TURN_DEG = 28
const MIN_LEG_M = 25

function classifyTurn(delta: number): TurnDirection {
  if (delta > MIN_TURN_DEG) return 'right'
  if (delta < -MIN_TURN_DEG) return 'left'
  return 'straight'
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
 * Used for demo navigation + ESP32 sync — not OSM turn-by-turn.
 */
export function extractManeuvers(geometry: [number, number][]): Maneuver[] {
  if (geometry.length < 2) return []

  const cum = cumulativeDistances(geometry)
  const maneuvers: Maneuver[] = []
  let maneuverIndex = 0

  for (let i = 1; i < geometry.length - 1; i += 1) {
    const prev = geometry[i - 1]!
    const curr = geometry[i]!
    const next = geometry[i + 1]!
    const legIn = cum[i]! - cum[i - 1]!
    const legOut = cum[i + 1]! - cum[i]!
    if (legIn < MIN_LEG_M || legOut < MIN_LEG_M) continue

    const bIn = bearingDeg(prev, curr)
    const bOut = bearingDeg(curr, next)
    const delta = angleDiffDeg(bIn, bOut)
    const turn = classifyTurn(delta)
    if (turn === 'straight') continue

    const [lat, lon] = curr
    maneuvers.push({
      id: `m${maneuverIndex}`,
      index: maneuverIndex,
      distanceFromStartM: cum[i]!,
      turn,
      instruction: instructionFor(turn, 0),
      lat,
      lon,
    })
    maneuverIndex += 1
  }

  const last = geometry[geometry.length - 1]!
  maneuvers.push({
    id: `m${maneuverIndex}`,
    index: maneuverIndex,
    distanceFromStartM: cum[cum.length - 1]!,
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
