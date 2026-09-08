import type {
  ApiErrorBody,
  Gap1Exhibit,
  RoutesResponse,
  ScenariosResponse,
  TimeWindow,
  TravelMode,
} from './types'
import { API_BASE, IS_MOBILE_BUILD } from './constants'
import { localFetchRoutes, localFetchScenarios } from './offline/localDemo'

export type DemoDataSource = 'api' | 'bundled'

let lastDataSource: DemoDataSource = 'api'
let preferBundled = false

export function getDemoDataSource(): DemoDataSource {
  return lastDataSource
}

export class DemoApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'DemoApiError'
    this.status = status
    this.code = code
  }
}

async function parseError(response: Response): Promise<DemoApiError> {
  let message = `Request failed (${response.status})`
  let code: string | undefined
  try {
    const body = (await response.json()) as ApiErrorBody
    if (typeof body.detail === 'string') {
      message = body.detail
    } else if (body.detail && typeof body.detail === 'object') {
      message = body.detail.message ?? message
      code = body.detail.error
    }
  } catch {
    // keep default message
  }
  return new DemoApiError(message, response.status, code)
}

function withTimeout(signal: AbortSignal | undefined, ms: number): AbortSignal {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), ms)
  const onAbort = () => {
    clearTimeout(timer)
    controller.abort()
  }
  signal?.addEventListener('abort', onAbort)
  controller.signal.addEventListener('abort', () => {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  })
  return controller.signal
}

async function fetchLiveScenarios(signal?: AbortSignal): Promise<ScenariosResponse> {
  const response = await fetch(`${API_BASE}/demo/scenarios`, {
    signal: withTimeout(signal, 6000),
  })
  if (!response.ok) {
    throw await parseError(response)
  }
  return (await response.json()) as ScenariosResponse
}

async function fetchLiveRoutes(
  params: {
    scenarioId?: string
    fromLatitude?: number
    fromLongitude?: number
    toLatitude?: number
    toLongitude?: number
    mode: TravelMode
    deltaMinutes: number
    timeWindow?: TimeWindow | string
  },
  signal?: AbortSignal,
): Promise<RoutesResponse> {
  const query = new URLSearchParams({
    mode: params.mode,
    delta_minutes: String(params.deltaMinutes),
    time_window: params.timeWindow ?? 'morning_peak',
  })
  if (
    params.fromLatitude != null &&
    params.fromLongitude != null &&
    params.toLatitude != null &&
    params.toLongitude != null
  ) {
    query.set('from_latitude', String(params.fromLatitude))
    query.set('from_longitude', String(params.fromLongitude))
    query.set('to_latitude', String(params.toLatitude))
    query.set('to_longitude', String(params.toLongitude))
  } else if (params.scenarioId) {
    query.set('scenario_id', params.scenarioId)
  }
  const response = await fetch(`${API_BASE}/demo/routes?${query.toString()}`, {
    signal: withTimeout(signal, 8000),
  })
  if (!response.ok) {
    throw await parseError(response)
  }
  return (await response.json()) as RoutesResponse
}

export async function fetchGap1Exhibit(
  signal?: AbortSignal,
): Promise<Gap1Exhibit> {
  const response = await fetch(`${API_BASE}/research/gap1`, {
    signal: withTimeout(signal, 8000),
  })
  if (!response.ok) {
    throw await parseError(response)
  }
  return (await response.json()) as Gap1Exhibit
}

export async function fetchScenarios(
  signal?: AbortSignal,
): Promise<ScenariosResponse> {
  try {
    const live = await fetchLiveScenarios(signal)
    preferBundled = false
    lastDataSource = 'api'
    return live
  } catch (err) {
    if (signal?.aborted) throw err
    if (!IS_MOBILE_BUILD) {
      throw err instanceof DemoApiError
        ? err
        : new DemoApiError(
            'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
            0,
            'api_unavailable',
          )
    }
    try {
      const bundled = await localFetchScenarios()
      preferBundled = true
      lastDataSource = 'bundled'
      return bundled
    } catch {
      throw new DemoApiError(
        'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
        0,
        'api_unavailable',
      )
    }
  }
}

export async function fetchRoutes(
  params: {
    scenarioId?: string
    fromLatitude?: number
    fromLongitude?: number
    toLatitude?: number
    toLongitude?: number
    mode: TravelMode
    deltaMinutes: number
    timeWindow?: TimeWindow | string
  },
  signal?: AbortSignal,
): Promise<RoutesResponse> {
  if (preferBundled && IS_MOBILE_BUILD) {
    try {
      const bundled = await localFetchRoutes(params)
      lastDataSource = 'bundled'
      return bundled
    } catch {
      throw new DemoApiError(
        'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
        0,
        'api_unavailable',
      )
    }
  }
  try {
    const live = await fetchLiveRoutes(params, signal)
    lastDataSource = 'api'
    return live
  } catch (err) {
    if (signal?.aborted) throw err
    if (!IS_MOBILE_BUILD) {
      throw err instanceof DemoApiError
        ? err
        : new DemoApiError(
            'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
            0,
            'api_unavailable',
          )
    }
    try {
      const bundled = await localFetchRoutes(params)
      preferBundled = true
      lastDataSource = 'bundled'
      return bundled
    } catch {
      throw new DemoApiError(
        'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
        0,
        'api_unavailable',
      )
    }
  }
}
