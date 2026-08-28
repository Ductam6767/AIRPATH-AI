import type { TimeWindow } from '../types'
import { TIME_WINDOWS } from '../constants'

interface TimeWindowToggleProps {
  value: TimeWindow
  onChange: (value: TimeWindow) => void
  disabled?: boolean
}

export function TimeWindowToggle({
  value,
  onChange,
  disabled,
}: TimeWindowToggleProps) {
  return (
    <fieldset className="mode-toggle" disabled={disabled}>
      <legend>Time of day (demo congestion proxy)</legend>
      <div className="mode-toggle__row" role="radiogroup" aria-label="Time of day">
        {TIME_WINDOWS.map((window) => (
          <button
            key={window.id}
            type="button"
            className={value === window.id ? 'mode-btn is-active' : 'mode-btn'}
            aria-pressed={value === window.id}
            onClick={() => onChange(window.id)}
          >
            {window.label}
          </button>
        ))}
      </div>
      <p className="muted small">
        Changes the arterial traffic multiplier only. Station background stays the
        06:00 field. Not a measurement of which street is jammed.
      </p>
    </fieldset>
  )
}
