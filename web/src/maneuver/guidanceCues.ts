import pack from '@demo-pack/guidance_cues.json'
import { nearestDistanceAlongRoute } from './geo'

export const HUD_APPROACH_M = 20
export const CUE_HOLD_AFTER_M = 8
export const BRIDGE_ICON_AHEAD_M = 80
export const CUE_TRIGGER_M = {
  roundabout: 10,
  lane: 15,
  bridge: 20,
} as const

export type GuidanceKind = 'roundabout' | 'lane' | 'bridge'
export type BridgeRelation = 'over' | 'under'
export type LaneTurn = 'left' | 'right'

export interface GuidanceCue {
  kind: GuidanceKind
  lat: number
  lng: number
  exit?: number
  arms?: number
  arm_deg?: number[]
  lanes?: number
  turn?: LaneTurn
  target?: number
  relation?: BridgeRelation
}

export interface PlacedCue extends GuidanceCue {
  id: string
  atM: number
}

const KIND_RANK: Record<GuidanceKind, number> = {
  roundabout: 0,
  lane: 1,
  bridge: 2,
}

function asCue(raw: unknown, index: number): GuidanceCue | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const kind = row.kind
  if (kind !== 'roundabout' && kind !== 'lane' && kind !== 'bridge') return null
  const lat = Number(row.lat)
  const lng = Number(row.lng)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
  const cue: GuidanceCue = { kind, lat, lng }
  if (kind === 'roundabout') {
    cue.exit = Math.max(1, Math.round(Number(row.exit) || 1))
    cue.arms = Math.max(3, Math.min(7, Math.round(Number(row.arms) || 4)))
    cue.arm_deg = Array.isArray(row.arm_deg)
      ? row.arm_deg.map((value) => Number(value)).filter(Number.isFinite)
      : [0, 90, 180, 270]
  }
  if (kind === 'lane') {
    cue.lanes = Math.max(3, Math.min(8, Math.round(Number(row.lanes) || 4)))
    cue.turn = row.turn === 'right' ? 'right' : 'left'
    cue.target = Math.max(0, Math.round(Number(row.target) || 0))
  }
  if (kind === 'bridge') {
    cue.relation = row.relation === 'under' ? 'under' : 'over'
  }
  void index
  return cue
}

const PACK_ROUTES: Record<string, GuidanceCue[]> = (() => {
  const routes = (pack as { routes?: Record<string, unknown> }).routes ?? {}
  const out: Record<string, GuidanceCue[]> = {}
  for (const [key, list] of Object.entries(routes)) {
    if (!Array.isArray(list)) continue
    out[key] = list
      .map((row, index) => asCue(row, index))
      .filter((cue): cue is GuidanceCue => cue != null)
  }
  return out
})()

export function cueRouteKey(
  scenarioId: string,
  mode: string,
  routeId: string,
): string {
  return `${scenarioId}|${mode}|${routeId}`
}

export function cuesForRoute(
  scenarioId: string | null | undefined,
  mode: string | null | undefined,
  routeId: string | null | undefined,
): GuidanceCue[] {
  if (!scenarioId || !mode || !routeId) return []
  return PACK_ROUTES[cueRouteKey(scenarioId, mode, routeId)] ?? []
}

export function placeCues(
  cues: GuidanceCue[],
  geometry: [number, number][],
): PlacedCue[] {
  return cues.map((cue, index) => ({
    ...cue,
    id: `${cue.kind}-${index}-${cue.lat.toFixed(5)}`,
    atM: nearestDistanceAlongRoute(geometry, [cue.lat, cue.lng]),
  }))
}

export function remainingToCue(atM: number, distanceAlongM: number): number {
  return atM - distanceAlongM
}

export function cueTriggerM(kind: GuidanceKind): number {
  return CUE_TRIGGER_M[kind]
}

/** Large HUD copy: auto from 20 m so the rider can look down without covering the road. */
export function isHudVisible(remainingM: number): boolean {
  return remainingM <= HUD_APPROACH_M && remainingM >= -CUE_HOLD_AFTER_M
}

export function isCueEmphasized(kind: GuidanceKind, remainingM: number): boolean {
  return remainingM <= cueTriggerM(kind) && remainingM >= -4
}

export function isMapDiagramVisible(kind: GuidanceKind, remainingM: number): boolean {
  if (kind === 'bridge') return isHudVisible(remainingM)
  return remainingM <= HUD_APPROACH_M && remainingM >= -CUE_HOLD_AFTER_M
}

export function isBridgeIconVisible(remainingM: number): boolean {
  return remainingM <= BRIDGE_ICON_AHEAD_M && remainingM >= -15
}

export function pickHudCue(
  placed: PlacedCue[],
  distanceAlongM: number,
): PlacedCue | null {
  const visible = placed
    .map((cue) => ({ cue, remaining: remainingToCue(cue.atM, distanceAlongM) }))
    .filter((row) => isHudVisible(row.remaining))
  if (visible.length === 0) return null
  visible.sort((a, b) => {
    const rank = KIND_RANK[a.cue.kind] - KIND_RANK[b.cue.kind]
    if (rank !== 0 && Math.abs(a.remaining - b.remaining) < 8) return rank
    return a.remaining - b.remaining
  })
  return visible[0]!.cue
}
