import type { AssistSnapshot } from '../hooks/useAssistNavigation'
import { useI18n } from '../i18n/LanguageContext'
import { armedTurnDirection, isCornerConfirm, signalState, TURN_SIGNAL_HOLD_AFTER_M } from '../maneuver/turnSignal'
import { ConfirmLed } from './ConfirmLed'

interface TurnSignalStatusProps {
  snapshot: AssistSnapshot
}

export function TurnSignalStatus({ snapshot }: TurnSignalStatusProps) {
  const { t } = useI18n()
  const state = signalState(snapshot)
  const distance = Math.round(snapshot.distanceToNextM)
  const armed = armedTurnDirection(
    snapshot.next?.turn,
    snapshot.distanceToNextM,
    snapshot.lastTurn?.turn,
    snapshot.distancePastLastTurnM,
  )
  const holding =
    snapshot.distancePastLastTurnM >= 0 &&
    snapshot.distancePastLastTurnM <= TURN_SIGNAL_HOLD_AFTER_M &&
    (snapshot.lastTurn?.turn === 'left' || snapshot.lastTurn?.turn === 'right')
  const confirming = isCornerConfirm(
    snapshot.next?.turn,
    snapshot.distanceToNextM,
    snapshot.lastTurn?.turn,
    snapshot.distancePastLastTurnM,
  )
  const label =
    state === 'ready'
      ? t.turnSignalReady
      : confirming
        ? t.turnConfirm
        : state === 'off'
          ? t.turnSignalOff
          : state === 'active'
            ? t.turnSignalActive
            : state === 'left'
              ? t.turnSignalLeft
              : t.turnSignalRight

  return (
    <div
      className={`turn-signal turn-signal--${state}${confirming ? ' turn-signal--confirm' : ''}`}
      role="status"
      aria-label={`${t.turnSignalTitle}: ${label}`}
    >
      <span className="turn-signal__kicker">{t.turnSignalTitle}</span>
      <strong className="turn-signal__label">
        <span className="turn-signal__dot" aria-hidden="true" />
        <ConfirmLed on={confirming} size="md" />
        {label}
      </strong>
      {armed && !holding ? (
        <span className="turn-signal__meta">{distance} m</span>
      ) : null}
      <p className="muted small">
        {confirming ? t.turnConfirmHint : t.turnSignalProto}
      </p>
    </div>
  )
}
