import type { TravelMode } from '../types'

/** UI mobility labels map to frozen API modes (walking | motorbike). */
export type MobilityChoice = 'walking' | 'cycling' | 'ebike'

export function mobilityToApiMode(choice: MobilityChoice): TravelMode {
  return choice === 'ebike' ? 'motorbike' : 'walking'
}

export function apiModeToMobility(mode: TravelMode): MobilityChoice {
  return mode === 'motorbike' ? 'ebike' : 'walking'
}

interface ModeToggleProps {
  value: MobilityChoice
  onChange: (choice: MobilityChoice) => void
  disabled?: boolean
}

export function ModeToggle({ value, onChange, disabled }: ModeToggleProps) {
  return (
    <fieldset className="mode-toggle" disabled={disabled}>
      <legend>Mobility (pilot)</legend>
      <div className="mode-toggle__grid" role="radiogroup" aria-label="Mobility mode">
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
          className={value === 'cycling' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'cycling'}
          onClick={() => onChange('cycling')}
        >
          Cycling
        </button>
        <button
          type="button"
          className={value === 'ebike' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'ebike'}
          onClick={() => onChange('ebike')}
        >
          E-bike
        </button>
      </div>
      <p className="small muted mode-footnote">
        Cycling uses walking-speed routes in this demo pack; e-bike uses motorbike
        ETAs.
      </p>
    </fieldset>
  )
}
