import { IS_MOBILE_BUILD } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import type { Scenario, TimeWindow, TravelMode } from '../types'
import { destinationsForOrigin, originLabel, uniqueOrigins } from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle, type MobilityChoice } from './ModeToggle'
import { TimeWindowToggle } from './TimeWindowToggle'
import { TravelModeToggle } from './TravelModeToggle'

interface SearchBarProps {
  scenarios: Scenario[]
  originKey: string
  destinationKey: string
  mode: TravelMode
  mobility: MobilityChoice
  timeWindow: TimeWindow
  deltaMinutes: number
  loadingRoutes: boolean
  compact?: boolean
  onOriginChange: (key: string) => void
  onDestinationChange: (key: string) => void
  onModeChange: (mode: TravelMode) => void
  onMobilityChange: (choice: MobilityChoice) => void
  onTimeWindowChange: (value: TimeWindow) => void
  onDeltaChange: (value: number) => void
  onFindRoutes: () => void
}

export function SearchBar({
  scenarios,
  originKey,
  destinationKey,
  mode,
  mobility,
  timeWindow,
  deltaMinutes,
  loadingRoutes,
  compact = false,
  onOriginChange,
  onDestinationChange,
  onModeChange,
  onMobilityChange,
  onTimeWindowChange,
  onDeltaChange,
  onFindRoutes,
}: SearchBarProps) {
  const { t } = useI18n()
  const origins = uniqueOrigins(scenarios)
  const destinations = originKey
    ? destinationsForOrigin(scenarios, originKey)
    : []
  const origin = origins.find((item) => item.key === originKey)
  const selectedScenario = scenarios.find(
    (scenario) =>
      `${scenario.origin.latitude.toFixed(6)},${scenario.origin.longitude.toFixed(6)}` ===
      originKey,
  )

  return (
    <section className={compact ? 'search-bar search-bar--compact' : 'search-bar'}>
      <label className="field" htmlFor="destination-select">
        <span>{t.whereTo}</span>
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

      <label className="field" htmlFor="origin-select">
        <span>{t.from}</span>
        <select
          id="origin-select"
          value={originKey}
          onChange={(event) => onOriginChange(event.target.value)}
        >
          {origins.map((item) => (
            <option key={item.key} value={item.key} title={item.secondary}>
              {item.label}
            </option>
          ))}
        </select>
        {origin && selectedScenario ? (
          <p className="muted small search-bar__here">
            {t.currentLocation}: {originLabel(selectedScenario)}
          </p>
        ) : null}
      </label>

      {compact ? null : (
        <>
          {IS_MOBILE_BUILD ? (
            <ModeToggle
              value={mobility}
              onChange={onMobilityChange}
              disabled={loadingRoutes}
            />
          ) : (
            <>
              <TravelModeToggle
                value={mode}
                onChange={onModeChange}
                disabled={loadingRoutes}
              />
              <TimeWindowToggle
                value={timeWindow}
                onChange={onTimeWindowChange}
                disabled={loadingRoutes}
              />
            </>
          )}

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
        </>
      )}
    </section>
  )
}
