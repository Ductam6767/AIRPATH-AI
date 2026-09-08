import { IS_MOBILE_BUILD } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import type { Scenario, TimeWindow, TravelMode } from '../types'
import {
  destinationsForOrigin,
  findScenarioId,
  originsForDestination,
  uniqueDestinations,
  uniqueOrigins,
} from '../utils/labels'
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
  const origins = uniqueOrigins(scenarios)
  const destinations = uniqueDestinations(scenarios)
  const pairId = findScenarioId(scenarios, originKey, destinationKey)
  const knownDests = originKey
    ? destinationsForOrigin(scenarios, originKey)
    : []
  const knownOrigins = destinationKey
    ? originsForDestination(scenarios, destinationKey)
    : []
  const reverseId = findScenarioId(scenarios, destinationKey, originKey)
  const canSwap = Boolean(originKey && destinationKey && reverseId)
  const unmatched = Boolean(originKey && destinationKey && !pairId)
  const showDestHints = Boolean(knownDests.length && (!destinationKey || unmatched))
  const showOriginHints = Boolean(
    knownOrigins.length && (!originKey || unmatched),
  )

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
            {origins.map((item) => (
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
            disabled={!canSwap}
            aria-label={t.swapEnds}
            title={canSwap ? t.swapEnds : t.swapUnavailable}
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
            {destinations.map((place) => (
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

      {showDestHints || showOriginHints || unmatched ? (
        <div className="pair-hint">
          {unmatched ? <p className="muted small">{t.unmatchedPair}</p> : null}
          {showDestHints ? (
            <p className="pair-hint__row">
              <span>{t.demoGoesTo}</span>
              {knownDests.map((place) => (
                <button
                  key={place.key}
                  type="button"
                  className="pair-hint__chip"
                  onClick={() => onDestinationChange(place.key)}
                >
                  {place.label}
                </button>
              ))}
            </p>
          ) : null}
          {showOriginHints ? (
            <p className="pair-hint__row">
              <span>{t.demoStartsAt}</span>
              {knownOrigins.map((place) => (
                <button
                  key={place.key}
                  type="button"
                  className="pair-hint__chip"
                  onClick={() => onOriginChange(place.key)}
                >
                  {place.label}
                </button>
              ))}
            </p>
          ) : null}
        </div>
      ) : null}

      {compact ? null : (
        <>
          <button
            type="button"
            className="primary-btn search-bar__compare"
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
        </>
      )}
    </section>
  )
}
