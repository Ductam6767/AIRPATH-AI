export type TrialAssistant = 'C' | 'K'
export type TrialYesNo = 'yes' | 'no' | 'skip'

export interface TrialRow {
  id: string
  at: string
  assistant: TrialAssistant
  speed50: number | null
  speedMax: number | null
  blinkerOk: TrialYesNo
  notes: string
}

const STORAGE_KEY = 'airpath_trials_v1'

export function loadTrials(): TrialRow[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as TrialRow[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveTrials(rows: TrialRow[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rows))
}

export function trialsToCsv(rows: TrialRow[]): string {
  const header = [
    'id',
    'at',
    'assistant',
    'speed50_kmh',
    'speedMax_kmh',
    'blinker_ok',
    'notes',
  ]
  const lines = rows.map((r) =>
    [
      r.id,
      r.at,
      r.assistant,
      r.speed50 ?? '',
      r.speedMax ?? '',
      r.blinkerOk,
      `"${r.notes.replaceAll('"', '""')}"`,
    ].join(','),
  )
  return [header.join(','), ...lines].join('\n')
}

export interface TrialSummaryRow {
  assistant: TrialAssistant
  n: number
  mean50: number | null
  pctBlinker: number | null
  pctSlow: number | null
}

export function summarizeTrials(rows: TrialRow[]): TrialSummaryRow[] {
  return (['C', 'K'] as const).map((assistant) => {
    const group = rows.filter((r) => r.assistant === assistant)
    const speeds = group
      .map((r) => r.speed50)
      .filter((v): v is number => v != null && Number.isFinite(v))
    const blinker = group.filter((r) => r.blinkerOk !== 'skip')
    const blinkerOk = blinker.filter((r) => r.blinkerOk === 'yes')
    const slow = speeds.filter((v) => v <= 25)
    return {
      assistant,
      n: group.length,
      mean50:
        speeds.length === 0
          ? null
          : speeds.reduce((a, b) => a + b, 0) / speeds.length,
      pctBlinker:
        blinker.length === 0 ? null : (100 * blinkerOk.length) / blinker.length,
      pctSlow: speeds.length === 0 ? null : (100 * slow.length) / speeds.length,
    }
  })
}
