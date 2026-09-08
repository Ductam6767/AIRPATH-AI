export const DELTA_MINUTES = [0, 1, 2, 3, 5, 10] as const
export const TIME_WINDOWS = [
  { id: 'morning_peak', label: 'Morning peak' },
  { id: 'midday', label: 'Midday' },
  { id: 'evening_peak', label: 'Evening peak' },
] as const

export const IS_MOBILE_BUILD = import.meta.env.MODE === 'mobile'

export const COLORS = {
  navy: '#121826',
  sky: '#2563EB',
  eco: '#0F766E',
  softGreen: '#E7F3F0',
  offWhite: '#F5F4F1',
  text: '#121826',
  muted: '#5C6570',
  border: '#E2E0DA',
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
