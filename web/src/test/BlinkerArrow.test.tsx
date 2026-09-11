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
    lastTurn: null,
    distancePastLastTurnM: Number.POSITIVE_INFINITY,
    cornerConfirm: false,
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

  it('draws the enlarged junction diagram in the nav sheet', () => {
    render(
      <NavigationInstruction
        route={mockRoutesWithAlts.alternatives[0]!}
        snapshot={snapshot(leftTurn, 50)}
        hudCue={{
          id: 'rb',
          kind: 'roundabout',
          lat: 10.8,
          lng: 106.67,
          atM: 90,
          exit: 2,
          arms: 4,
          arm_deg: [0, 90, 180, 270],
        }}
      />,
    )
    expect(screen.getByLabelText('Junction diagram')).toBeInTheDocument()
    expect(screen.getByText(/Roundabout · take exit 2/)).toBeInTheDocument()
    expect(screen.getByText('Orange = the road to take')).toBeInTheDocument()
    expect(screen.getByText('in 50 m')).toBeInTheDocument()
  })

  it('flashes the pale-blue confirm LED only in the last 6 m', () => {
    const { rerender } = render(
      <NavigationInstruction
        route={mockRoutesWithAlts.alternatives[0]!}
        snapshot={{ ...snapshot(leftTurn, 20), cornerConfirm: false }}
      />,
    )
    expect(screen.queryByTestId('confirm-led')).not.toBeInTheDocument()
    rerender(
      <NavigationInstruction
        route={mockRoutesWithAlts.alternatives[0]!}
        snapshot={{ ...snapshot(leftTurn, 5), cornerConfirm: true }}
      />,
    )
    expect(screen.getByTestId('confirm-led')).toBeInTheDocument()
    expect(screen.getByText(/This junction — turn now/)).toBeInTheDocument()
  })
})
