interface ConfirmLedProps {
  on: boolean
  size?: 'md' | 'lg'
}

/** Pale-blue flash: this is the turn, not a hẻm the rider passed first. */
export function ConfirmLed({ on, size = 'lg' }: ConfirmLedProps) {
  if (!on) return null
  return (
    <span
      className={`confirm-led confirm-led--${size}`}
      data-testid="confirm-led"
      aria-hidden="true"
    />
  )
}
