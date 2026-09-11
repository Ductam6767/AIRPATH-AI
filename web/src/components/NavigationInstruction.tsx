import type { AssistSnapshot } from '../hooks/useAssistNavigation'
import { useI18n } from '../i18n/LanguageContext'
import type { RouteRecord } from '../types'
import {
  formatDistanceKm,
  formatMinutes,
  routeCardTitle,
} from '../utils/labels'
import { armedTurnDirection } from '../maneuver/turnSignal'
import {
  isCueEmphasized,
  remainingToCue,
  type PlacedCue,
} from '../maneuver/guidanceCues'
import { BlinkerArrow } from './BlinkerArrow'
import { ConfirmLed } from './ConfirmLed'
import { GuidanceDiagram } from './GuidanceDiagram'

interface NavigationInstructionProps {
  route: RouteRecord
  snapshot: AssistSnapshot
  hudCue?: PlacedCue | null
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

function cueTitle(
  cue: PlacedCue,
  t: ReturnType<typeof useI18n>['t'],
): string {
  if (cue.kind === 'roundabout') return t.cueRoundabout(cue.exit ?? 1)
  if (cue.kind === 'lane') {
    return cue.turn === 'right' ? t.cueLaneOuter : t.cueLaneInner
  }
  return cue.relation === 'under' ? t.cueBridgeUnder : t.cueBridgeOver
}

export function NavigationInstruction({
  route,
  snapshot,
  hudCue = null,
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
    snapshot.lastTurn?.turn,
    snapshot.distancePastLastTurnM,
  )
  const cueRemaining = hudCue
    ? remainingToCue(hudCue.atM, snapshot.distanceAlongM)
    : null
  const cueOn =
    hudCue != null &&
    cueRemaining != null &&
    isCueEmphasized(hudCue.kind, cueRemaining)

  return (
    <article className="nav-card" aria-live="polite">
      <div className="nav-card__primary">
        <BlinkerArrow turn={blinker} size="lg" />
        <ConfirmLed on={snapshot.cornerConfirm} size="lg" />
        <div className="nav-card__copy">
          <p className="nav-card__turn">
            {hudCue ? cueTitle(hudCue, t) : maneuverTitle(snapshot, t)}
          </p>
          <p className="nav-card__distance">
            {hudCue && cueRemaining != null
              ? t.inDistance(Math.max(0, cueRemaining))
              : snapshot.next
                ? t.inDistance(snapshot.distanceToNextM)
                : t.turnArrive}
          </p>
          {snapshot.cornerConfirm ? (
            <p className="nav-card__confirm">{t.turnConfirm}</p>
          ) : null}
        </div>
      </div>
      {hudCue ? (
        <div className="nav-card__diagram" aria-label={t.cueDiagram}>
          <GuidanceDiagram cue={hudCue} size="hud" emphasized={cueOn} />
          {hudCue.kind === 'roundabout' ? (
            <p className="nav-card__paint-hint">{t.cuePaintPath}</p>
          ) : null}
        </div>
      ) : null}
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
