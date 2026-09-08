import { TIME_WINDOWS } from '../constants'
import type { TimeWindow } from '../types'
import { useI18n } from '../i18n/LanguageContext'

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
  const { t } = useI18n()
  return (
    <fieldset className="mode-toggle" disabled={disabled}>
      <legend>{t.timeWindowLegend}</legend>
      <div className="mode-toggle__row" role="radiogroup" aria-label={t.timeWindowLegend}>
        {TIME_WINDOWS.map((window) => (
          <button
            key={window.id}
            type="button"
            className={value === window.id ? 'mode-btn is-active' : 'mode-btn'}
            aria-pressed={value === window.id}
            onClick={() => onChange(window.id)}
          >
            {t.timeWindowLabel(window.id)}
          </button>
        ))}
      </div>
      <p className="muted small">{t.timeWindowHelp}</p>
    </fieldset>
  )
}
