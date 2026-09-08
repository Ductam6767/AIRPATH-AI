import type { AssistSnapshot } from '../hooks/useAssistNavigation'
import { useI18n } from '../i18n/LanguageContext'

interface TurnSignalStatusProps {
  snapshot: AssistSnapshot
}

function signalState(snapshot: AssistSnapshot): 'ready' | 'left' | 'right' | 'active' | 'off' {
  if (!snapshot.active || !snapshot.next) return 'ready'
  const turn = snapshot.next.turn
  if (turn === 'arrive' || turn === 'straight') return 'off'
  if (snapshot.distanceToNextM <= 40) return 'active'
  return turn === 'left' ? 'left' : 'right'
}

export function TurnSignalStatus({ snapshot }: TurnSignalStatusProps) {
  const { t } = useI18n()
  const state = signalState(snapshot)
  const distance = Math.round(snapshot.distanceToNextM)
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
      {state === 'left' || state === 'right' ? (
        <span className="turn-signal__meta">{distance} m</span>
      ) : null}
      <p className="muted small">{t.turnSignalProto}</p>
    </div>
  )
}
