import type { RouteRecord } from '../types'
import { useI18n } from '../i18n/LanguageContext'
import {
  extraDistanceMeters,
  formatDistanceKm,
  formatMinutes,
  formatSignedDistanceKm,
  formatSignedMinutes,
  isLowerPredictedExposure,
} from '../utils/labels'

interface WhyThisRouteProps {
  route: RouteRecord
  fastestRoute: RouteRecord
  onStart: () => void
}

function exposureTone(percent: number): 'lower' | 'higher' | 'similar' {
  if (isLowerPredictedExposure(percent)) return 'lower'
  if (percent < -0.5) return 'higher'
  return 'similar'
}

export function WhyThisRoute({
  route,
  fastestRoute,
  onStart,
}: WhyThisRouteProps) {
  const { t } = useI18n()
  const percent = route.predicted_exposure_reduction_percent
  const tone = exposureTone(percent)
  const extraMeters = extraDistanceMeters(route, fastestRoute)
  const roundedPercent = Math.round(Math.abs(percent))

  return (
    <section className="route-action" aria-labelledby="why-route-title">
      <article className="why-route">
        <h3 id="why-route-title">{t.whyTitle}</h3>
        <p className={`why-route__exposure why-route__exposure--${tone}`}>
          <span className="why-route__exposure-value">
            {tone === 'lower' ? `↓ ${roundedPercent}%` : null}
            {tone === 'higher' ? `↑ ${roundedPercent}%` : null}
            {tone === 'similar' ? '0%' : null}
          </span>
          <span className="why-route__exposure-label">{t.whyExposure}</span>
        </p>
        <dl className="why-route__metrics">
          <div>
            <dt>{t.whyTime}</dt>
            <dd>
              {formatMinutes(route.travel_time_minutes)} min
              <span className="why-route__delta">
                {formatSignedMinutes(route.additional_time_vs_fastest_minutes)}
              </span>
            </dd>
          </div>
          <div>
            <dt>{t.whyDistance}</dt>
            <dd>
              {formatDistanceKm(route.distance_m)}
              <span className="why-route__delta">
                {formatSignedDistanceKm(extraMeters)}
              </span>
            </dd>
          </div>
        </dl>
      </article>
      <button
        type="button"
        className="start-card"
        onClick={onStart}
        aria-label={t.startNav}
      >
        <span className="start-card__label">{t.startCta}</span>
        <span className="start-card__arrow" aria-hidden="true">
          →
        </span>
      </button>
    </section>
  )
}
