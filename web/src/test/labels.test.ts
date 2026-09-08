import { describe, expect, it } from 'vitest'
import {
  destinationLabel,
  findScenarioId,
  hasLowerPredictedExposureAlternative,
  isLowerPredictedExposure,
  originLabel,
  pickRecommendedRoute,
  reductionBadgeText,
  routeCardTitle,
  routeKindLabel,
  scenarioDestKey,
  scenarioNumber,
  scenarioOriginKey,
  uniqueDestinations,
  uniquePlaces,
  originsForDestination,
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

  it('lists origins and destinations independently as places', () => {
    const first: Scenario = {
      ...base,
      scenario_id: 'od_01',
      origin: { label: 'od_01 origin', latitude: 10.79, longitude: 106.66 },
      destination: { label: 'od_01 destination', latitude: 10.8, longitude: 106.68 },
    }
    const second: Scenario = {
      ...base,
      scenario_id: 'od_05',
      origin: { label: 'Park Gate', latitude: 10.75, longitude: 106.63 },
      destination: { label: 'Market Hall', latitude: 10.78, longitude: 106.68 },
    }
    const places = uniquePlaces([first, second])
    const labels = places.map((place) => place.label)
    expect(labels).toEqual(
      expect.arrayContaining(['Origin 01', 'Destination 01', 'Park Gate', 'Market Hall']),
    )
    expect(places).toHaveLength(4)
  })

  it('lists destinations independently of the selected origin', () => {
    const first: Scenario = {
      ...base,
      scenario_id: 'od_01',
      origin: { label: 'Origin A', latitude: 10.79, longitude: 106.66 },
      destination: { label: 'Dest A', latitude: 10.8, longitude: 106.68 },
    }
    const second: Scenario = {
      ...base,
      scenario_id: 'od_05',
      origin: { label: 'Park Gate', latitude: 10.75, longitude: 106.63 },
      destination: { label: 'Market Hall', latitude: 10.78, longitude: 106.68 },
    }
    expect(uniqueDestinations([first, second]).map((place) => place.label)).toEqual(
      expect.arrayContaining(['Dest A', 'Market Hall']),
    )
    expect(originsForDestination([first, second], scenarioDestKey(second))[0]?.label).toBe(
      'Park Gate',
    )
  })

  it('looks up a precomputed pair without inferring destination from origin', () => {
    const first: Scenario = {
      ...base,
      scenario_id: 'od_01',
      origin: { label: 'Origin A', latitude: 10.79, longitude: 106.66 },
      destination: { label: 'Dest A', latitude: 10.8, longitude: 106.68 },
    }
    const second: Scenario = {
      ...base,
      scenario_id: 'od_05',
      origin: { label: 'Park Gate', latitude: 10.75, longitude: 106.63 },
      destination: { label: 'Market Hall', latitude: 10.78, longitude: 106.68 },
    }
    const scenarios = [first, second]
    expect(
      findScenarioId(
        scenarios,
        scenarioOriginKey(first),
        scenarioDestKey(first),
      ),
    ).toBe('od_01')
    expect(
      findScenarioId(
        scenarios,
        scenarioOriginKey(first),
        scenarioDestKey(second),
      ),
    ).toBeNull()
    expect(
      findScenarioId(
        scenarios,
        scenarioDestKey(first),
        scenarioOriginKey(first),
      ),
    ).toBeNull()
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
    expect(routeCardTitle(alt)).toBe('Balanced')
    expect(
      routeCardTitle({ ...alt, predicted_exposure_reduction_percent: 28 }),
    ).toBe('Health-first')
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
    expect(reductionBadgeText(-9.7)).toBe('+10% higher predicted exposure')
  })

  it('detects whether any feasible alternative has lower predicted exposure', () => {
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
    expect(hasLowerPredictedExposureAlternative([lower])).toBe(true)
    expect(
      hasLowerPredictedExposureAlternative([
        { ...lower, predicted_exposure_reduction_percent: -9.7 },
      ]),
    ).toBe(false)
    expect(hasLowerPredictedExposureAlternative([])).toBe(false)
  })

  it('recommends the lower-exposure alternative when one exists', () => {
    const fastest: RouteRecord = {
      route_id: 'w-1',
      route_type: 'fastest',
      rank: 0,
      is_fastest: true,
      is_feasible: true,
      travel_time_minutes: 20,
      additional_time_vs_fastest_minutes: 0,
      predicted_exposure_index: 1000,
      predicted_exposure_reduction_percent: 0,
      distance_m: 1000,
      geometry: [],
    }
    const health: RouteRecord = {
      ...fastest,
      route_id: 'w-2',
      is_fastest: false,
      route_type: 'AIRPATH alternative',
      predicted_exposure_index: 720,
      predicted_exposure_reduction_percent: 28,
    }
    expect(pickRecommendedRoute(fastest, [health]).route_id).toBe('w-2')
    expect(pickRecommendedRoute(fastest, []).route_id).toBe('w-1')
  })
})
