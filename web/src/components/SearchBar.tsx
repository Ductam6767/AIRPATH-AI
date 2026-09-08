import { IS_MOBILE_BUILD } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import type { Scenario, TimeWindow, TravelMode } from '../types'
import {
  matchDemoPair,
  tripsKeepingFrom,
  tripsKeepingTo,
  uniquePlaces,
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
  onSelectPair: (fromKey: string, toKey: string) => void
  onModeChange: (mode: TravelMode) => void
  onMobilityChange: (choice: MobilityChoice) => void
  onTimeWindowChange: (value: TimeWindow) => void
  onDeltaChange: (value: number) => void
  onFindRoutes: () => void
}

function PlaceOptions({
  places,
  matchedKeys,
  demoGroup,
  otherGroup,
}: {
  places: { key: string; label: string; secondary: string }[]
  matchedKeys: Set<string>
  demoGroup: string
  otherGroup: string
}) {
  if (matchedKeys.size === 0) {
    return places.map((place) => (
      <option key={place.key} value={place.key} title={place.secondary}>
        {place.label}
      </option>
    ))
  }
  const matched = places.filter((place) => matchedKeys.has(place.key))
  const other = places.filter((place) => !matchedKeys.has(place.key))
  return (
    <>
      {matched.length > 0 ? (
        <optgroup label={demoGroup}>
          {matched.map((place) => (
            <option key={place.key} value={place.key} title={place.secondary}>
              {place.label}
            </option>
          ))}
        </optgroup>
      ) : null}
      {other.length > 0 ? (
        <optgroup label={otherGroup}>
          {other.map((place) => (
            <option key={place.key} value={place.key} title={place.secondary}>
              {place.label}
            </option>
          ))}
        </optgroup>
      ) : null}
    </>
  )
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
  onSelectPair,
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
  const matched = Boolean(matchDemoPair(scenarios, originKey, destinationKey))
  const unmatched = Boolean(
    originKey &&
      destinationKey &&
      originKey !== destinationKey &&
      !matched,
  )
  const fromMatched = new Set(
    destinationKey
      ? fromPlaces
          .filter((place) => matchDemoPair(scenarios, place.key, destinationKey))
          .map((place) => place.key)
      : [],
  )
  const toMatched = new Set(
    originKey
      ? toPlaces
          .filter((place) => matchDemoPair(scenarios, originKey, place.key))
          .map((place) => place.key)
      : [],
  )
  const keepFrom = tripsKeepingFrom(scenarios, originKey).filter(
    (trip) => trip.toKey !== destinationKey,
  )
  const keepTo = tripsKeepingTo(scenarios, destinationKey).filter(
    (trip) => trip.fromKey !== originKey,
  )
  const showFromSuggestions = Boolean(originKey) && keepFrom.length > 0 && !matched
  const showToSuggestions = Boolean(destinationKey) && keepTo.length > 0 && !matched

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
            <PlaceOptions
              places={fromPlaces}
              matchedKeys={fromMatched}
              demoGroup={t.demoRouteGroup}
              otherGroup={t.otherPlaceGroup}
            />
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
            <PlaceOptions
              places={toPlaces}
              matchedKeys={toMatched}
              demoGroup={t.demoRouteGroup}
              otherGroup={t.otherPlaceGroup}
            />
          </select>
        </label>
      </div>

      {showFromSuggestions || showToSuggestions ? (
        <div className="pair-hint" role="status">
          {unmatched ? <p className="pair-hint__note">{t.unmatchedPair}</p> : null}
          {showFromSuggestions
            ? keepFrom.map((trip) => (
                <p key={`from-${trip.toKey}`} className="pair-hint__row">
                  <button
                    type="button"
                    className="pair-hint__chip"
                    onClick={() => onSelectPair(originKey, trip.toKey)}
                  >
                    {unmatched
                      ? t.keepFromTrip(trip.toLabel)
                      : t.setToTrip(trip.toLabel)}
                  </button>
                </p>
              ))
            : null}
          {showToSuggestions
            ? keepTo.map((trip) => (
                <p key={`to-${trip.fromKey}`} className="pair-hint__row">
                  <button
                    type="button"
                    className="pair-hint__chip"
                    onClick={() => onSelectPair(trip.fromKey, destinationKey)}
                  >
                    {unmatched
                      ? t.keepToTrip(trip.fromLabel)
                      : t.setFromTrip(trip.fromLabel)}
                  </button>
                </p>
              ))
            : null}
        </div>
      ) : null}

      {compact ? null : (
        <>
          <button
            type="button"
            className="primary-btn search-bar__compare"
            onClick={onFindRoutes}
            title={unmatched ? t.unmatchedPair : undefined}
            disabled={
              loadingRoutes ||
              !originKey ||
              !destinationKey ||
              originKey === destinationKey ||
              unmatched
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
