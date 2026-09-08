import type { RouteRecord } from '../types'
import { useI18n } from '../i18n/LanguageContext'
import {
  formatDistanceKm,
  formatExposure,
  formatMinutes,
  isLowerPredictedExposure,
  productRouteKind,
  reductionBadgeText,
} from '../utils/labels'

interface WhyThisRouteProps {
  route: RouteRecord
  deltaMinutes: number
  hasLowerExposureAlt: boolean
}

export function WhyThisRoute({
  route,
  deltaMinutes,
  hasLowerExposureAlt,
}: WhyThisRouteProps) {
  const { t } = useI18n()
  const kind = productRouteKind(route)
  const copy =
    kind === 'health'
      ? t.whyHealth
      : kind === 'fastest'
        ? hasLowerExposureAlt
          ? t.whyFastestHurry
          : t.whyFastest
        : t.whyBalanced
  const vsFastest = reductionBadgeText(route.predicted_exposure_reduction_percent)
  const within =
    route.additional_time_vs_fastest_minutes <= deltaMinutes + 0.05

  return (
    <section className="why-route" aria-labelledby="why-route-title">
      <h3 id="why-route-title">{t.whyTitle}</h3>
      <p>{copy}</p>
      <dl className="why-route__metrics">
        <div>
          <dt>{t.whyTime}</dt>
          <dd>{formatMinutes(route.travel_time_minutes)} min</dd>
        </div>
        <div>
          <dt>{t.whyDistance}</dt>
          <dd>{formatDistanceKm(route.distance_m)}</dd>
        </div>
        <div>
          <dt>{t.whyExposure}</dt>
          <dd>
            {formatExposure(route.predicted_exposure_index)}
            <span className="muted"> (µg/m³)·min</span>
          </dd>
        </div>
        <div>
          <dt>{t.whyVsFastest}</dt>
          <dd>
            {route.is_fastest
              ? 'Baseline'
              : vsFastest ?? 'Similar predicted exposure'}
          </dd>
        </div>
        <div>
          <dt>{t.whyConstraint}</dt>
          <dd>
            {within ? `${t.whyWithin} ✓` : `+${deltaMinutes} min`}
          </dd>
        </div>
      </dl>
      {kind === 'health' &&
      isLowerPredictedExposure(route.predicted_exposure_reduction_percent) ? (
        <p className="muted small">
          ↓ {Math.round(route.predicted_exposure_reduction_percent)}% {t.whyExposure}
        </p>
      ) : null}
    </section>
  )
}
