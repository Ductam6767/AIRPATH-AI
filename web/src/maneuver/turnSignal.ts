import type { TurnDirection } from './types'

/** Arm the turn signal only when the next left/right is this close. */
export const TURN_SIGNAL_ARM_M = 62.5

/**
 * Keep this corner’s blinker on with the confirm LED, then go dark.
 * Next blinker may not arm until after TURN_SIGNAL_QUIET_AFTER_M.
 */
export const TURN_SIGNAL_HOLD_AFTER_M = 1.5

/** Still “active” in the last metres before the corner. */
export const TURN_SIGNAL_CLOSE_M = 40

/**
 * Second confirmation at the real corner (not an alley the rider passes first).
 * Xi-nhan already means “slow down, a turn is coming”; this pale-blue LED
 * means “turn here”.
 */
export const TURN_CONFIRM_M = 6
export const TURN_CONFIRM_HOLD_AFTER_M = 1.5

/** After the confirm LED goes off, stay dark before the next blinker. */
export const TURN_SIGNAL_QUIET_AFTER_M = 4

function hasPassedTurn(
  lastTurn: TurnDirection | null | undefined,
  distancePastLastTurnM: number | undefined,
): boolean {
  return (
    (lastTurn === 'left' || lastTurn === 'right') &&
    Number.isFinite(distancePastLastTurnM) &&
    (distancePastLastTurnM as number) >= 0
  )
}

export function isAfterTurnQuiet(
  lastTurn: TurnDirection | null | undefined,
  distancePastLastTurnM: number | undefined,
): boolean {
  if (!hasPassedTurn(lastTurn, distancePastLastTurnM)) return false
  const past = distancePastLastTurnM as number
  return (
    past > TURN_CONFIRM_HOLD_AFTER_M &&
    past <= TURN_CONFIRM_HOLD_AFTER_M + TURN_SIGNAL_QUIET_AFTER_M
  )
}

export function armedTurnDirection(
  turn: TurnDirection | null | undefined,
  distanceToNextM: number,
  lastTurn: TurnDirection | null | undefined = null,
  distancePastLastTurnM: number | undefined = Number.POSITIVE_INFINITY,
): 'left' | 'right' | null {
  if (hasPassedTurn(lastTurn, distancePastLastTurnM)) {
    const past = distancePastLastTurnM as number
    if (past <= TURN_SIGNAL_HOLD_AFTER_M) return lastTurn as 'left' | 'right'
    if (isAfterTurnQuiet(lastTurn, past)) return null
  }
  if (turn !== 'left' && turn !== 'right') return null
  if (!Number.isFinite(distanceToNextM) || distanceToNextM > TURN_SIGNAL_ARM_M) {
    return null
  }
  return turn
}

/** Pale-blue LED: this exact junction, 6 m out — skip the hẻm before it. */
export function isCornerConfirm(
  turn: TurnDirection | null | undefined,
  distanceToNextM: number,
  lastTurn: TurnDirection | null | undefined = null,
  distancePastLastTurnM: number | undefined = Number.POSITIVE_INFINITY,
): boolean {
  if (hasPassedTurn(lastTurn, distancePastLastTurnM)) {
    const past = distancePastLastTurnM as number
    if (past <= TURN_CONFIRM_HOLD_AFTER_M) return true
    if (isAfterTurnQuiet(lastTurn, past)) return false
  }
  if (turn !== 'left' && turn !== 'right') return false
  if (!Number.isFinite(distanceToNextM)) return false
  return distanceToNextM <= TURN_CONFIRM_M && distanceToNextM >= 0
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
