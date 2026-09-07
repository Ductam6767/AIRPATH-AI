import { useI18n } from '../i18n/LanguageContext'
import type { Scenario } from '../types'
import type { MobilityChoice } from './ModeToggle'
import { destinationsForOrigin, uniqueOrigins } from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle } from './ModeToggle'

interface SidebarProps {
  scenarios: Scenario[]
  originKey: string
  destinationKey: string
  mobility: MobilityChoice
  deltaMinutes: number
  loadingRoutes: boolean
  onOriginChange: (key: string) => void
  onDestinationChange: (key: string) => void
  onMobilityChange: (choice: MobilityChoice) => void
  onDeltaChange: (value: number) => void
  onFindRoutes: () => void
  onOpenMethodology: () => void
}

export function Sidebar({
  scenarios,
  originKey,
  destinationKey,
  mobility,
  deltaMinutes,
  loadingRoutes,
  onOriginChange,
  onDestinationChange,
  onMobilityChange,
  onDeltaChange,
  onFindRoutes,
  onOpenMethodology,
}: SidebarProps) {
  const { t, lang, setLang } = useI18n()
  const origins = uniqueOrigins(scenarios)
  const destinations = originKey
    ? destinationsForOrigin(scenarios, originKey)
    : []

  return (
    <aside className="sidebar" aria-label="Trip controls">
      <div className="brand-block">
        <div className="brand-row">
          <p className="brand">AIRPATH-AI</p>
          <div className="lang-toggle" role="group" aria-label="Language">
            <button
              type="button"
              className={lang === 'en' ? 'lang-btn is-active' : 'lang-btn'}
              onClick={() => setLang('en')}
            >
              {t.langEn}
            </button>
            <button
              type="button"
              className={lang === 'vi' ? 'lang-btn is-active' : 'lang-btn'}
              onClick={() => setLang('vi')}
            >
              {t.langVi}
            </button>
          </div>
        </div>
        <h1 className="hero-line">{t.hero}</h1>
        <p className="muted">{t.heroSub}</p>
        <p className="pilot-chip">{t.chip}</p>
      </div>

      <div className="control-stack">
        <label className="field" htmlFor="origin-select">
          <span>{t.from}</span>
          <select
            id="origin-select"
            value={originKey}
            onChange={(event) => onOriginChange(event.target.value)}
          >
            {origins.map((origin) => (
              <option key={origin.key} value={origin.key} title={origin.secondary}>
                {origin.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field" htmlFor="destination-select">
          <span>{t.to}</span>
          <select
            id="destination-select"
            value={destinationKey}
            onChange={(event) => onDestinationChange(event.target.value)}
            disabled={destinations.length === 0}
          >
            {destinations.map((destination) => (
              <option
                key={destination.key}
                value={destination.key}
                title={destination.secondary}
              >
                {destination.label}
              </option>
            ))}
          </select>
        </label>

        <ModeToggle
          value={mobility}
          onChange={onMobilityChange}
          disabled={loadingRoutes}
        />

        <DeltaSlider
          value={deltaMinutes}
          onChange={onDeltaChange}
          disabled={loadingRoutes}
        />

        <button
          type="button"
          className="primary-btn"
          onClick={onFindRoutes}
          disabled={loadingRoutes || !originKey || !destinationKey}
        >
          {loadingRoutes ? t.comparing : t.compare}
        </button>

        <button type="button" className="linkish" onClick={onOpenMethodology}>
          {t.howItWorks}
        </button>
      </div>

      <p className="sidebar-footnote muted small">{t.footnote}</p>
    </aside>
  )
}
