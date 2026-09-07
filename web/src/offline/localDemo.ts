import type { RouteRecord, RoutesResponse, Scenario, ScenariosResponse } from '../types'

type RawPack = {
  scenarios: Scenario[]
  routes: Array<Record<string, unknown>>
  metadata: Record<string, unknown>
}

let packCache: RawPack | null = null

function asRecord(mod: unknown): Record<string, unknown> {
  if (mod && typeof mod === 'object' && 'default' in mod) {
    return (mod as { default: Record<string, unknown> }).default
  }
  return mod as Record<string, unknown>
}

async function loadPack(): Promise<RawPack> {
  if (packCache) return packCache
  const [scenariosMod, routesMod, metadataMod] = await Promise.all([
    import('@demo-pack/scenarios.json'),
    import('@demo-pack/routes.json'),
    import('@demo-pack/metadata.json'),
  ])
  const scenariosPayload = asRecord(scenariosMod)
  const routesPayload = asRecord(routesMod)
  const metadata = asRecord(metadataMod)
  const scenarios = scenariosPayload.scenarios
  const routes = routesPayload.routes
  if (!Array.isArray(scenarios) || scenarios.length === 0) {
    throw new Error('Bundled scenarios.json is empty.')
  }
  if (!Array.isArray(routes) || routes.length === 0) {
    throw new Error('Bundled routes.json is empty.')
  }
  packCache = {
    scenarios: scenarios as Scenario[],
    routes: routes as Array<Record<string, unknown>>,
    metadata,
  }
  return packCache
}

function toRoute(row: Record<string, unknown>): RouteRecord {
  return {
    route_id: String(row.route_id),
    route_type: String(row.route_type),
    rank: Number(row.rank),
    is_fastest: Boolean(row.is_fastest),
    is_feasible: row.is_feasible === undefined ? true : Boolean(row.is_feasible),
    travel_time_minutes: Number(row.travel_time_minutes),
    additional_time_vs_fastest_minutes: Number(
      row.additional_time_vs_fastest_minutes,
    ),
    predicted_exposure_index: Number(row.predicted_exposure_index),
    predicted_exposure_reduction_percent: Number(
      row.predicted_exposure_reduction_percent,
    ),
    distance_m: Number(row.distance_m),
    geometry: row.geometry as [number, number][],
    available_feasible_alternatives:
      row.available_feasible_alternatives == null
        ? null
        : Number(row.available_feasible_alternatives),
    fewer_than_requested_alternatives:
      row.fewer_than_requested_alternatives == null
        ? null
        : Boolean(row.fewer_than_requested_alternatives),
    research_warning:
      row.research_warning == null ? null : String(row.research_warning),
  }
}

function isFastest(row: Record<string, unknown>): boolean {
  return Boolean(row.is_fastest) || String(row.route_type) === 'fastest'
}

export async function localFetchScenarios(): Promise<ScenariosResponse> {
  const pack = await loadPack()
  return { scenarios: pack.scenarios }
}

export async function localFetchRoutes(params: {
  scenarioId: string
  mode: string
  deltaMinutes: number
}): Promise<RoutesResponse> {
  const pack = await loadPack()
  const scenario = pack.scenarios.find((s) => s.scenario_id === params.scenarioId)
  if (!scenario) {
    throw new Error(`Unknown scenario_id '${params.scenarioId}'.`)
  }
  const mode = params.mode.trim().toLowerCase()
  const matchedDelta = scenario.supported_delta_minutes.find(
    (d) => Math.abs(Number(d) - params.deltaMinutes) < 1e-9,
  )
  if (matchedDelta === undefined) {
    throw new Error(`Unsupported delta_minutes=${params.deltaMinutes}.`)
  }
  const group = pack.routes.filter(
    (row) =>
      String(row.scenario_id) === params.scenarioId &&
      String(row.mode).toLowerCase() === mode &&
      Math.abs(Number(row.delta_minutes) - Number(matchedDelta)) < 1e-9,
  )
  group.sort(
    (a, b) => Number(a.rank) - Number(b.rank) || String(a.route_id).localeCompare(String(b.route_id)),
  )
  const fastestRaw = group.find(isFastest)
  if (!fastestRaw) {
    throw new Error(
      `No frozen demo routes for ${params.scenarioId}/${mode}/${matchedDelta}.`,
    )
  }
  const alternativesRaw = group.filter((row) => !isFastest(row))
  const metadata = {
    ...pack.metadata,
    available_feasible_alternatives: fastestRaw.available_feasible_alternatives,
    fewer_than_requested_alternatives: fastestRaw.fewer_than_requested_alternatives,
    alternative_count: alternativesRaw.length,
    empty_alternatives_message: alternativesRaw.length
      ? null
      : 'No lower-exposure alternative fits your current time limit. Try allowing a few more minutes.',
    data_source: 'bundled_demo_pack',
  }
  return {
    scenario_id: params.scenarioId,
    mode,
    delta_minutes: Number(matchedDelta),
    fastest_route: toRoute(fastestRaw),
    alternatives: alternativesRaw.map(toRoute),
    metadata,
  }
}
