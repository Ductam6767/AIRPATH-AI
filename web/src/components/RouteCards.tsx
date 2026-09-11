import type { RouteRecord } from '../types'
import { EXPOSURE_NOTE } from '../constants'
import { useI18n } from '../i18n/LanguageContext'
import {
  exposureCompareHeadline,
  formatDistanceKm,
  formatExposure,
  formatMinutes,
  formatSignedMinutes,
  hasLowerPredictedExposureAlternative,
  productRouteKind,
  reductionBadgeText,
  routeCardTitle,
  routeKindLabel,
} from '../utils/labels'

interface RouteCardsProps {
  fastest: RouteRecord | null
  alternatives: RouteRecord[]
  selectedRouteId: string | null
  recommendedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  compact?: boolean
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
  recommendedRouteId,
  onSelectRoute,
  compact = false,
}: RouteCardsProps) {
  const { t } = useI18n()
  if (!fastest) {
    return null
  }

  const all = [fastest, ...alternatives]
  const maxExposure = Math.max(
    ...all.map((route) => route.predicted_exposure_index),
    1,
  )
  const hasLowerExposureAlt = hasLowerPredictedExposureAlternative(alternatives)

  return (
    <section className="route-cards" aria-label="Route comparison" id="route-comparison">
      <div className="route-cards__header">
        <h2>Route comparison</h2>
        <p className="muted small">{EXPOSURE_NOTE}</p>
      </div>

      <ul className={`route-card-list${compact ? ' route-card-list--compact' : ''}`}>
        {all.map((route) => {
          const selected = route.route_id === selectedRouteId
          const recommended = route.route_id === recommendedRouteId
          const title = routeCardTitle(route)
          const kind = productRouteKind(route)
          const extra = route.is_fastest
            ? '+0 min'
            : formatSignedMinutes(route.additional_time_vs_fastest_minutes)
          const reduction = reductionBadgeText(
            route.predicted_exposure_reduction_percent,
          )
          const exposureCompare = exposureCompareHeadline(
            route.predicted_exposure_reduction_percent,
            route.is_fastest,
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
                  recommended ? 'is-recommended' : ''
                } ${route.is_fastest ? 'is-fastest' : 'is-alternative'}`}
                aria-pressed={selected}
                aria-label={`${title}, ${formatMinutes(route.travel_time_minutes)} minutes, ${extra}, predicted exposure ${formatExposure(route.predicted_exposure_index)}${!route.is_fastest && reduction ? `, ${reduction}` : ''}`}
                onClick={() => onSelectRoute(route.route_id)}
              >
                <div className="route-card__kicker">
                  {recommended ? (
                    <span className="kind kind--recommended">{t.recommended}</span>
                  ) : null}
                  <span
                    className={
                      kind === 'fastest'
                        ? 'kind kind--fastest'
                        : kind === 'health'
                          ? 'kind kind--alt'
                          : 'kind kind--neutral'
                    }
                  >
                    {routeKindLabel(route)}
                  </span>
                  {kind === 'fastest' && !hasLowerExposureAlt ? (
                    <span className="kind kind--alt">{t.alsoLowestExposure}</span>
                  ) : null}
                  {selected ? <span className="kind kind--selected">Selected</span> : null}
                </div>
                <div className="route-card__top">
                  <span className="route-card__label">{title}</span>
                  <span className="route-card__time">
                    {formatMinutes(route.travel_time_minutes)} min
                  </span>
                </div>
                <p className="route-card__distance">{formatDistanceKm(route.distance_m)}</p>
                <div className="route-card__stats">
                  <div className="route-stat">
                    <span className="route-stat__value">{extra}</span>
                    <span className="route-stat__label">Extra time</span>
                  </div>
                  <div className={`route-stat route-stat--${exposureCompare.tone}`}>
                    <span className="route-stat__value">{exposureCompare.value}</span>
                    <span className="route-stat__label">{exposureCompare.caption}</span>
                  </div>
                </div>
                {reduction ? <span className="sr-only">{reduction}</span> : null}
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

    </section>
  )
}

export function RouteCardsNotes({
  alternatives,
}: {
  alternatives: RouteRecord[]
}) {
  const { t } = useI18n()
  const hasLowerExposureAlt = hasLowerPredictedExposureAlternative(alternatives)

  return (
    <div className="route-cards-notes">
      {hasLowerExposureAlt ? (
        <p className="muted small">{t.altsCompareNote}</p>
      ) : (
        <div className="empty-alts" role="status">
          <p>{t.emptyAltsFastestBest}</p>
          <p>
            {alternatives.length === 0
              ? t.emptyAltsNoneFound
              : t.otherFeasibleNote}
          </p>
        </div>
      )}
      <p className="muted small search-bar__pack-note">{t.packFinding}</p>
    </div>
  )
}
