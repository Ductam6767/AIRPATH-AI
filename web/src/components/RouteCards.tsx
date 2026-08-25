import type { RouteRecord } from '../types'
import { EXPOSURE_NOTE } from '../constants'
import {
  formatExposure,
  formatMinutes,
  hasLowerPredictedExposureAlternative,
  isLowerPredictedExposure,
  reductionBadgeText,
  routeCardTitle,
  routeKindLabel,
} from '../utils/labels'

interface RouteCardsProps {
  fastest: RouteRecord | null
  alternatives: RouteRecord[]
  selectedRouteId: string | null
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
  const hasLowerExposureAlt =
    hasLowerPredictedExposureAlternative(alternatives)

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
                        : isLowerPredictedExposure(
                              route.predicted_exposure_reduction_percent,
                            )
                          ? 'kind kind--alt'
                          : 'kind kind--neutral'
                    }
                  >
                    {routeKindLabel(route)}
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
                    <span
                      className={
                        isLowerPredictedExposure(
                          route.predicted_exposure_reduction_percent,
                        )
                          ? 'chip chip--eco'
                          : 'chip'
                      }
                    >
                      {reduction}
                    </span>
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

      {hasLowerExposureAlt ? (
        <p className="muted small">
          Top feasible alternatives among the generated candidate routes.
          Slightly slower options with lower predicted exposure are listed first.
          AIRPATH compares feasible route alternatives rather than guaranteeing a
          cleaner route.
        </p>
      ) : (
        <div className="empty-alts" role="status">
          <p>Fastest route is also the lowest-exposure feasible option.</p>
          <p>
            No lower-exposure alternative was found within your time limit.
          </p>
        </div>
      )}
    </section>
  )
}
