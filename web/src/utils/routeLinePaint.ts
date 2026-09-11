import type { PathOptions } from 'leaflet'
import { COLORS } from '../constants'
import type { RouteRecord } from '../types'

export const ROUTE_CASING_COLOR = '#111111'

/** Must match the follow-camera world transform in RouteMap. */
export const FOLLOW_MAP_SCALE = 1.58

type RouteRole = 'selected' | 'fastest' | 'other'

function roleOf(route: RouteRecord, selectedRouteId: string | null): RouteRole {
  if (route.route_id === selectedRouteId) return 'selected'
  if (route.is_fastest) return 'fastest'
  return 'other'
}

function screenPx(px: number, followActive: boolean): number {
  return followActive ? px / FOLLOW_MAP_SCALE : px
}

/** Coloured fill in screen pixels, then shrunk in follow mode so CSS scale does not flood the OSM carriageway. */
export function innerRouteWeight(
  zoom: number,
  role: RouteRole,
  followActive: boolean,
): number {
  const z = Math.max(11, Math.min(19, zoom))
  if (followActive) {
    if (z >= 17) return screenPx(3.15, true)
    if (z >= 16) return screenPx(3.45, true)
    return screenPx(3.8, true)
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

/** Black outline on both sides. Extra is in screen pixels (~1px each edge). */
export function casingRouteWeight(inner: number, followActive = false): number {
  const extra = followActive ? screenPx(2, true) : 2.3
  return inner + extra
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
    weight: casingRouteWeight(inner, followActive),
    opacity: 0.95,
    lineCap: 'round',
    lineJoin: 'round',
    interactive: true,
  }
  return { fill, casing }
}
