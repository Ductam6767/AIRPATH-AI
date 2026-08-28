import type { Gap1Exhibit, RoutesResponse, ScenariosResponse } from '../types'

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

export const mockRoutesHigherExposure: RoutesResponse = {
  ...mockRoutesWithAlts,
  alternatives: [
    {
      ...mockRoutesWithAlts.alternatives[0],
      predicted_exposure_index: 1100,
      predicted_exposure_reduction_percent: -10,
    },
  ],
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

export const mockGap1Exhibit: Gap1Exhibit = {
  pack_name: 'airpath_gap1_direction_a_v1',
  uses_simulated_onroad_pm: false,
  scientific_logic_modified: false,
  question:
    'Does ranking the same candidate routes by hourly arrival-time exposure change the constrained selection relative to a static departure-time PM snapshot?',
  desired_quantity:
    'PM2.5 at the road segment at the exact minute the traveller arrives there.',
  available_substitution:
    'Ceiling the segment ETA to the next HealthyAir hour, then IDW p=1 from six station forecasts.',
  not_available: ['On-road / mobile-monitoring PM2.5 at the segment'],
  data_required_for_street_pm: [
    'PM2.5 sampled on or beside the roadway, time-aligned to the trajectory',
  ],
  worked_example: {
    departure: '06:00',
    forecast_origin: '05:00',
    segment_passage: '06:17',
    hour_used: '07:00',
    note: '06:17 is not interpolated. The supported HealthyAir hour is 07:00.',
  },
  ceiling_rule:
    'Exact hourly ETA stays on that hour. Any other ETA is ceiled to the next exact hour.',
  exposure_definition: 'sum_pm25_times_duration_minutes',
  exposure_unit: '(µg/m³)·min',
  forecaster: 'C_xgboost_current_pm',
  spatial_model: 'idw_p1',
  freeze_gap1_conclusion:
    'MIXED/WEAK evidence that hourly forecast-bucket-aware exposure changes route decisions relative to a static departure-time snapshot (P0-2A/P0-2B).',
  p0_2a: {
    label: 'Single morning departure (2022-02-28 06:00)',
    classification: 'B. MIXED EVIDENCE',
    rationale: 'Selections sometimes differ, but oracle gains are weak.',
    nontrivial_selection_difference_rate: 0.0633,
    mean_oracle_percent_improvement_when_differ: 0.1077,
    mean_spearman_static_vs_airpath: 0.992,
    representative_disagreements: [
      {
        scenario_id: 'od_02',
        mode: 'motorbike',
        delta_minutes: 5,
        fastest_route_id: 'motorbike-1',
        static_selected_route_id: 'motorbike-2',
        airpath_selected_route_id: 'motorbike-1',
        oracle_percent_improvement_airpath_over_static: 0.071,
      },
    ],
  },
  p0_2b: {
    label: 'Five clock times on 2022-02-27',
    classification: 'B. MIXED EVIDENCE',
    rationale: 'Pooled difference rate is lower than P0-2A.',
    nontrivial_selection_difference_rate: 0.0133,
    mean_oracle_percent_improvement_when_differ: 0.02,
    mean_spearman_static_vs_airpath: 0.997,
    by_clock: [
      {
        clock_time: '06:00',
        departure_time: '2022-02-27 06:00:00',
        nontrivial_selection_difference_rate: 0.05,
        mean_spearman: 0.99,
        mean_oracle_pct_improvement_when_differ: 0.04,
      },
    ],
    representative_disagreements: [],
  },
  paper_claim_allowed:
    'Hourly forecast-bucket-aware exposure rarely changes constrained route selection versus a static snapshot (MIXED/WEAK).',
  paper_claim_forbidden: [
    'AIRPATH knows PM2.5 on street D at the arrival minute.',
    'The product map simulated traffic-class PM is a Gap 1 result.',
  ],
}
