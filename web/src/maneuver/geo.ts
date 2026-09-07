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
