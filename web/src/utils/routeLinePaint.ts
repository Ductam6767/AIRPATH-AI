import type { PathOptions } from 'leaflet'
import { COLORS } from '../constants'
import type { RouteRecord } from '../types'

export const ROUTE_CASING_COLOR = '#111111'

type RouteRole = 'selected' | 'fastest' | 'other'

function roleOf(route: RouteRecord, selectedRouteId: string | null): RouteRole {
  if (route.route_id === selectedRouteId) return 'selected'
  if (route.is_fastest) return 'fastest'
  return 'other'
}

/** Keep the coloured fill inside a typical OSM carriageway at street zoom. */
export function innerRouteWeight(
  zoom: number,
  role: RouteRole,
  followActive: boolean,
): number {
  const z = Math.max(11, Math.min(19, zoom))
  if (followActive) {
    if (z >= 17) return 4
    if (z >= 16) return 4.25
    return 5
  }
  if (role === 'selected') {
    if (z >= 16) return 4.25
    if (z >= 14) return 4.75
    return 5.25
  }
  if (role === 'fastest') {
    if (z >= 16) return 3.75
    if (z >= 14) return 4.25
    return 4.75
  }
  if (z >= 16) return 3
  if (z >= 14) return 3.4
  return 3.75
}

/** Black outline on both sides of the fill (~1.15px each edge). */
export function casingRouteWeight(inner: number): number {
  return inner + 2.3
}

export function routeLinePaint(
  route: RouteRecord,
  selectedRouteId: string | null,
  followActive: boolean,
  zoom: number,
): { fill: PathOptions; casing: PathOptions } {
  const role = roleOf(route, selectedRouteId)
  const inner = innerRouteWeight(zoom, role, followActive)
  const fillColor =
    role === 'selected' && !route.is_fastest
      ? COLORS.eco
      : role === 'other'
        ? COLORS.altMuted
        : COLORS.sky

  const fill: PathOptions = {
    color: fillColor,
    weight: inner,
    opacity: role === 'other' ? 0.78 : 0.96,
    lineCap: 'round',
    lineJoin: 'round',
  }
  const casing: PathOptions = {
    color: ROUTE_CASING_COLOR,
    weight: casingRouteWeight(inner),
    opacity: 0.92,
    lineCap: 'round',
    lineJoin: 'round',
    interactive: true,
  }
  return { fill, casing }
}
