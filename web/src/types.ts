/** Shared TypeScript contracts for the WEB-1 demo API (render-only). */

export type TravelMode = 'walking' | 'motorbike'
export type TimeWindow = 'morning_peak' | 'midday' | 'evening_peak'

export interface Coordinate {
  label: string
  latitude: number
  longitude: number
}

export interface Scenario {
  scenario_id: string
  origin: Coordinate
  destination: Coordinate
  straight_line_distance_km: number
  supported_modes: string[]
  supported_delta_minutes: number[]
  supported_time_windows?: string[]
  demo_distance_rank: number
  selection_method: string
  opening_example?: boolean
}

export interface ScenariosResponse {
  scenarios: Scenario[]
}

export interface RouteRecord {
  route_id: string
  route_type: string
  rank: number
  is_fastest: boolean
  is_feasible: boolean
  travel_time_minutes: number
  additional_time_vs_fastest_minutes: number
  predicted_exposure_index: number
  predicted_exposure_reduction_percent: number
  distance_m: number
  geometry: [number, number][]
  available_feasible_alternatives?: number | null
  fewer_than_requested_alternatives?: boolean | null
  is_also_lowest_exposure?: boolean | null
  tradeoff_slot?: string | null
  research_warning?: string | null
}

export interface RoutesResponse {
  scenario_id: string
  mode: TravelMode | string
  delta_minutes: number
  time_window?: TimeWindow | string
  fastest_route: RouteRecord
  alternatives: RouteRecord[]
  metadata: Record<string, unknown>
}

export interface ApiErrorBody {
  detail?:
    | string
    | {
        error?: string
        message?: string
        [key: string]: unknown
      }
}

export interface Gap1Disagreement {
  scenario_id: string
  mode: string
  delta_minutes: number
  fastest_route_id: string
  static_selected_route_id: string
  airpath_selected_route_id: string
  oracle_percent_improvement_airpath_over_static: number
  departure_time?: string
}

export interface Gap1ClockRow {
  clock_time: string
  departure_time: string
  nontrivial_selection_difference_rate: number
  mean_spearman: number
  mean_oracle_pct_improvement_when_differ: number | null
  mean_abs_pct_exposure_diff?: number
  band?: string
}

export interface Gap1CountRow {
  differ_count: number
  nontrivial_count: number
  rate: number
  mode?: string
  clock_time?: string
  band?: string
}

export interface Gap1Proof {
  meaning: string
  recipe: string
  reviewer_sentence: string
  p0_2a: Gap1CountRow & { by_mode: Gap1CountRow[] }
  p0_2b: Gap1CountRow & {
    by_mode: Gap1CountRow[]
    by_clock_and_mode?: Gap1CountRow[]
  }
}

export interface Gap1PeakHourNote {
  what_is_identifiable: string
  what_is_not_identifiable: string
  result: string
  future_when_street_data_exists: string
}

export interface Gap1Panel {
  label: string
  classification: string
  rationale: string
  nontrivial_selection_difference_rate: number
  mean_oracle_percent_improvement_when_differ: number
  mean_spearman_static_vs_airpath: number
  representative_disagreements: Gap1Disagreement[]
  gap1_conclusion_changed_vs_p0_2a?: boolean
  by_clock?: Gap1ClockRow[]
}

export interface Gap1WorkedExample {
  departure: string
  forecast_origin: string
  segment_passage: string
  hour_used: string
  note: string
}

export interface Gap1Exhibit {
  pack_name: string
  uses_simulated_onroad_pm: boolean
  scientific_logic_modified: boolean
  question: string
  desired_quantity: string
  available_substitution: string
  not_available: string[]
  data_required_for_street_pm: string[]
  worked_example: Gap1WorkedExample
  ceiling_rule: string
  exposure_definition: string
  exposure_unit: string
  forecaster: string
  spatial_model: string
  freeze_gap1_conclusion: string
  p0_2a: Gap1Panel
  p0_2b: Gap1Panel
  how_to_prove_rare: Gap1Proof
  peak_hour_with_current_data: Gap1PeakHourNote
  paper_claim_allowed: string
  paper_claim_forbidden: string[]
}
