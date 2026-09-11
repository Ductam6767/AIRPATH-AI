import { describe, expect, it } from 'vitest'
import {
  CUE_TRIGGER_M,
  HUD_APPROACH_M,
  cuesForRoute,
  isCueEmphasized,
  isHudVisible,
  pickHudCue,
  placeCues,
  remainingToCue,
  type GuidanceCue,
  type PlacedCue,
} from '../maneuver/guidanceCues'
import { nearestDistanceAlongRoute } from '../maneuver/geo'

const northLine: [number, number][] = [
  [10.8, 106.66],
  [10.801, 106.66],
  [10.802, 106.66],
  [10.803, 106.66],
]

function placed(
  kind: PlacedCue['kind'],
  atM: number,
  extra: Partial<PlacedCue> = {},
): PlacedCue {
  return {
    id: kind,
    kind,
    lat: 10.8,
    lng: 106.66,
    atM,
    ...extra,
  }
}

describe('guidance cue distances', () => {
  it('projects a cue onto the nearest point along the polyline', () => {
    const along = nearestDistanceAlongRoute(northLine, [10.801, 106.66])
    expect(along).toBeGreaterThan(90)
    expect(along).toBeLessThan(130)
  })

  it('shows the HUD from 20 m and emphasizes at the type-specific range', () => {
    expect(isHudVisible(20)).toBe(true)
    expect(isHudVisible(21)).toBe(false)
    expect(isCueEmphasized('roundabout', 10)).toBe(true)
    expect(isCueEmphasized('roundabout', 11)).toBe(false)
    expect(isCueEmphasized('lane', 15)).toBe(true)
    expect(isCueEmphasized('lane', 16)).toBe(false)
    expect(isCueEmphasized('bridge', 20)).toBe(true)
    expect(CUE_TRIGGER_M.roundabout).toBe(10)
    expect(CUE_TRIGGER_M.lane).toBe(15)
    expect(CUE_TRIGGER_M.bridge).toBe(HUD_APPROACH_M)
  })

  it('picks the nearest upcoming junction, preferring a roundabout when they overlap', () => {
    const cues = [
      placed('bridge', 100),
      placed('roundabout', 104, { exit: 2, arms: 4 }),
      placed('lane', 160, { lanes: 4, turn: 'left', target: 0 }),
    ]
    expect(pickHudCue(cues, 0)).toBeNull()
    expect(pickHudCue(cues, 85)?.kind).toBe('roundabout')
    expect(remainingToCue(104, 94)).toBe(10)
  })

  it('still finds the same lat/lng after the geometry is reversed', () => {
    const cue: GuidanceCue = {
      kind: 'roundabout',
      lat: 10.802,
      lng: 106.66,
      exit: 2,
      arms: 4,
    }
    const forward = placeCues([cue], northLine)[0]!
    const reverse = placeCues([cue], [...northLine].reverse())[0]!
    expect(forward.atM).toBeGreaterThan(200)
    expect(reverse.atM).toBeGreaterThan(90)
    expect(Math.abs(forward.atM + reverse.atM - 333)).toBeLessThan(40)
  })
})

describe('bundled demo cues', () => {
  it('has a numbered roundabout on od_01 motorbike Fastest', () => {
    const cues = cuesForRoute('od_01', 'motorbike', 'motorbike-1')
    const roundabout = cues.find((cue) => cue.kind === 'roundabout')
    expect(roundabout).toBeTruthy()
    expect(roundabout?.exit).toBeGreaterThanOrEqual(1)
    expect(roundabout?.arms).toBeGreaterThanOrEqual(4)
    expect(roundabout?.arm_deg?.length).toBeGreaterThan(0)
  })
})
