import { describe, expect, it } from 'vitest'
import {
  angleDiffDeg,
  bearingDeg,
  cumulativeDistances,
  distanceM,
  lerpHeadingDeg,
  pointAlongRoute,
  upcomingRouteSlice,
} from '../maneuver/geo'
import {
  classifyTurn,
  extractManeuvers,
  distanceToManeuver,
  lastPassedTurn,
} from '../maneuver/extractManeuvers'
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
  it('uses navigation bearings: north then east is a right turn', () => {
    expect(bearingDeg([10.77, 106.66], [10.78, 106.66])).toBeCloseTo(0, 0)
    expect(bearingDeg([10.77, 106.66], [10.77, 106.67])).toBeCloseTo(90, 0)
    expect(classifyTurn(angleDiffDeg(0, 90))).toBe('right')
    expect(classifyTurn(angleDiffDeg(0, -90))).toBe('left')
    expect(lerpHeadingDeg(0, 90, 0.5)).toBeCloseTo(45, 5)
  })

  it('labels a north-then-west corner left, even with dense OSM vertices', () => {
    const geom: [number, number][] = []
    for (let i = 0; i <= 8; i += 1) {
      geom.push([10.77 + i * 0.00012, 106.66])
    }
    const lastNorth = geom[geom.length - 1]!
    for (let i = 1; i <= 8; i += 1) {
      geom.push([lastNorth[0], lastNorth[1] - i * 0.00012])
    }
    const turns = extractManeuvers(geom).filter((m) => m.turn !== 'arrive')
    expect(turns.map((m) => m.turn)).toEqual(['left'])
  })

  it('labels a north-then-east corner right', () => {
    const geom: [number, number][] = []
    for (let i = 0; i <= 8; i += 1) {
      geom.push([10.77 + i * 0.00012, 106.66])
    }
    const lastNorth = geom[geom.length - 1]!
    for (let i = 1; i <= 8; i += 1) {
      geom.push([lastNorth[0], lastNorth[1] + i * 0.00012])
    }
    const turns = extractManeuvers(geom).filter((m) => m.turn !== 'arrive')
    expect(turns.map((m) => m.turn)).toEqual(['right'])
  })

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

  it('keeps successive opposite turns on a short hẻm zigzag', () => {
    const start: [number, number] = [10.77, 106.66]
    const mPerLat = 111_320
    const mPerLon = 111_320 * Math.cos((start[0] * Math.PI) / 180)
    const geom: [number, number][] = [start]
    const push = (northM: number, eastM: number, n: number) => {
      const origin = geom[geom.length - 1]!
      for (let i = 1; i <= n; i += 1) {
        geom.push([
          origin[0] + (northM * i) / n / mPerLat,
          origin[1] + (eastM * i) / n / mPerLon,
        ])
      }
    }
    push(22, 0, 6)
    push(0, -16, 5)
    push(22, 0, 6)
    const turns = extractManeuvers(geom).filter((m) => m.turn !== 'arrive')
    expect(turns.map((m) => m.turn)).toEqual(['left', 'right'])
    expect(turns[1]!.distanceFromStartM - turns[0]!.distanceFromStartM).toBeGreaterThan(
      12,
    )
  })

  it('tracks the last passed left/right after the corner', () => {
    const geom: [number, number][] = []
    for (let i = 0; i <= 8; i += 1) {
      geom.push([10.77 + i * 0.00012, 106.66])
    }
    const lastNorth = geom[geom.length - 1]!
    for (let i = 1; i <= 8; i += 1) {
      geom.push([lastNorth[0], lastNorth[1] - i * 0.00012])
    }
    const maneuvers = extractManeuvers(geom)
    const left = maneuvers.find((m) => m.turn === 'left')
    expect(left).toBeTruthy()
    expect(lastPassedTurn(maneuvers, left!.distanceFromStartM - 2)?.turn).not.toBe(
      'left',
    )
    expect(lastPassedTurn(maneuvers, left!.distanceFromStartM + 3)?.turn).toBe('left')
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
