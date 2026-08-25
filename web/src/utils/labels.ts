import type { RouteRecord, Scenario } from '../types'

export function formatMinutes(value: number): string {
  const rounded = Math.round(value * 10) / 10
  return Number.isInteger(rounded) ? `${rounded}` : rounded.toFixed(1)
}

export function formatExposure(value: number): string {
  return Math.round(value).toLocaleString()
}

export function formatCoord(lat: number, lon: number): string {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`
}

export function scenarioNumber(scenarioId: string): string {
  const match = scenarioId.match(/(\d+)\s*$/)
  return match ? match[1].padStart(2, '0') : scenarioId
}

function isGenericEndpointLabel(label: string, kind: 'origin' | 'destination'): boolean {
  const pattern =
    kind === 'origin' ? /^od_\d+\s+origin$/i : /^od_\d+\s+destination$/i
  return pattern.test(label)
}

export function originLabel(scenario: Scenario): string {
  const label = scenario.origin.label?.trim()
  if (label && !isGenericEndpointLabel(label, 'origin')) {
    return label
  }
  return `Origin ${scenarioNumber(scenario.scenario_id)}`
}

export function destinationLabel(scenario: Scenario): string {
  const label = scenario.destination.label?.trim()
  if (label && !isGenericEndpointLabel(label, 'destination')) {
    return label
  }
  return `Destination ${scenarioNumber(scenario.scenario_id)}`
}

export function scenarioPairLabel(scenario: Scenario): string {
  return `${originLabel(scenario)} → ${destinationLabel(scenario)}`
}

export function routeCardTitle(route: RouteRecord): string {
  if (route.is_fastest || route.route_type === 'fastest') {
    return 'Fastest'
  }
  return `AIRPATH alternative ${route.rank}`
}

export function isLowerPredictedExposure(percent: number): boolean {
  return percent > 0.5
}

export function isAlsoLowestExposureRoute(
  fastest: RouteRecord,
  alternatives: RouteRecord[],
): boolean {
  if (fastest.is_also_lowest_exposure) return true
  return alternatives.length === 0
}

export function routeKindLabel(route: RouteRecord): string {
  if (route.is_fastest || route.route_type === 'fastest') {
    return 'Fastest'
  }
  if (route.tradeoff_slot === 'closer_to_fastest') {
    return 'Slightly slower · lower exposure'
  }
  if (route.tradeoff_slot === 'second_fastest') {
    return 'Second-fastest · lower exposure'
  }
  if (route.tradeoff_slot === 'near_time_limit') {
    return 'Near time limit · lower exposure'
  }
  return isLowerPredictedExposure(route.predicted_exposure_reduction_percent)
    ? 'Lower predicted exposure'
    : 'Feasible alternative'
}

export function reductionBadgeText(percent: number): string | null {
  if (isLowerPredictedExposure(percent)) {
    return `${Math.round(percent)}% lower predicted exposure`
  }
  if (percent < -0.5) {
    return `+${Math.round(Math.abs(percent))}% higher predicted exposure`
  }
  return 'Similar predicted exposure'
}

export function hasLowerPredictedExposureAlternative(
  alternatives: RouteRecord[],
): boolean {
  return alternatives.some((route) =>
    isLowerPredictedExposure(route.predicted_exposure_reduction_percent),
  )
}

export function findScenarioId(
  scenarios: Scenario[],
  originKey: string,
  destinationKey: string,
): string | null {
  const match = scenarios.find(
    (s) => scenarioOriginKey(s) === originKey && scenarioDestKey(s) === destinationKey,
  )
  return match?.scenario_id ?? null
}

export function scenarioOriginKey(scenario: Scenario): string {
  return `${scenario.origin.latitude.toFixed(6)},${scenario.origin.longitude.toFixed(6)}`
}

export function scenarioDestKey(scenario: Scenario): string {
  return `${scenario.destination.latitude.toFixed(6)},${scenario.destination.longitude.toFixed(6)}`
}

export function uniqueOrigins(scenarios: Scenario[]): {
  key: string
  label: string
  secondary: string
  scenarioIds: string[]
}[] {
  const map = new Map<
    string,
    { key: string; label: string; secondary: string; scenarioIds: string[] }
  >()
  for (const scenario of scenarios) {
    const key = scenarioOriginKey(scenario)
    const existing = map.get(key)
    if (existing) {
      existing.scenarioIds.push(scenario.scenario_id)
    } else {
      map.set(key, {
        key,
        label: originLabel(scenario),
        secondary: formatCoord(scenario.origin.latitude, scenario.origin.longitude),
        scenarioIds: [scenario.scenario_id],
      })
    }
  }
  return [...map.values()]
}

export function destinationsForOrigin(
  scenarios: Scenario[],
  originKey: string,
): { key: string; label: string; secondary: string; scenarioId: string }[] {
  return scenarios
    .filter((s) => scenarioOriginKey(s) === originKey)
    .map((s) => ({
      key: scenarioDestKey(s),
      label: destinationLabel(s),
      secondary: formatCoord(s.destination.latitude, s.destination.longitude),
      scenarioId: s.scenario_id,
    }))
}

export function safeGeometry(
  geometry: RouteRecord['geometry'] | undefined,
): [number, number][] {
  if (!Array.isArray(geometry)) return []
  return geometry.filter(
    (point): point is [number, number] =>
      Array.isArray(point) &&
      point.length === 2 &&
      Number.isFinite(point[0]) &&
      Number.isFinite(point[1]),
  )
}

export function friendlyApiError(err: unknown): string {
  const fallback = 'Unable to load this request. Please try again.'
  if (!err || typeof err !== 'object') return fallback
  const code = 'code' in err ? String(err.code) : ''
  const message = 'message' in err ? String(err.message) : fallback
  if (code === 'api_unavailable') {
    return 'The demo API is unavailable. Start the backend on port 8000 and refresh.'
  }
  if (code === 'unknown_scenario_id') {
    return 'That origin and destination pair is not in the demo dataset.'
  }
  if (code === 'unsupported_mode') {
    return 'That travel mode is not available for this demo trip.'
  }
  if (code === 'unsupported_delta_minutes') {
    return 'That extra-time value is not supported. Use 0, 1, 2, 3, 5, or 10 minutes.'
  }
  if (code === 'route_request_outside_demo_dataset') {
    return 'No precomputed route is available for this combination.'
  }
  return message || fallback
}
