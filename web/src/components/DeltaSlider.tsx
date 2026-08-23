import { COLORS, DELTA_MINUTES } from '../constants'

interface DeltaSliderProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

export function DeltaSlider({ value, onChange, disabled }: DeltaSliderProps) {
  const index = Math.max(0, DELTA_MINUTES.indexOf(value as (typeof DELTA_MINUTES)[number]))
  const safeIndex = index === -1 ? 0 : index

  return (
    <div className="delta-slider">
      <div className="delta-slider__header">
        <label htmlFor="delta-minutes-slider">
          How much extra time are you willing to spend?
        </label>
        <p className="delta-slider__value" aria-live="polite">
          +{DELTA_MINUTES[safeIndex]} min
        </p>
      </div>
      <input
        id="delta-minutes-slider"
        type="range"
        min={0}
        max={DELTA_MINUTES.length - 1}
        step={1}
        value={safeIndex}
        disabled={disabled}
        aria-valuetext={`Allow up to +${DELTA_MINUTES[safeIndex]} minutes`}
        onChange={(event) => {
          const next = DELTA_MINUTES[Number(event.target.value)] ?? 0
          onChange(next)
        }}
      />
      <div className="delta-slider__ticks" aria-hidden="true">
        {DELTA_MINUTES.map((minute) => (
          <span key={minute} style={{ color: minute === value ? COLORS.navy : undefined }}>
            {minute}
          </span>
        ))}
      </div>
      <p className="muted small">
        Allow up to +{DELTA_MINUTES[safeIndex]} min longer than the fastest route.
      </p>
    </div>
  )
}
