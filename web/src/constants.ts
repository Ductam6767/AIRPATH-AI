export const DELTA_MINUTES = [0, 1, 2, 3, 5, 10] as const

export const COLORS = {
  navy: '#0B1F33',
  sky: '#3B82F6',
  eco: '#22C55E',
  softGreen: '#EAF7EF',
  offWhite: '#F7F6F1',
  text: '#172033',
  muted: '#6B7280',
  border: '#DDE3E8',
  altMuted: '#94A3B8',
} as const

export const EXPOSURE_NOTE =
  'Exposure is a model-estimated PM2.5 time-weighted proxy from hourly data, not a medical risk score.'

/** Empty in local Vite (proxy /demo and /health). Set VITE_API_URL in production. */
export function resolveApiBase(envUrl: string | undefined): string {
  const trimmed = envUrl?.trim()
  if (!trimmed) return ''
  return trimmed.replace(/\/+$/, '')
}

export const API_BASE = resolveApiBase(import.meta.env.VITE_API_URL)
