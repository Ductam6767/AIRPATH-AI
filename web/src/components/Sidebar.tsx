import type { Scenario, TravelMode } from '../types'
import { destinationsForOrigin, uniqueOrigins } from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle } from './ModeToggle'

interface SidebarProps {
  scenarios: Scenario[]
  originKey: string
  destinationKey: string
  mode: TravelMode
  deltaMinutes: number
  loadingRoutes: boolean
  onOriginChange: (key: string) => void
  onDestinationChange: (key: string) => void
  onModeChange: (mode: TravelMode) => void
  onDeltaChange: (value: number) => void
  onFindRoutes: () => void
  onOpenMethodology: () => void
}

export function Sidebar({
  scenarios,
  originKey,
  destinationKey,
  mode,
  deltaMinutes,
  loadingRoutes,
  onOriginChange,
  onDestinationChange,
  onModeChange,
  onDeltaChange,
  onFindRoutes,
  onOpenMethodology,
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
          Compare the fastest route (shortest travel time) with up to three
          slower alternatives that have lower predicted PM2.5 exposure. Choose
          the fastest route when you are in a hurry, or an alternative to reduce
          exposure.
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
      </div>

      <p className="sidebar-footnote muted small">
        Coordinates stay in secondary metadata (option titles and map popups). This
        demo does not search the live city network.
      </p>
    </aside>
  )
}
