import type { Scenario } from '../types'
import {
  destinationsForOrigin,
  findScenarioId,
  uniqueOrigins,
} from '../utils/labels'
import { DeltaSlider } from './DeltaSlider'
import { ModeToggle } from './ModeToggle'
import type { TravelMode } from '../types'

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
    <aside className="sidebar" aria-label="Route controls">
      <div className="brand-block">
        <p className="brand">AIRPATH-AI</p>
        <h1 className="hero-line">Find a route that fits your time — and your air.</h1>
        <p className="muted">
          Compare faster and lower-exposure routes using forecast-based PM2.5 estimates.
        </p>
        <p className="pilot-chip">Precomputed pilot scenarios · not live city routing</p>
      </div>

      <div className="control-stack">
        <label className="field">
          <span>From</span>
          <select
            value={originKey}
            onChange={(event) => onOriginChange(event.target.value)}
            aria-label="Origin"
          >
            {origins.map((origin) => (
              <option key={origin.key} value={origin.key}>
                {origin.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>To</span>
          <select
            value={destinationKey}
            onChange={(event) => onDestinationChange(event.target.value)}
            aria-label="Destination"
            disabled={destinations.length === 0}
          >
            {destinations.map((destination) => (
              <option key={destination.key} value={destination.key}>
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
          {loadingRoutes ? 'Finding routes…' : 'Find routes'}
        </button>

        <button
          type="button"
          className="linkish"
          onClick={onOpenMethodology}
        >
          How AIRPATH works · limitations
        </button>
      </div>

      <p className="sidebar-footnote muted small">
        Demo OD pairs come from the frozen research pack. Selecting From/To maps to a
        valid <code>scenario_id</code>
        {originKey && destinationKey
          ? ` (currently ${findScenarioId(scenarios, originKey, destinationKey) ?? '—'})`
          : ''}
        .
      </p>
    </aside>
  )
}
