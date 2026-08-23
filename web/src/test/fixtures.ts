import type { RoutesResponse, ScenariosResponse } from '../types'

export const mockScenarios: ScenariosResponse = {
  scenarios: [
    {
      scenario_id: 'od_01',
      origin: {
        label: 'od_01 origin',
        latitude: 10.7992,
        longitude: 106.6612,
      },
      destination: {
        label: 'od_01 destination',
        latitude: 10.8056,
        longitude: 106.6871,
      },
      straight_line_distance_km: 2.9,
      supported_modes: ['walking', 'motorbike'],
      supported_delta_minutes: [0, 1, 2, 3, 5, 10],
      demo_distance_rank: 12,
      selection_method: 'test',
    },
    {
      scenario_id: 'od_05',
      origin: {
        label: 'Park Gate',
        latitude: 10.75,
        longitude: 106.63,
      },
      destination: {
        label: 'Market Hall',
        latitude: 10.78,
        longitude: 106.68,
      },
      straight_line_distance_km: 5.6,
      supported_modes: ['walking', 'motorbike'],
      supported_delta_minutes: [0, 1, 2, 3, 5, 10],
      demo_distance_rank: 29,
      selection_method: 'test',
    },
  ],
}

export const mockRoutesWithAlts: RoutesResponse = {
  scenario_id: 'od_01',
  mode: 'walking',
  delta_minutes: 3,
  fastest_route: {
    route_id: 'walking-1',
    route_type: 'fastest',
    rank: 0,
    is_fastest: true,
    is_feasible: true,
    travel_time_minutes: 40,
    additional_time_vs_fastest_minutes: 0,
    predicted_exposure_index: 1000,
    predicted_exposure_reduction_percent: 0,
    distance_m: 3300,
    geometry: [
      [10.7992, 106.6612],
      [10.8056, 106.6871],
    ],
  },
  alternatives: [
    {
      route_id: 'walking-2',
      route_type: 'AIRPATH alternative',
      rank: 1,
      is_fastest: false,
      is_feasible: true,
      travel_time_minutes: 42,
      additional_time_vs_fastest_minutes: 2,
      predicted_exposure_index: 720,
      predicted_exposure_reduction_percent: 28,
      distance_m: 3500,
      geometry: [
        [10.7992, 106.6612],
        [10.802, 106.67],
        [10.8056, 106.6871],
      ],
    },
  ],
  metadata: {
    empty_alternatives_message: null,
  },
}

export const mockRoutesEmptyAlts: RoutesResponse = {
  ...mockRoutesWithAlts,
  delta_minutes: 0,
  alternatives: [],
  metadata: {
    empty_alternatives_message:
      'No lower-exposure alternative fits your current time limit. Try allowing a few more minutes.',
  },
}
