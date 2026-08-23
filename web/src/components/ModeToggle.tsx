import type { TravelMode } from '../types'

interface ModeToggleProps {
  value: TravelMode
  onChange: (mode: TravelMode) => void
  disabled?: boolean
}

export function ModeToggle({ value, onChange, disabled }: ModeToggleProps) {
  return (
    <fieldset className="mode-toggle" disabled={disabled}>
      <legend>Travel mode</legend>
      <div className="mode-toggle__row" role="group" aria-label="Travel mode">
        <button
          type="button"
          className={value === 'walking' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'walking'}
          onClick={() => onChange('walking')}
        >
          Walking
        </button>
        <button
          type="button"
          className={value === 'motorbike' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'motorbike'}
          onClick={() => onChange('motorbike')}
        >
          Motorbike
        </button>
      </div>
    </fieldset>
  )
}
