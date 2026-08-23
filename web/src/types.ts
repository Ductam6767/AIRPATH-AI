/** Shared TypeScript contracts for the WEB-1 demo API (render-only). */

export type TravelMode = 'walking' | 'motorbike'

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
  demo_distance_rank: number
  selection_method: string
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
  research_warning?: string | null
}

export interface RoutesResponse {
  scenario_id: string
  mode: TravelMode | string
  delta_minutes: number
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
