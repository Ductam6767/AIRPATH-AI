import { describe, expect, it } from 'vitest'
import {
  armedTurnDirection,
  assistPayloadTurn,
  isCornerConfirm,
  signalState,
  TURN_SIGNAL_ARM_M,
} from '../maneuver/turnSignal'

describe('turn signal arming', () => {
  it('stays off until the next left/right is within 62.5 m', () => {
    expect(armedTurnDirection('left', 62.6)).toBeNull()
    expect(armedTurnDirection('right', TURN_SIGNAL_ARM_M)).toBe('right')
    expect(armedTurnDirection('left', 40)).toBe('left')
    expect(armedTurnDirection('straight', 20)).toBeNull()
    expect(armedTurnDirection('arrive', 5)).toBeNull()
  })

  it('only sends left/right on the assist payload inside 62.5 m', () => {
    expect(assistPayloadTurn('left', 250)).toBe('straight')
    expect(assistPayloadTurn('right', 62.5)).toBe('right')
    expect(assistPayloadTurn('arrive', 10)).toBe('straight')
  })

  it('keeps the signal on for 5 m after the corner, then turns it off', () => {
    expect(armedTurnDirection('right', 40, 'left', 2)).toBe('left')
    expect(armedTurnDirection('right', 200, 'left', 5)).toBe('left')
    expect(armedTurnDirection('right', 200, 'left', 5.1)).toBeNull()
    expect(assistPayloadTurn('right', 200, 'left', 3)).toBe('left')
    expect(assistPayloadTurn('right', 200, 'left', 6)).toBe('straight')
  })

  it('marks the UI ready, off, armed, then active', () => {
    expect(
      signalState({ active: false, next: null, distanceToNextM: 0 }),
    ).toBe('ready')
    expect(
      signalState({
        active: true,
        next: { turn: 'left' },
        distanceToNextM: 180,
      }),
    ).toBe('off')
    expect(
      signalState({
        active: true,
        next: { turn: 'left' },
        distanceToNextM: 50,
      }),
    ).toBe('left')
    expect(
      signalState({
        active: true,
        next: { turn: 'right' },
        distanceToNextM: 25,
      }),
    ).toBe('active')
  })

  it('flashes the pale-blue confirm LED from 6 m, not while only the blinker is on', () => {
    expect(isCornerConfirm('right', 20)).toBe(false)
    expect(isCornerConfirm('right', 6)).toBe(true)
    expect(isCornerConfirm('left', 5)).toBe(true)
    expect(isCornerConfirm('right', 0)).toBe(true)
    expect(isCornerConfirm('straight', 4)).toBe(false)
    expect(isCornerConfirm('right', 200, 'left', 1)).toBe(true)
    expect(isCornerConfirm('right', 200, 'left', 2)).toBe(false)
  })
})
