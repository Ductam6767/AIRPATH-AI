import { describe, expect, it } from 'vitest'
import {
  casingRouteWeight,
  innerRouteWeight,
  routeLinePaint,
  ROUTE_CASING_COLOR,
} from '../utils/routeLinePaint'
import type { RouteRecord } from '../types'

const fastest: RouteRecord = {
  route_id: 'f',
  route_type: 'fastest',
  rank: 0,
  is_fastest: true,
  is_feasible: true,
  travel_time_minutes: 10,
  additional_time_vs_fastest_minutes: 0,
  predicted_exposure_index: 1,
  predicted_exposure_reduction_percent: 0,
  distance_m: 1000,
  geometry: [],
}

describe('routeLinePaint', () => {
  it('keeps street-zoom strokes thinner than the old 8–10px overlay', () => {
    expect(innerRouteWeight(16, 'selected', false)).toBeLessThan(5)
    expect(innerRouteWeight(16, 'selected', true)).toBeLessThan(5)
    expect(casingRouteWeight(4.25)).toBeLessThan(8)
  })

  it('draws a black casing wider than the coloured fill', () => {
    const paint = routeLinePaint(fastest, 'f', false, 16)
    expect(paint.casing.color).toBe(ROUTE_CASING_COLOR)
    expect(paint.fill.weight).toBeLessThan(paint.casing.weight as number)
    expect((paint.casing.weight as number) - (paint.fill.weight as number)).toBeGreaterThan(
      1.5,
    )
  })
})
