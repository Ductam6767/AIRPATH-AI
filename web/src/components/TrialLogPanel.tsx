import { useState } from 'react'
import { useI18n } from '../i18n/LanguageContext'
import {
  loadTrials,
  saveTrials,
  summarizeTrials,
  trialsToCsv,
  type TrialAssistant,
  type TrialRow,
  type TrialYesNo,
} from '../offline/trials'

function parseOptionalNumber(raw: string): number | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  const n = Number(trimmed)
  return Number.isFinite(n) ? n : null
}

export function TrialLogPanel() {
  const { t } = useI18n()
  const [rows, setRows] = useState<TrialRow[]>(() => loadTrials())
  const [assistant, setAssistant] = useState<TrialAssistant>('C')
  const [speed50, setSpeed50] = useState('')
  const [speedMax, setSpeedMax] = useState('')
  const [blinkerOk, setBlinkerOk] = useState<TrialYesNo>('yes')
  const [notes, setNotes] = useState('')

  const persist = (next: TrialRow[]) => {
    setRows(next)
    saveTrials(next)
  }

  const summary = summarizeTrials(rows)

  return (
    <section className="trial-panel" aria-label={t.trialsTitle}>
      <div className="trial-panel__header">
        <h2>{t.trialsTitle}</h2>
        <p className="small muted">{t.trialsIntro}</p>
      </div>

      <form
        className="trial-form"
        onSubmit={(event) => {
          event.preventDefault()
          const row: TrialRow = {
            id: `t${Date.now()}`,
            at: new Date().toISOString(),
            assistant,
            speed50: parseOptionalNumber(speed50),
            speedMax: parseOptionalNumber(speedMax),
            blinkerOk,
            notes: notes.trim(),
          }
          persist([row, ...rows])
          setNotes('')
        }}
      >
        <fieldset className="trial-form__row">
          <legend className="visually-hidden">{t.assistantOn}</legend>
          <label className="trial-radio">
            <input
              type="radio"
              name="assistant"
              checked={assistant === 'C'}
              onChange={() => setAssistant('C')}
            />
            {t.assistantOn}
          </label>
          <label className="trial-radio">
            <input
              type="radio"
              name="assistant"
              checked={assistant === 'K'}
              onChange={() => setAssistant('K')}
            />
            {t.assistantOff}
          </label>
        </fieldset>
        <label className="field">
          <span>{t.speed50}</span>
          <input
            inputMode="decimal"
            value={speed50}
            onChange={(e) => setSpeed50(e.target.value)}
          />
        </label>
        <label className="field">
          <span>{t.speedMax}</span>
          <input
            inputMode="decimal"
            value={speedMax}
            onChange={(e) => setSpeedMax(e.target.value)}
          />
        </label>
        <label className="field">
          <span>{t.blinkerOk}</span>
          <select
            value={blinkerOk}
            onChange={(e) => setBlinkerOk(e.target.value as TrialYesNo)}
          >
            <option value="yes">{t.yes}</option>
            <option value="no">{t.no}</option>
            <option value="skip">{t.skip}</option>
          </select>
        </label>
        <label className="field">
          <span>{t.notes}</span>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button type="submit" className="secondary-btn">
          {t.addTrial}
        </button>
      </form>

      {rows.length === 0 ? (
        <p className="small muted">{t.trialsEmpty}</p>
      ) : (
        <>
          <table className="trial-summary">
            <thead>
              <tr>
                <th />
                <th>{t.nRuns}</th>
                <th>{t.mean50}</th>
                <th>{t.pctBlinker}</th>
                <th>{t.pctSlow}</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((s) => (
                <tr key={s.assistant}>
                  <th>{s.assistant === 'C' ? t.summaryOn : t.summaryOff}</th>
                  <td>{s.n}</td>
                  <td>{s.mean50 == null ? '—' : s.mean50.toFixed(1)}</td>
                  <td>{s.pctBlinker == null ? '—' : `${s.pctBlinker.toFixed(0)}%`}</td>
                  <td>{s.pctSlow == null ? '—' : `${s.pctSlow.toFixed(0)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="assist-actions">
            <button
              type="button"
              className="secondary-btn"
              onClick={() => {
                const blob = new Blob([trialsToCsv(rows)], {
                  type: 'text/csv;charset=utf-8',
                })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'airpath_n_luot.csv'
                a.click()
                URL.revokeObjectURL(url)
              }}
            >
              {t.exportCsv}
            </button>
            <button
              type="button"
              className="linkish"
              onClick={() => persist([])}
            >
              {t.clearTrials}
            </button>
          </div>
        </>
      )}
    </section>
  )
}
