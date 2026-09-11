import type { AssistSnapshot } from '../hooks/useAssistNavigation'
import { useI18n } from '../i18n/LanguageContext'
import { armedTurnDirection, signalState } from '../maneuver/turnSignal'

interface TurnSignalStatusProps {
  snapshot: AssistSnapshot
}

export function TurnSignalStatus({ snapshot }: TurnSignalStatusProps) {
  const { t } = useI18n()
  const state = signalState(snapshot)
  const distance = Math.round(snapshot.distanceToNextM)
  const armed = armedTurnDirection(snapshot.next?.turn, snapshot.distanceToNextM)
  const label =
    state === 'ready'
      ? t.turnSignalReady
      : state === 'off'
        ? t.turnSignalOff
        : state === 'active'
          ? t.turnSignalActive
          : state === 'left'
            ? t.turnSignalLeft
            : t.turnSignalRight

  return (
    <div
      className={`turn-signal turn-signal--${state}`}
      role="status"
      aria-label={`${t.turnSignalTitle}: ${label}`}
    >
      <span className="turn-signal__kicker">{t.turnSignalTitle}</span>
      <strong className="turn-signal__label">
        <span className="turn-signal__dot" aria-hidden="true" />
        {label}
      </strong>
      {armed ? <span className="turn-signal__meta">{distance} m</span> : null}
      <p className="muted small">{t.turnSignalProto}</p>
    </div>
  )
}
