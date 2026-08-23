import type { RouteRecord } from '../types'
import { EXPOSURE_NOTE } from '../constants'
import {
  formatExposure,
  formatMinutes,
  reductionBadgeText,
  routeCardTitle,
} from '../utils/labels'

interface RouteCardsProps {
  fastest: RouteRecord | null
  alternatives: RouteRecord[]
  selectedRouteId: string | null
  deltaMinutes: number
  onSelectRoute: (routeId: string) => void
}

function ExposureBar({
  value,
  max,
  tone,
}: {
  value: number
  max: number
  tone: 'fastest' | 'alt' | 'selected'
}) {
  const width = max > 0 ? Math.max(8, Math.min(100, (value / max) * 100)) : 8
  return (
    <div className="exposure-bar" aria-hidden="true">
      <div
        className={`exposure-bar__fill exposure-bar__fill--${tone}`}
        style={{ width: `${width}%` }}
      />
    </div>
  )
}

export function RouteCards({
  fastest,
  alternatives,
  selectedRouteId,
  deltaMinutes,
  onSelectRoute,
}: RouteCardsProps) {
  if (!fastest) {
    return null
  }

  const all = [fastest, ...alternatives]
  const maxExposure = Math.max(
    ...all.map((route) => route.predicted_exposure_index),
    1,
  )

  return (
    <section className="route-cards" aria-label="Route comparison">
      <div className="route-cards__header">
        <h2>Route comparison</h2>
        <p className="muted small">{EXPOSURE_NOTE}</p>
      </div>

      <ul className="route-card-list">
        {all.map((route) => {
          const selected = route.route_id === selectedRouteId
          const title = routeCardTitle(route)
          const extra = route.is_fastest
            ? '+0 min'
            : `+${formatMinutes(route.additional_time_vs_fastest_minutes)} min`
          const reduction = reductionBadgeText(
            route.predicted_exposure_reduction_percent,
          )
          const tone = route.is_fastest
            ? 'fastest'
            : selected
              ? 'selected'
              : 'alt'

          return (
            <li key={route.route_id}>
              <button
                type="button"
                className={`route-card ${selected ? 'is-selected' : ''} ${
                  route.is_fastest ? 'is-fastest' : 'is-alternative'
                }`}
                aria-pressed={selected}
                aria-label={`${title}, ${formatMinutes(route.travel_time_minutes)} minutes, ${extra}, predicted exposure ${formatExposure(route.predicted_exposure_index)}${!route.is_fastest && reduction ? `, ${reduction}` : ''}`}
                onClick={() => onSelectRoute(route.route_id)}
              >
                <div className="route-card__kicker">
                  <span
                    className={
                      route.is_fastest
                        ? 'kind kind--fastest'
                        : route.predicted_exposure_reduction_percent > 0.5
                          ? 'kind kind--alt'
                          : 'kind kind--neutral'
                    }
                  >
                    {route.is_fastest
                      ? 'Fastest'
                      : route.predicted_exposure_reduction_percent > 0.5
                        ? 'Lower predicted exposure'
                        : 'Feasible alternative'}
                  </span>
                  {selected ? <span className="kind kind--selected">Selected</span> : null}
                </div>
                <div className="route-card__top">
                  <span className="route-card__label">{title}</span>
                  <span className="route-card__time">
                    {formatMinutes(route.travel_time_minutes)} min
                  </span>
                </div>
                <div className="route-card__meta">
                  <span className="chip">{extra}</span>
                  {!route.is_fastest && reduction ? (
                    <span className="chip chip--eco">{reduction}</span>
                  ) : null}
                </div>
                <p className="route-card__exposure">
                  Predicted exposure{' '}
                  <strong>{formatExposure(route.predicted_exposure_index)}</strong>
                  <span className="muted"> (µg/m³)·min</span>
                </p>
                <ExposureBar
                  value={route.predicted_exposure_index}
                  max={maxExposure}
                  tone={tone}
                />
              </button>
            </li>
          )
        })}
      </ul>

      {alternatives.length === 0 ? (
        <p className="empty-alts" role="status">
          {deltaMinutes === 0
            ? 'No alternative fits the selected +0 min limit. Showing the fastest route.'
            : 'No lower-exposure alternative fits your current time limit. Try allowing a few more minutes.'}
        </p>
      ) : (
        <p className="muted small">
          Top feasible lower-exposure alternatives among the generated candidate
          routes.
        </p>
      )}
    </section>
  )
}
