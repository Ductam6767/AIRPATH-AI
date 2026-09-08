import { IS_MOBILE_BUILD } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import type { Scenario, TimeWindow, TravelMode } from '../types'
import { matchDemoPair, placesCompatibleWith } from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle, type MobilityChoice } from './ModeToggle'
import { PlacePicker } from './PlacePicker'
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
  const fromPlaces = placesCompatibleWith(scenarios, destinationKey, 'from')
  const toPlaces = placesCompatibleWith(scenarios, originKey, 'to')
  const canCompare = Boolean(matchDemoPair(scenarios, originKey, destinationKey))

  return (
    <section className={compact ? 'search-bar search-bar--compact' : 'search-bar'}>
      <div className="search-bar__ends">
        <PlacePicker
          label={t.from}
          placeholder={t.chooseOrigin}
          value={originKey}
          places={fromPlaces}
          onChange={onOriginChange}
        />

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

        <PlacePicker
          label={t.to}
          placeholder={t.chooseDestination}
          value={destinationKey}
          places={toPlaces}
          onChange={onDestinationChange}
        />
      </div>

      {compact ? null : (
        <>
          <button
            type="button"
            className="primary-btn search-bar__compare"
            onClick={onFindRoutes}
            disabled={loadingRoutes || !canCompare}
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
