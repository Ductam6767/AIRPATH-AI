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

export function isGenericPlaceLabel(label: string): boolean {
  const trimmed = label.trim()
  if (!trimmed) return true
  if (/^od_\d+\s+(origin|destination)$/i.test(trimmed)) return true
  if (/^(Origin|Destination)\s+\d+$/i.test(trimmed)) return true
  return false
}

function normalizePlaceLabel(label: string): string {
  return label.trim().toLocaleLowerCase('vi')
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

export function formatDistanceKm(meters: number): string {
  if (!Number.isFinite(meters) || meters <= 0) return '—'
  const km = meters / 1000
  const rounded = km < 10 ? Math.round(km * 10) / 10 : Math.round(km)
  return Number.isInteger(rounded) ? `${rounded} km` : `${rounded.toFixed(1)} km`
}

export type ProductRouteKind = 'fastest' | 'health' | 'balanced'

export function productRouteKind(route: RouteRecord): ProductRouteKind {
  if (route.is_fastest || route.route_type === 'fastest') {
    return 'fastest'
  }
  return isLowerPredictedExposure(route.predicted_exposure_reduction_percent)
    ? 'health'
    : 'balanced'
}

export function routeCardTitle(route: RouteRecord): string {
  if (route.tradeoff_slot === 'closer_to_fastest') {
    return 'Slightly slower · lower exposure'
  }
  if (route.tradeoff_slot === 'second_fastest') {
    return 'Second-fastest · lower exposure'
  }
  if (route.tradeoff_slot === 'near_time_limit') {
    return 'Near time limit · lower exposure'
  }
  const kind = productRouteKind(route)
  if (kind === 'fastest') return 'Fastest'
  if (kind === 'health') return 'Health-first'
  return 'Balanced'
}

export function isLowerPredictedExposure(percent: number): boolean {
  return percent > 0.5
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

export function pickRecommendedRoute(
  fastest: RouteRecord,
  alternatives: RouteRecord[],
): RouteRecord {
  const health = alternatives.filter((route) =>
    isLowerPredictedExposure(route.predicted_exposure_reduction_percent),
  )
  if (health.length === 0) return fastest
  return health.reduce((best, route) =>
    route.predicted_exposure_reduction_percent >
    best.predicted_exposure_reduction_percent
      ? route
      : best,
  )
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
  return matchDemoPair(scenarios, originKey, destinationKey)?.scenario.scenario_id ?? null
}

export function scenarioOriginKey(scenario: Scenario): string {
  return placeKey(scenario.origin.latitude, scenario.origin.longitude)
}

export function scenarioDestKey(scenario: Scenario): string {
  return placeKey(scenario.destination.latitude, scenario.destination.longitude)
}

export function placeKey(lat: number, lon: number): string {
  return `${lat.toFixed(6)},${lon.toFixed(6)}`
}

export function parsePlaceKey(
  key: string,
): { latitude: number; longitude: number } | null {
  const [latRaw, lonRaw] = key.split(',')
  const latitude = Number(latRaw)
  const longitude = Number(lonRaw)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return { latitude, longitude }
}

export function matchDemoPair(
  scenarios: Scenario[],
  fromKey: string,
  toKey: string,
): { scenario: Scenario; reversed: boolean } | null {
  if (!fromKey || !toKey || fromKey === toKey) return null
  for (const scenario of scenarios) {
    const origin = scenarioOriginKey(scenario)
    const dest = scenarioDestKey(scenario)
    if (origin === fromKey && dest === toKey) {
      return { scenario, reversed: false }
    }
    if (origin === toKey && dest === fromKey) {
      return { scenario, reversed: true }
    }
  }
  return null
}

export function tripsKeepingFrom(
  scenarios: Scenario[],
  fromKey: string,
): { toKey: string; toLabel: string }[] {
  if (!fromKey) return []
  const seen = new Set<string>()
  const trips: { toKey: string; toLabel: string }[] = []
  for (const scenario of scenarios) {
    const origin = scenarioOriginKey(scenario)
    const dest = scenarioDestKey(scenario)
    if (origin === fromKey && !seen.has(dest)) {
      seen.add(dest)
      trips.push({ toKey: dest, toLabel: destinationLabel(scenario) })
    }
    if (dest === fromKey && !seen.has(origin)) {
      seen.add(origin)
      trips.push({ toKey: origin, toLabel: originLabel(scenario) })
    }
  }
  return trips
}

export function tripsKeepingTo(
  scenarios: Scenario[],
  toKey: string,
): { fromKey: string; fromLabel: string }[] {
  if (!toKey) return []
  const seen = new Set<string>()
  const trips: { fromKey: string; fromLabel: string }[] = []
  for (const scenario of scenarios) {
    const origin = scenarioOriginKey(scenario)
    const dest = scenarioDestKey(scenario)
    if (dest === toKey && !seen.has(origin)) {
      seen.add(origin)
      trips.push({ fromKey: origin, fromLabel: originLabel(scenario) })
    }
    if (origin === toKey && !seen.has(dest)) {
      seen.add(dest)
      trips.push({ fromKey: dest, fromLabel: destinationLabel(scenario) })
    }
  }
  return trips
}

export function scenarioForRequestedEnds(
  scenarios: Scenario[],
  fromKey: string,
  toKey: string,
): Scenario | null {
  const match = matchDemoPair(scenarios, fromKey, toKey)
  if (!match) return null
  if (!match.reversed) return match.scenario
  return {
    ...match.scenario,
    origin: match.scenario.destination,
    destination: match.scenario.origin,
  }
}

export function uniquePlaces(scenarios: Scenario[]): {
  key: string
  label: string
  secondary: string
}[] {
  const map = new Map<
    string,
    { key: string; label: string; secondary: string }
  >()
  const labelToKey = new Map<string, string>()

  const upsert = (key: string, label: string, lat: number, lon: number) => {
    if (isGenericPlaceLabel(label)) return

    const normalized = normalizePlaceLabel(label)
    const existingKey = labelToKey.get(normalized)
    if (existingKey && existingKey !== key) {
      return
    }

    const existing = map.get(key)
    if (!existing) {
      map.set(key, {
        key,
        label,
        secondary: formatCoord(lat, lon),
      })
      labelToKey.set(normalized, key)
      return
    }
    if (isGenericPlaceLabel(existing.label) && !isGenericPlaceLabel(label)) {
      labelToKey.delete(normalizePlaceLabel(existing.label))
      existing.label = label
      labelToKey.set(normalized, key)
    }
  }

  for (const scenario of scenarios) {
    upsert(
      scenarioOriginKey(scenario),
      originLabel(scenario),
      scenario.origin.latitude,
      scenario.origin.longitude,
    )
    upsert(
      scenarioDestKey(scenario),
      destinationLabel(scenario),
      scenario.destination.latitude,
      scenario.destination.longitude,
    )
  }
  return [...map.values()].sort((a, b) =>
    a.label.localeCompare(b.label, 'vi', { sensitivity: 'base' }),
  )
}

export function lookupPlace(
  scenarios: Scenario[],
  key: string,
): { label: string; latitude: number; longitude: number } | null {
  if (!key) return null
  const parsed = parsePlaceKey(key)
  const place = uniquePlaces(scenarios).find((item) => item.key === key)
  if (!parsed || !place) return null
  return {
    label: place.label,
    latitude: parsed.latitude,
    longitude: parsed.longitude,
  }
}

export function placesCompatibleWith(
  scenarios: Scenario[],
  otherKey: string,
  as: 'from' | 'to',
): { key: string; label: string; secondary: string }[] {
  const places = uniquePlaces(scenarios)
  if (!otherKey) return places
  return places.filter((place) =>
    as === 'from'
      ? matchDemoPair(scenarios, place.key, otherKey) != null
      : matchDemoPair(scenarios, otherKey, place.key) != null,
  )
}

export function soleCompatiblePlace(
  scenarios: Scenario[],
  otherKey: string,
  as: 'from' | 'to',
): { key: string; label: string; secondary: string } | null {
  if (!otherKey) return null
  const places = placesCompatibleWith(scenarios, otherKey, as)
  return places.length === 1 ? places[0] : null
}

function sortPlaces<T extends { label: string }>(places: T[]): T[] {
  return [...places].sort((a, b) =>
    a.label.localeCompare(b.label, 'vi', { sensitivity: 'base' }),
  )
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
  return sortPlaces([...map.values()])
}

export function uniqueDestinations(scenarios: Scenario[]): {
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
    const key = scenarioDestKey(scenario)
    const existing = map.get(key)
    if (existing) {
      existing.scenarioIds.push(scenario.scenario_id)
    } else {
      map.set(key, {
        key,
        label: destinationLabel(scenario),
        secondary: formatCoord(
          scenario.destination.latitude,
          scenario.destination.longitude,
        ),
        scenarioIds: [scenario.scenario_id],
      })
    }
  }
  return sortPlaces([...map.values()])
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

export function originsForDestination(
  scenarios: Scenario[],
  destKey: string,
): { key: string; label: string; secondary: string; scenarioId: string }[] {
  return scenarios
    .filter((s) => scenarioDestKey(s) === destKey)
    .map((s) => ({
      key: scenarioOriginKey(s),
      label: originLabel(s),
      secondary: formatCoord(s.origin.latitude, s.origin.longitude),
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

export function reverseRouteGeometry(route: RouteRecord): RouteRecord {
  return {
    ...route,
    geometry: [...safeGeometry(route.geometry)].reverse(),
  }
}

export function friendlyApiError(err: unknown): string {
  const fallback = 'Unable to load this request. Please try again.'
  if (!err || typeof err !== 'object') return fallback
  const code = 'code' in err ? String(err.code) : ''
  const message = 'message' in err ? String(err.message) : fallback
  if (code === 'api_unavailable') {
    return 'The demo API is unavailable. Start the backend on port 8000 and refresh.'
  }
  if (code === 'unknown_scenario_id' || code === 'unknown_endpoint_pair') {
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
