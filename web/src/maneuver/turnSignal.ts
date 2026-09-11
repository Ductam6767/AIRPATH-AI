import type { TurnDirection } from './types'

/** Arm the turn signal only when the next left/right is this close. */
export const TURN_SIGNAL_ARM_M = 62.5

/** Keep the completed turn’s signal on until the rider has gone this far past it. */
export const TURN_SIGNAL_HOLD_AFTER_M = 5

/** Still “active” in the last metres before the corner. */
export const TURN_SIGNAL_CLOSE_M = 40

export function armedTurnDirection(
  turn: TurnDirection | null | undefined,
  distanceToNextM: number,
  lastTurn: TurnDirection | null | undefined = null,
  distancePastLastTurnM: number | undefined = Number.POSITIVE_INFINITY,
): 'left' | 'right' | null {
  if (
    (lastTurn === 'left' || lastTurn === 'right') &&
    Number.isFinite(distancePastLastTurnM) &&
    distancePastLastTurnM >= 0 &&
    distancePastLastTurnM <= TURN_SIGNAL_HOLD_AFTER_M
  ) {
    return lastTurn
  }
  if (turn !== 'left' && turn !== 'right') return null
  if (!Number.isFinite(distanceToNextM) || distanceToNextM > TURN_SIGNAL_ARM_M) {
    return null
  }
  return turn
}

export function assistPayloadTurn(
  turn: TurnDirection,
  distanceToNextM: number,
  lastTurn: TurnDirection | null | undefined = null,
  distancePastLastTurnM: number | undefined = Number.POSITIVE_INFINITY,
): TurnDirection {
  return (
    armedTurnDirection(turn, distanceToNextM, lastTurn, distancePastLastTurnM) ??
    'straight'
  )
}

export function signalState(snapshot: {
  active: boolean
  next: { turn: TurnDirection } | null
  distanceToNextM: number
  lastTurn?: { turn: TurnDirection } | null
  distancePastLastTurnM?: number
}): 'ready' | 'left' | 'right' | 'active' | 'off' {
  if (!snapshot.active || !snapshot.next) return 'ready'
  const armed = armedTurnDirection(
    snapshot.next.turn,
    snapshot.distanceToNextM,
    snapshot.lastTurn?.turn,
    snapshot.distancePastLastTurnM,
  )
  if (!armed) return 'off'
  if (
    snapshot.distancePastLastTurnM != null &&
    snapshot.distancePastLastTurnM >= 0 &&
    snapshot.distancePastLastTurnM <= TURN_SIGNAL_HOLD_AFTER_M &&
    (snapshot.lastTurn?.turn === 'left' || snapshot.lastTurn?.turn === 'right')
  ) {
    return armed
  }
  if (snapshot.distanceToNextM <= TURN_SIGNAL_CLOSE_M) return 'active'
  return armed
}
