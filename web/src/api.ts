import type {
  ApiErrorBody,
  Gap1Exhibit,
  RoutesResponse,
  ScenariosResponse,
  TravelMode,
} from './types'
import { API_BASE } from './constants'

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

export async function fetchScenarios(
  signal?: AbortSignal,
): Promise<ScenariosResponse> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/demo/scenarios`, { signal })
  } catch {
    throw new DemoApiError(
      'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
      0,
      'api_unavailable',
    )
  }
  if (!response.ok) {
    throw await parseError(response)
  }
  return (await response.json()) as ScenariosResponse
}

export async function fetchGap1Exhibit(
  signal?: AbortSignal,
): Promise<Gap1Exhibit> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/research/gap1`, { signal })
  } catch {
    throw new DemoApiError(
      'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
      0,
      'api_unavailable',
    )
  }
  if (!response.ok) {
    throw await parseError(response)
  }
  return (await response.json()) as Gap1Exhibit
}

export async function fetchRoutes(
  params: {
    scenarioId: string
    mode: TravelMode
    deltaMinutes: number
  },
  signal?: AbortSignal,
): Promise<RoutesResponse> {
  const query = new URLSearchParams({
    scenario_id: params.scenarioId,
    mode: params.mode,
    delta_minutes: String(params.deltaMinutes),
  })
  let response: Response
  try {
    response = await fetch(`${API_BASE}/demo/routes?${query.toString()}`, {
      signal,
    })
  } catch {
    throw new DemoApiError(
      'Cannot reach the AIRPATH demo API. Start the FastAPI backend on port 8000.',
      0,
      'api_unavailable',
    )
  }
  if (!response.ok) {
    throw await parseError(response)
  }
  return (await response.json()) as RoutesResponse
}
