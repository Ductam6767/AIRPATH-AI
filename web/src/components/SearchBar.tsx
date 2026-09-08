import { IS_MOBILE_BUILD } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import type { Scenario, TimeWindow, TravelMode } from '../types'
import { uniquePlaces } from '../utils/labels'
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
  onSwapEnds: () => void
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
  onSwapEnds,
  onModeChange,
  onMobilityChange,
  onTimeWindowChange,
  onDeltaChange,
  onFindRoutes,
}: SearchBarProps) {
  const { t } = useI18n()
  const places = uniquePlaces(scenarios)
  const fromPlaces = places.filter((place) => place.key !== destinationKey)
  const toPlaces = places.filter((place) => place.key !== originKey)

  return (
    <section className={compact ? 'search-bar search-bar--compact' : 'search-bar'}>
      <div className="search-bar__ends">
        <label className="field" htmlFor="origin-select">
          <span>{t.from}</span>
          <select
            id="origin-select"
            name="origin"
            value={originKey}
            onChange={(event) => onOriginChange(event.target.value)}
            aria-label={t.from}
          >
            <option value="">{t.chooseOrigin}</option>
            {fromPlaces.map((item) => (
              <option key={item.key} value={item.key} title={item.secondary}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <div className="search-bar__swap">
          <button
            type="button"
            className="icon-btn"
            onClick={onSwapEnds}
            disabled={!originKey && !destinationKey}
            aria-label={t.swapEnds}
          >
            ↕
          </button>
        </div>

        <label className="field" htmlFor="destination-select">
          <span>{t.to}</span>
          <select
            id="destination-select"
            name="destination"
            value={destinationKey}
            onChange={(event) => onDestinationChange(event.target.value)}
            aria-label={t.to}
          >
            <option value="">{t.chooseDestination}</option>
            {toPlaces.map((place) => (
              <option
                key={place.key}
                value={place.key}
                title={place.secondary}
              >
                {place.label}
              </option>
            ))}
          </select>
        </label>
      </div>

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
            disabled={
              loadingRoutes ||
              !originKey ||
              !destinationKey ||
              originKey === destinationKey
            }
          >
            {loadingRoutes ? t.comparing : t.compare}
          </button>
        </>
      )}
    </section>
  )
}
