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

export function originLabel(scenario: Scenario): string {
  const label = scenario.origin.label?.trim()
  if (label && !/^od_\d+\s+origin$/i.test(label)) {
    return label
  }
  return `Origin · ${formatCoord(scenario.origin.latitude, scenario.origin.longitude)}`
}

export function destinationLabel(scenario: Scenario): string {
  const label = scenario.destination.label?.trim()
  if (label && !/^od_\d+\s+destination$/i.test(label)) {
    return label
  }
  return `Destination · ${formatCoord(scenario.destination.latitude, scenario.destination.longitude)}`
}

export function scenarioPairLabel(scenario: Scenario): string {
  return `${originLabel(scenario)} → ${destinationLabel(scenario)}`
}

export function routeCardTitle(route: RouteRecord): string {
  if (route.is_fastest || route.route_type === 'fastest') {
    return 'Fastest route'
  }
  return `Exposure-aware option ${route.rank}`
}

export function reductionBadgeText(percent: number): string | null {
  if (percent > 0.5) {
    return `${Math.round(percent)}% lower predicted exposure`
  }
  if (percent < -0.5) {
    return `${Math.round(Math.abs(percent))}% higher predicted exposure`
  }
  return 'Similar predicted exposure'
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
  scenarioIds: string[]
}[] {
  const map = new Map<string, { key: string; label: string; scenarioIds: string[] }>()
  for (const scenario of scenarios) {
    const key = scenarioOriginKey(scenario)
    const existing = map.get(key)
    if (existing) {
      existing.scenarioIds.push(scenario.scenario_id)
    } else {
      map.set(key, {
        key,
        label: originLabel(scenario),
        scenarioIds: [scenario.scenario_id],
      })
    }
  }
  return [...map.values()]
}

export function destinationsForOrigin(
  scenarios: Scenario[],
  originKey: string,
): { key: string; label: string; scenarioId: string }[] {
  return scenarios
    .filter((s) => scenarioOriginKey(s) === originKey)
    .map((s) => ({
      key: scenarioDestKey(s),
      label: destinationLabel(s),
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
