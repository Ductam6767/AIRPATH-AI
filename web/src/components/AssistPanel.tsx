import { useEffect, useState } from 'react'
import type { AssistSnapshot, AssistMode } from '../hooks/useAssistNavigation'
import {
  getBleTransportState,
  sendAssistPayload,
  subscribeBleTransport,
  type BleTransportState,
} from '../ble/bleTransport'

interface AssistPanelProps {
  snapshot: AssistSnapshot
  assistMode: AssistMode
  onAssistModeChange: (mode: AssistMode) => void
  onReset: () => void
}

function turnLabel(turn: AssistSnapshot['next']): string {
  if (!turn) return '—'
  if (turn.turn === 'left') return '↰ Left'
  if (turn.turn === 'right') return '↱ Right'
  if (turn.turn === 'arrive') return '◎ Arrive'
  return '↑ Continue'
}

export function AssistPanel({
  snapshot,
  assistMode,
  onAssistModeChange,
  onReset,
}: AssistPanelProps) {
  const [ble, setBle] = useState<BleTransportState>(() => getBleTransportState())

  useEffect(() => subscribeBleTransport(setBle), [])

  const disabled = !snapshot.active && assistMode === 'off'

  return (
    <section className="assist-panel" aria-label="Maneuver safety assistant">
      <div className="assist-panel__header">
        <h2>Safety assistant (demo)</h2>
        <p className="small muted">
          Syncs turn hint + speed steps to ESP32 via BLE (or simulated JSON). Not
          live Google Maps — uses the selected route polyline.
        </p>
      </div>

      <div className="assist-mode-row" role="radiogroup" aria-label="Assistant mode">
        {(
          [
            ['off', 'Off'],
            ['demo', 'Demo play'],
            ['live', 'GPS live'],
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
            <div className="assist-metric">
              <span className="assist-metric__label">Next maneuver</span>
              <strong className="assist-metric__value">{turnLabel(snapshot.next)}</strong>
            </div>
            <div className="assist-metric">
              <span className="assist-metric__label">Distance</span>
              <strong className="assist-metric__value">
                {Math.round(snapshot.distanceToNextM)} m
              </strong>
            </div>
            <div className="assist-metric">
              <span className="assist-metric__label">Target speed</span>
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
              Reset to route start
            </button>
            <button
              type="button"
              className="secondary-btn"
              disabled={!snapshot.payload}
              onClick={() => {
                if (snapshot.payload) {
                  void sendAssistPayload(snapshot.payload, { preferBluetooth: true })
                }
              }}
            >
              Pair BLE &amp; send
            </button>
          </div>

          <p className="small muted assist-ble-status">
            BLE: {ble.status}
            {ble.deviceName ? ` · ${ble.deviceName}` : ''}
            {ble.lastError ? ` · ${ble.lastError}` : ''}
          </p>
        </>
      ) : (
        <p className="small muted">
          Select a route, then enable Demo play or GPS live to preview maneuver
          sync for your ESP32 prototype.
        </p>
      )}

      {disabled ? null : (
        <p className="small muted assist-disclaimer">
          Assistant output is a pilot demo — not medical advice, not certified
          navigation. Driver/rider remains responsible.
        </p>
      )}
    </section>
  )
}
