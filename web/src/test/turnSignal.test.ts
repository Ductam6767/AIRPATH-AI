import { describe, expect, it } from 'vitest'
import {
  armedTurnDirection,
  assistPayloadTurn,
  signalState,
  TURN_SIGNAL_ARM_M,
} from '../maneuver/turnSignal'

describe('turn signal arming', () => {
  it('stays off until the next left/right is within 100 m', () => {
    expect(armedTurnDirection('left', 101)).toBeNull()
    expect(armedTurnDirection('right', TURN_SIGNAL_ARM_M)).toBe('right')
    expect(armedTurnDirection('left', 40)).toBe('left')
    expect(armedTurnDirection('straight', 20)).toBeNull()
    expect(armedTurnDirection('arrive', 5)).toBeNull()
  })

  it('only sends left/right on the assist payload inside 100 m', () => {
    expect(assistPayloadTurn('left', 250)).toBe('straight')
    expect(assistPayloadTurn('right', 100)).toBe('right')
    expect(assistPayloadTurn('arrive', 10)).toBe('straight')
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
        distanceToNextM: 80,
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
})
