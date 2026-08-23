import { DELTA_MINUTES } from '../constants'

interface DeltaSliderProps {
  value: number
  onChange: (value: number) => void
  disabled?: boolean
}

export function DeltaSlider({ value, onChange, disabled }: DeltaSliderProps) {
  const index = DELTA_MINUTES.indexOf(value as (typeof DELTA_MINUTES)[number])
  const safeIndex = index === -1 ? 0 : index
  const selected = DELTA_MINUTES[safeIndex]

  return (
    <div className="delta-slider">
      <div className="delta-slider__header">
        <label htmlFor="delta-minutes-slider">Maximum additional time</label>
        <p className="delta-slider__value" aria-live="polite">
          Allow up to +{selected} min
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
        aria-valuemin={0}
        aria-valuemax={10}
        aria-valuenow={selected}
        aria-valuetext={`Allow up to +${selected} minutes`}
        onChange={(event) => {
          const next = DELTA_MINUTES[Number(event.target.value)] ?? 0
          onChange(next)
        }}
      />
      <div className="delta-slider__ticks">
        {DELTA_MINUTES.map((minute, tickIndex) => (
          <button
            key={minute}
            type="button"
            className={
              minute === selected
                ? 'delta-slider__tick is-active'
                : 'delta-slider__tick'
            }
            disabled={disabled}
            onClick={() => onChange(minute)}
            aria-label={`Allow up to +${minute} minutes`}
            aria-pressed={minute === selected}
            tabIndex={tickIndex === safeIndex ? 0 : -1}
          >
            {minute}
          </button>
        ))}
      </div>
      <p className="muted small">
        Allows routes up to {selected} minutes longer than the fastest route.
      </p>
    </div>
  )
}
