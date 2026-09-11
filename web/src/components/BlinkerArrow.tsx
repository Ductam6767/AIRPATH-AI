import type { TurnDirection } from '../maneuver/types'

interface BlinkerArrowProps {
  turn: TurnDirection | null | undefined
  size?: 'md' | 'lg'
}

export function BlinkerArrow({ turn, size = 'lg' }: BlinkerArrowProps) {
  if (turn !== 'left' && turn !== 'right') return null
  return (
    <span
      className={`blinker-arrow blinker-arrow--${turn} blinker-arrow--${size}`}
      data-testid={`blinker-${turn}`}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" focusable="false">
        {turn === 'left' ? (
          <polygon points="19,3 5,12 19,21 19,15.5 13,12 19,8.5" />
        ) : (
          <polygon points="5,3 19,12 5,21 5,15.5 11,12 5,8.5" />
        )}
      </svg>
    </span>
  )
}
