import { describe, expect, it } from 'vitest'
import {
  cumulativeDistances,
  distanceM,
  pointAlongRoute,
  upcomingRouteSlice,
} from '../maneuver/geo'
import { extractManeuvers, distanceToManeuver } from '../maneuver/extractManeuvers'
import { suggestedSpeedKmh } from '../maneuver/speedProfile'

describe('maneuver geo', () => {
  it('computes positive distance between HCMC points', () => {
    const a: [number, number] = [10.799, 106.661]
    const b: [number, number] = [10.798, 106.662]
    expect(distanceM(a, b)).toBeGreaterThan(50)
    expect(distanceM(a, b)).toBeLessThan(200)
  })

  it('builds cumulative distances along polyline', () => {
    const geom: [number, number][] = [
      [10.799, 106.661],
      [10.798, 106.662],
      [10.797, 106.663],
    ]
    const cum = cumulativeDistances(geom)
    expect(cum[0]).toBe(0)
    expect(cum[2]).toBeGreaterThan(cum[1]!)
  })

  it('slices the upcoming path from the traveler for follow-camera bounds', () => {
    const geom: [number, number][] = [
      [10.799, 106.661],
      [10.798, 106.662],
      [10.797, 106.663],
      [10.796, 106.664],
    ]
    const start = pointAlongRoute(geom, 0)
    const slice = upcomingRouteSlice(geom, 0, 80)
    expect(start).toEqual(geom[0])
    expect(slice[0]).toEqual(geom[0])
    expect(slice.length).toBeGreaterThan(1)
    expect(slice[slice.length - 1]).not.toEqual(geom[0])
  })
})

describe('extractManeuvers', () => {
  it('adds arrive maneuver at route end', () => {
    const geom: [number, number][] = [
      [10.799, 106.661],
      [10.7995, 106.6615],
      [10.8, 106.662],
      [10.8005, 106.6625],
    ]
    const m = extractManeuvers(geom)
    expect(m.length).toBeGreaterThanOrEqual(1)
    expect(m[m.length - 1]?.turn).toBe('arrive')
  })
})

describe('speedProfile', () => {
  it('steps speed down as distance to maneuver shrinks', () => {
    expect(suggestedSpeedKmh(350)).toBe(45)
    expect(suggestedSpeedKmh(250)).toBe(40)
    expect(suggestedSpeedKmh(150)).toBe(30)
    expect(suggestedSpeedKmh(80)).toBe(25)
    expect(suggestedSpeedKmh(30)).toBe(20)
  })
})

describe('distanceToManeuver', () => {
  it('returns remaining meters along route', () => {
    const m = {
      id: 'm0',
      index: 0,
      distanceFromStartM: 120,
      turn: 'left' as const,
      instruction: 'turn',
      lat: 10,
      lon: 106,
    }
    expect(distanceToManeuver(m, 70)).toBe(50)
  })
})
