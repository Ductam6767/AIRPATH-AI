import type { AssistSnapshot } from '../hooks/useAssistNavigation'
import { useI18n } from '../i18n/LanguageContext'
import type { RouteRecord } from '../types'
import {
  formatDistanceKm,
  formatMinutes,
  routeCardTitle,
} from '../utils/labels'
import { armedTurnDirection } from '../maneuver/turnSignal'
import { BlinkerArrow } from './BlinkerArrow'

interface NavigationInstructionProps {
  route: RouteRecord
  snapshot: AssistSnapshot
}

function maneuverTitle(
  snapshot: AssistSnapshot,
  t: ReturnType<typeof useI18n>['t'],
): string {
  const turn = snapshot.next?.turn
  if (turn === 'left') return t.turnLeft
  if (turn === 'right') return t.turnRight
  if (turn === 'arrive') return t.turnArrive
  return t.turnContinue
}

export function NavigationInstruction({
  route,
  snapshot,
}: NavigationInstructionProps) {
  const { t } = useI18n()
  const remainingM = Math.max(0, route.distance_m - snapshot.distanceAlongM)
  const progress =
    snapshot.routeLengthM > 0
      ? snapshot.distanceAlongM / snapshot.routeLengthM
      : 0
  const remainingMin = Math.max(
    0,
    route.travel_time_minutes * (1 - progress),
  )

  const blinker = armedTurnDirection(
    snapshot.next?.turn,
    snapshot.distanceToNextM,
  )

  return (
    <article className="nav-card" aria-live="polite">
      <div className="nav-card__primary">
        <BlinkerArrow turn={blinker} size="lg" />
        <div className="nav-card__copy">
          <p className="nav-card__turn">{maneuverTitle(snapshot, t)}</p>
          <p className="nav-card__distance">
            {snapshot.next ? t.inDistance(snapshot.distanceToNextM) : t.turnArrive}
          </p>
        </div>
      </div>
      <p className="nav-card__meta">
        {formatMinutes(remainingMin)} {t.minLeft}
        <span aria-hidden="true"> · </span>
        {formatDistanceKm(remainingM)} {t.remaining}
      </p>
      <p className="muted small">
        {t.selectedRoute}: {routeCardTitle(route)}
      </p>
    </article>
  )
}
