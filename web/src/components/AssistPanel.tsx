import { useEffect, useState } from 'react'
import { useI18n } from '../i18n/LanguageContext'
import type { AssistSnapshot, AssistMode } from '../hooks/useAssistNavigation'
import {
  getBleTransportState,
  pairBleDevice,
  sendAssistPayload,
  subscribeBleTransport,
  type BleTransportState,
} from '../ble/bleTransport'
import { armedTurnDirection } from '../maneuver/turnSignal'
import { BlinkerArrow } from './BlinkerArrow'
import { ConfirmLed } from './ConfirmLed'

interface AssistPanelProps {
  snapshot: AssistSnapshot
  assistMode: AssistMode
  onAssistModeChange: (mode: AssistMode) => void
  onReset: () => void
}

function turnLabel(
  turn: AssistSnapshot['next'],
  t: ReturnType<typeof useI18n>['t'],
): string {
  if (!turn) return '—'
  if (turn.turn === 'left') return t.turnLeft
  if (turn.turn === 'right') return t.turnRight
  if (turn.turn === 'arrive') return t.turnArrive
  return t.turnContinue
}

export function AssistPanel({
  snapshot,
  assistMode,
  onAssistModeChange,
  onReset,
}: AssistPanelProps) {
  const { t } = useI18n()
  const [ble, setBle] = useState<BleTransportState>(() => getBleTransportState())

  useEffect(() => subscribeBleTransport(setBle), [])

  const disabled = !snapshot.active && assistMode === 'off'

  return (
    <section className="assist-panel" aria-label={t.assistTitle}>
      <div className="assist-panel__header">
        <h2>{t.assistTitle}</h2>
        <p className="small muted">{t.assistIntro}</p>
      </div>

      <div className="assist-mode-row" role="radiogroup" aria-label={t.assistTitle}>
        {(
          [
            ['off', t.assistOff],
            ['demo', t.assistDemo],
            ['live', t.assistGps],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={
              assistMode === value ? 'assist-mode-btn is-active' : 'assist-mode-btn'
            }
            aria-pressed={assistMode === value}
            onClick={() => onAssistModeChange(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {assistMode !== 'off' ? (
        <>
          <div className="assist-metrics">
            <div className="assist-metric assist-metric--maneuver">
              <span className="assist-metric__label">{t.nextManeuver}</span>
              <strong className="assist-metric__value">
                <BlinkerArrow
                  turn={armedTurnDirection(
                    snapshot.next?.turn,
                    snapshot.distanceToNextM,
                    snapshot.lastTurn?.turn,
                    snapshot.distancePastLastTurnM,
                  )}
                  size="md"
                />
                <ConfirmLed on={snapshot.cornerConfirm} size="md" />
                {turnLabel(snapshot.next, t)}
              </strong>
            </div>
            <div className="assist-metric">
              <span className="assist-metric__label">{t.distance}</span>
              <strong className="assist-metric__value">
                {Math.round(snapshot.distanceToNextM)} m
              </strong>
            </div>
            <div className="assist-metric">
              <span className="assist-metric__label">{t.targetSpeed}</span>
              <strong className="assist-metric__value assist-speed-ladder">
                {snapshot.speedSteps.length
                  ? snapshot.speedSteps.map((s) => `↓${s}`).join(' → ')
                  : '—'}
              </strong>
            </div>
          </div>

          <div className="assist-progress">
            <div
              className="assist-progress__bar"
              style={{
                width: snapshot.routeLengthM
                  ? `${(snapshot.distanceAlongM / snapshot.routeLengthM) * 100}%`
                  : '0%',
              }}
            />
          </div>

          <div className="assist-actions">
            <button type="button" className="linkish" onClick={onReset}>
              {t.resetStart}
            </button>
            <button
              type="button"
              className="secondary-btn"
              onClick={() => {
                void (async () => {
                  try {
                    await pairBleDevice()
                    if (snapshot.payload) {
                      await sendAssistPayload(snapshot.payload, {
                        preferBluetooth: true,
                      })
                    }
                  } catch {
                    /* status shown below */
                  }
                })()
              }}
            >
              {t.pairBle}
            </button>
          </div>

          <p className="small muted assist-ble-status">
            {t.ble}: {ble.status}
            {ble.deviceName ? ` · ${ble.deviceName}` : ''}
            {ble.lastError ? ` · ${ble.lastError}` : ''}
          </p>
        </>
      ) : (
        <p className="small muted">{t.assistIdle}</p>
      )}

      {disabled ? null : (
        <p className="small muted assist-disclaimer">{t.assistDisclaimer}</p>
      )}
    </section>
  )
}
