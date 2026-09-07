import type { TravelMode } from '../types'
import { useI18n } from '../i18n/LanguageContext'

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
  const { t } = useI18n()
  return (
    <fieldset className="mode-toggle" disabled={disabled}>
      <legend>{t.mobility}</legend>
      <div className="mode-toggle__grid" role="radiogroup" aria-label={t.mobility}>
        <button
          type="button"
          className={value === 'walking' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'walking'}
          onClick={() => onChange('walking')}
        >
          {t.walking}
        </button>
        <button
          type="button"
          className={value === 'cycling' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'cycling'}
          onClick={() => onChange('cycling')}
        >
          {t.cycling}
        </button>
        <button
          type="button"
          className={value === 'ebike' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'ebike'}
          onClick={() => onChange('ebike')}
        >
          {t.ebike}
        </button>
      </div>
      <p className="small muted mode-footnote">{t.modeFootnote}</p>
    </fieldset>
  )
}
