import type { TravelMode } from '../types'
import { useI18n } from '../i18n/LanguageContext'

interface TravelModeToggleProps {
  value: TravelMode
  onChange: (mode: TravelMode) => void
  disabled?: boolean
}

export function TravelModeToggle({
  value,
  onChange,
  disabled,
}: TravelModeToggleProps) {
  const { t } = useI18n()
  return (
    <fieldset className="mode-toggle" disabled={disabled}>
      <legend>{t.travelMode}</legend>
      <div className="mode-toggle__row" role="radiogroup" aria-label={t.travelMode}>
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
          className={value === 'motorbike' ? 'mode-btn is-active' : 'mode-btn'}
          aria-pressed={value === 'motorbike'}
          onClick={() => onChange('motorbike')}
        >
          {t.motorbike}
        </button>
      </div>
    </fieldset>
  )
}
