import type { Scenario, TimeWindow, TravelMode } from '../types'
import { destinationsForOrigin, uniqueOrigins } from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle } from './ModeToggle'
import { TimeWindowToggle } from './TimeWindowToggle'

interface SidebarProps {
  scenarios: Scenario[]
  originKey: string
  destinationKey: string
  mode: TravelMode
  timeWindow: TimeWindow
  deltaMinutes: number
  loadingRoutes: boolean
  onOriginChange: (key: string) => void
  onDestinationChange: (key: string) => void
  onModeChange: (mode: TravelMode) => void
  onTimeWindowChange: (value: TimeWindow) => void
  onDeltaChange: (value: number) => void
  onFindRoutes: () => void
  onOpenMethodology: () => void
  onOpenGap1: () => void
}

export function Sidebar({
  scenarios,
  originKey,
  destinationKey,
  mode,
  timeWindow,
  deltaMinutes,
  loadingRoutes,
  onOriginChange,
  onDestinationChange,
  onModeChange,
  onTimeWindowChange,
  onDeltaChange,
  onFindRoutes,
  onOpenMethodology,
  onOpenGap1,
}: SidebarProps) {
  const origins = uniqueOrigins(scenarios)
  const destinations = originKey
    ? destinationsForOrigin(scenarios, originKey)
    : []

  return (
    <aside className="sidebar" aria-label="Trip controls">
      <div className="brand-block">
        <p className="brand">AIRPATH-AI</p>
        <h1 className="hero-line">
          Compare routes by travel time and predicted PM2.5 exposure.
        </h1>
        <p className="muted">
          Compare the fastest route with up to three slower, lower-exposure
          options when they exist. Walking and motorbike use different detour
          thresholds. If the fastest route is also the lowest-exposure option,
          only that one card is shown.
        </p>
        <p className="pilot-chip">
          Pilot area · hourly data · precomputed scenarios · not live routing
        </p>
      </div>

      <div className="control-stack">
        <label className="field" htmlFor="origin-select">
          <span>From</span>
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
          <span>To</span>
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

        <ModeToggle value={mode} onChange={onModeChange} disabled={loadingRoutes} />

        <TimeWindowToggle
          value={timeWindow}
          onChange={onTimeWindowChange}
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
          {loadingRoutes ? 'Comparing routes…' : 'Compare routes'}
        </button>

        <button type="button" className="linkish" onClick={onOpenMethodology}>
          How AIRPATH works
        </button>
        <button type="button" className="linkish" onClick={onOpenGap1}>
          Gap 1 research exhibit
        </button>
      </div>

      <p className="sidebar-footnote muted small">
        From/To names are OSM street labels from the demo API. Coordinates stay in
        option titles and map popups. This demo does not search the live city
        network.
      </p>
    </aside>
  )
}
