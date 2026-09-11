import type { TurnDirection } from './types'

/** Arm the turn signal only when the next left/right is this close. */
export const TURN_SIGNAL_ARM_M = 100

/** Still “active” in the last metres before the corner. */
export const TURN_SIGNAL_CLOSE_M = 40

export function armedTurnDirection(
  turn: TurnDirection | null | undefined,
  distanceToNextM: number,
): 'left' | 'right' | null {
  if (turn !== 'left' && turn !== 'right') return null
  if (!Number.isFinite(distanceToNextM) || distanceToNextM > TURN_SIGNAL_ARM_M) {
    return null
  }
  return turn
}

export function assistPayloadTurn(
  turn: TurnDirection,
  distanceToNextM: number,
): TurnDirection {
  return armedTurnDirection(turn, distanceToNextM) ?? 'straight'
}

export function signalState(snapshot: {
  active: boolean
  next: { turn: TurnDirection } | null
  distanceToNextM: number
}): 'ready' | 'left' | 'right' | 'active' | 'off' {
  if (!snapshot.active || !snapshot.next) return 'ready'
  const armed = armedTurnDirection(snapshot.next.turn, snapshot.distanceToNextM)
  if (!armed) return 'off'
  if (snapshot.distanceToNextM <= TURN_SIGNAL_CLOSE_M) return 'active'
  return armed
}
