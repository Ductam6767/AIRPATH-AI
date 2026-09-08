import { IS_MOBILE_BUILD } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import type { Scenario, TimeWindow, TravelMode } from '../types'
import { destinationsForOrigin, uniqueOrigins } from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle, type MobilityChoice } from './ModeToggle'
import { TimeWindowToggle } from './TimeWindowToggle'
import { TravelModeToggle } from './TravelModeToggle'

interface SidebarProps {
  scenarios: Scenario[]
  originKey: string
  destinationKey: string
  mode: TravelMode
  mobility: MobilityChoice
  timeWindow: TimeWindow
  deltaMinutes: number
  loadingRoutes: boolean
  onOriginChange: (key: string) => void
  onDestinationChange: (key: string) => void
  onModeChange: (mode: TravelMode) => void
  onMobilityChange: (choice: MobilityChoice) => void
  onTimeWindowChange: (value: TimeWindow) => void
  onDeltaChange: (value: number) => void
  onFindRoutes: () => void
  onOpenMethodology: () => void
  onOpenGap1?: () => void
}

export function Sidebar({
  scenarios,
  originKey,
  destinationKey,
  mode,
  mobility,
  timeWindow,
  deltaMinutes,
  loadingRoutes,
  onOriginChange,
  onDestinationChange,
  onModeChange,
  onMobilityChange,
  onTimeWindowChange,
  onDeltaChange,
  onFindRoutes,
  onOpenMethodology,
  onOpenGap1,
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
          {IS_MOBILE_BUILD ? (
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
          ) : null}
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

        {IS_MOBILE_BUILD ? (
          <ModeToggle
            value={mobility}
            onChange={onMobilityChange}
            disabled={loadingRoutes}
          />
        ) : (
          <TravelModeToggle
            value={mode}
            onChange={onModeChange}
            disabled={loadingRoutes}
          />
        )}

        {!IS_MOBILE_BUILD ? (
          <TimeWindowToggle
            value={timeWindow}
            onChange={onTimeWindowChange}
            disabled={loadingRoutes}
          />
        ) : null}

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

        {!IS_MOBILE_BUILD && onOpenGap1 ? (
          <button type="button" className="linkish" onClick={onOpenGap1}>
            {t.gap1Link}
          </button>
        ) : null}
      </div>

      <p className="sidebar-footnote muted small">{t.footnote}</p>
    </aside>
  )
}
