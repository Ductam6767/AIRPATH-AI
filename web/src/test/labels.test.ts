import { describe, expect, it } from 'vitest'
import {
  destinationLabel,
  isLowerPredictedExposure,
  originLabel,
  reductionBadgeText,
  routeCardTitle,
  routeKindLabel,
  scenarioNumber,
} from '../utils/labels'
import type { RouteRecord, Scenario } from '../types'

const base = {
  straight_line_distance_km: 2.9,
  supported_modes: ['walking'],
  supported_delta_minutes: [0, 3],
  demo_distance_rank: 0,
  selection_method: 'test',
}

describe('labels', () => {
  it('uses stable Origin / Destination numbers instead of raw coordinates', () => {
    const scenario: Scenario = {
      ...base,
      scenario_id: 'od_26',
      origin: { label: 'od_26 origin', latitude: 10.75, longitude: 106.63 },
      destination: {
        label: 'od_26 destination',
        latitude: 10.76,
        longitude: 106.64,
      },
    }
    expect(scenarioNumber('od_26')).toBe('26')
    expect(originLabel(scenario)).toBe('Origin 26')
    expect(destinationLabel(scenario)).toBe('Destination 26')
  })

  it('keeps human-readable names when the API provides them', () => {
    const scenario: Scenario = {
      ...base,
      scenario_id: 'od_05',
      origin: { label: 'Park Gate', latitude: 10.75, longitude: 106.63 },
      destination: { label: 'Market Hall', latitude: 10.78, longitude: 106.68 },
    }
    expect(originLabel(scenario)).toBe('Park Gate')
    expect(destinationLabel(scenario)).toBe('Market Hall')
  })

  it('names route cards without medical language', () => {
    const fastest: RouteRecord = {
      route_id: 'w-1',
      route_type: 'fastest',
      rank: 0,
      is_fastest: true,
      is_feasible: true,
      travel_time_minutes: 20,
      additional_time_vs_fastest_minutes: 0,
      predicted_exposure_index: 100,
      predicted_exposure_reduction_percent: 0,
      distance_m: 1000,
      geometry: [],
    }
    const alt: RouteRecord = { ...fastest, route_id: 'w-2', route_type: 'AIRPATH alternative', rank: 1, is_fastest: false }
    expect(routeCardTitle(fastest)).toBe('Fastest')
    expect(routeCardTitle(alt)).toBe('AIRPATH alternative 1')
  })

  it('uses Lower predicted exposure only when exposure is actually lower', () => {
    const lower: RouteRecord = {
      route_id: 'w-2',
      route_type: 'AIRPATH alternative',
      rank: 1,
      is_fastest: false,
      is_feasible: true,
      travel_time_minutes: 21,
      additional_time_vs_fastest_minutes: 1,
      predicted_exposure_index: 720,
      predicted_exposure_reduction_percent: 28,
      distance_m: 1000,
      geometry: [],
    }
    const higher: RouteRecord = {
      ...lower,
      predicted_exposure_reduction_percent: -9.7,
    }
    expect(isLowerPredictedExposure(28)).toBe(true)
    expect(isLowerPredictedExposure(-9.7)).toBe(false)
    expect(routeKindLabel(lower)).toBe('Lower predicted exposure')
    expect(routeKindLabel(higher)).toBe('Feasible alternative')
    expect(reductionBadgeText(28)).toBe('28% lower predicted exposure')
    expect(reductionBadgeText(-9.7)).toBe('10% higher predicted exposure')
  })
})
