import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BlinkerArrow } from '../components/BlinkerArrow'
import { NavigationInstruction } from '../components/NavigationInstruction'
import type { AssistSnapshot } from '../hooks/useAssistNavigation'
import type { Maneuver } from '../maneuver/types'
import { mockRoutesWithAlts } from './fixtures'

function snapshot(next: Maneuver | null, distanceToNextM = 80): AssistSnapshot {
  return {
    active: true,
    mode: 'demo',
    distanceAlongM: 40,
    routeLengthM: 3500,
    next,
    distanceToNextM,
    speedTargetKmh: 18,
    speedSteps: [18, 12],
    payload: null,
  }
}

const leftTurn: Maneuver = {
  id: 'm-left',
  index: 1,
  distanceFromStartM: 120,
  turn: 'left',
  instruction: 'Turn left',
  lat: 10.8,
  lon: 106.67,
}

describe('BlinkerArrow', () => {
  it('renders a red left/right blinker and stays hidden for straight or arrive', () => {
    const { rerender } = render(<BlinkerArrow turn="left" />)
    expect(screen.getByTestId('blinker-left')).toBeInTheDocument()
    rerender(<BlinkerArrow turn="right" />)
    expect(screen.getByTestId('blinker-right')).toBeInTheDocument()
    rerender(<BlinkerArrow turn="straight" />)
    expect(screen.queryByTestId('blinker-left')).not.toBeInTheDocument()
    expect(screen.queryByTestId('blinker-right')).not.toBeInTheDocument()
    rerender(<BlinkerArrow turn="arrive" />)
    expect(screen.queryByTestId('blinker-left')).not.toBeInTheDocument()
  })
})

describe('NavigationInstruction blinker', () => {
  it('shows a blinking left arrow only when the turn is within 62.5 m', () => {
    const { rerender } = render(
      <NavigationInstruction
        route={mockRoutesWithAlts.alternatives[0]!}
        snapshot={snapshot(leftTurn, 80)}
      />,
    )
    expect(screen.queryByTestId('blinker-left')).not.toBeInTheDocument()
    expect(screen.getByText('Left')).toBeInTheDocument()
    expect(screen.getByText('in 80 m')).toBeInTheDocument()

    rerender(
      <NavigationInstruction
        route={mockRoutesWithAlts.alternatives[0]!}
        snapshot={snapshot(leftTurn, 50)}
      />,
    )
    expect(screen.getByTestId('blinker-left')).toBeInTheDocument()
    expect(screen.getByText('in 50 m')).toBeInTheDocument()
  })
})
