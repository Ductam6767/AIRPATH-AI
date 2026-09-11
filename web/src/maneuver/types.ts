/** Turn-by-turn maneuver derived from frozen route polyline (demo navigation). */

export type TurnDirection = 'left' | 'right' | 'straight' | 'arrive'

export interface Maneuver {
  id: string
  index: number
  /** Meters from route start to this maneuver point. */
  distanceFromStartM: number
  turn: TurnDirection
  /** Human label for UI / BLE. */
  instruction: string
  lat: number
  lon: number
}

export interface AssistPayload {
  turn: TurnDirection
  distance_m: number
  speed_target_kmh: number
  maneuver_index: number
  instruction: string
  ts: number
  /** Pale-blue LED: this is the turn, not an alley before it. */
  corner_confirm?: boolean
}
