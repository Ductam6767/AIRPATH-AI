const EARTH_RADIUS_M = 6_371_000

/** Haversine distance in meters between [lat, lon] points. */
export function distanceM(a: [number, number], b: [number, number]): number {
  const [lat1, lon1] = a
  const [lat2, lon2] = b
  const φ1 = (lat1 * Math.PI) / 180
  const φ2 = (lat2 * Math.PI) / 180
  const Δφ = ((lat2 - lat1) * Math.PI) / 180
  const Δλ = ((lon2 - lon1) * Math.PI) / 180
  const h =
    Math.sin(Δφ / 2) ** 2 +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Initial bearing from a to b in degrees (-180..180). */
export function bearingDeg(a: [number, number], b: [number, number]): number {
  const [lat1, lon1] = a
  const [lat2, lon2] = b
  const φ1 = (lat1 * Math.PI) / 180
  const φ2 = (lat2 * Math.PI) / 180
  const Δλ = ((lon2 - lon1) * Math.PI) / 180
  const y = Math.sin(Δλ) * Math.cos(φ2)
  const x =
    Math.cos(φ1) * Math.sin(φ2) -
    Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ)
  return (Math.atan2(y, x) * 180) / Math.PI
}

/** Smallest signed angle difference in degrees. */
export function angleDiffDeg(from: number, to: number): number {
  let d = ((to - from + 540) % 360) - 180
  return d
}

/** Move heading toward a target bearing without crossing the ±180° cut. */
export function lerpHeadingDeg(from: number, to: number, t: number): number {
  const k = Math.min(1, Math.max(0, t))
  return from + angleDiffDeg(from, to) * k
}

/** Cumulative distance at each geometry vertex (meters). */
export function cumulativeDistances(geometry: [number, number][]): number[] {
  const out = [0]
  for (let i = 1; i < geometry.length; i += 1) {
    out.push(out[i - 1]! + distanceM(geometry[i - 1]!, geometry[i]!))
  }
  return out
}

/** Interpolate [lat, lon] at a distance along the polyline. */
export function pointAlongRoute(
  geometry: [number, number][],
  distanceAlongM: number,
): [number, number] | null {
  if (geometry.length === 0) return null
  if (geometry.length === 1 || distanceAlongM <= 0) return geometry[0]!
  const cum = cumulativeDistances(geometry)
  const max = cum[cum.length - 1] ?? 0
  if (distanceAlongM >= max) return geometry[geometry.length - 1]!
  for (let i = 1; i < cum.length; i += 1) {
    if (cum[i]! >= distanceAlongM) {
      const span = cum[i]! - cum[i - 1]!
      const t = span <= 0 ? 0 : (distanceAlongM - cum[i - 1]!) / span
      const a = geometry[i - 1]!
      const b = geometry[i]!
      return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    }
  }
  return geometry[geometry.length - 1]!
}

/** Distance along the polyline of the closest point to `target`. */
export function nearestDistanceAlongRoute(
  geometry: [number, number][],
  target: [number, number],
): number {
  if (geometry.length === 0) return 0
  if (geometry.length === 1) return 0
  const cum = cumulativeDistances(geometry)
  let bestDist = Number.POSITIVE_INFINITY
  let bestAlong = 0
  for (let i = 0; i < geometry.length - 1; i += 1) {
    const a = geometry[i]!
    const b = geometry[i + 1]!
    const span = cum[i + 1]! - cum[i]!
    if (span <= 0.05) {
      const d = distanceM(target, a)
      if (d < bestDist) {
        bestDist = d
        bestAlong = cum[i]!
      }
      continue
    }
    const abLat = b[0] - a[0]
    const abLng = b[1] - a[1]
    const apLat = target[0] - a[0]
    const apLng = target[1] - a[1]
    const ab2 = abLat * abLat + abLng * abLng
    const t = Math.min(1, Math.max(0, (apLat * abLat + apLng * abLng) / ab2))
    const proj: [number, number] = [a[0] + t * abLat, a[1] + t * abLng]
    const d = distanceM(target, proj)
    if (d < bestDist) {
      bestDist = d
      bestAlong = cum[i]! + t * span
    }
  }
  return bestAlong
}

/** Travel heading a short look-ahead from the current progress point. */
export function headingAlongRoute(
  geometry: [number, number][],
  distanceAlongM: number,
  lookaheadM = 55,
): number {
  const here = pointAlongRoute(geometry, distanceAlongM)
  const ahead = pointAlongRoute(geometry, distanceAlongM + lookaheadM)
  if (!here || !ahead) return 0
  if (
    Math.abs(ahead[0] - here[0]) < 1e-8 &&
    Math.abs(ahead[1] - here[1]) < 1e-8
  ) {
    return 0
  }
  return bearingDeg(here, ahead)
}

/** Upcoming polyline from the traveler through the next stretch of road. */
export function upcomingRouteSlice(
  geometry: [number, number][],
  distanceAlongM: number,
  lookaheadM: number,
): [number, number][] {
  const start = pointAlongRoute(geometry, distanceAlongM)
  if (!start) return []
  const end = pointAlongRoute(geometry, distanceAlongM + lookaheadM) ?? start
  const cum = cumulativeDistances(geometry)
  const from = Math.max(0, distanceAlongM)
  const to = from + Math.max(0, lookaheadM)
  const points: [number, number][] = [start]
  for (let i = 0; i < geometry.length; i += 1) {
    const at = cum[i] ?? 0
    if (at > from && at < to) {
      points.push(geometry[i]!)
    }
  }
  const last = points[points.length - 1]
  if (!last || last[0] !== end[0] || last[1] !== end[1]) {
    points.push(end)
  }
  return points
}
