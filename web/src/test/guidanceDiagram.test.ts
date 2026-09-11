import { describe, expect, it } from 'vitest'
import {
  guidanceDiagramInner,
  resolveRoundaboutArms,
  roundaboutTravelAngle,
} from '../maneuver/guidanceDiagramSvg'

describe('guidance diagrams', () => {
  it('paints every roundabout arm and fills the taken road orange', () => {
    const svg = guidanceDiagramInner(
      {
        kind: 'roundabout',
        lat: 10.8,
        lng: 106.66,
        exit: 2,
        arms: 4,
        arm_deg: [0, 90, 180, 270],
      },
      true,
    )
    expect(svg.match(/class="rb-arm"/g)?.length).toBe(4)
    expect(svg).toContain('class="rb-taken-paint"')
    expect(svg).toContain('fill="#ea580c"')
    expect(svg).toContain('>1</text>')
    expect(svg).toContain('>2</text>')
    expect(svg).toContain('>3</text>')
    expect(roundaboutTravelAngle(0)).toBe(90)
    expect(roundaboutTravelAngle(90)).toBe(0)
    expect(roundaboutTravelAngle(180)).toBe(-90)
    // Exit 2 paints the RIGHT half of the ring (bottom → right → top), not the left.
    const sector = [...svg.matchAll(/class="rb-taken-paint" d="([^"]+)"/g)][0]?.[1] ?? ''
    expect(sector).toMatch(/9[0-9]\.[0-9] 60\./)
  })

  it('spaces clustered OSM arms evenly so every road stays visible', () => {
    const arms = resolveRoundaboutArms(
      {
        kind: 'roundabout',
        lat: 10.8,
        lng: 106.66,
        exit: 1,
        arms: 4,
        arm_deg: [0, 15, 105, 180],
      },
      4,
    )
    expect(arms).toEqual([0, 90, 180, 270])
    const svg = guidanceDiagramInner({
      kind: 'roundabout',
      lat: 10.8,
      lng: 106.66,
      exit: 2,
      arms: 4,
      arm_deg: [0, 15, 105, 180],
    })
    expect(svg.match(/class="rb-arm"/g)?.length).toBe(4)
    expect(svg.match(/class="rb-taken-paint"/g)?.length).toBe(3)
  })

  it('highlights the inner lane for a left turn', () => {
    const svg = guidanceDiagramInner({
      kind: 'lane',
      lat: 10.8,
      lng: 106.66,
      lanes: 4,
      turn: 'left',
      target: 0,
    })
    expect(svg).toContain('#fdba74')
    expect(svg).toContain('#ea580c')
  })

  it('draws a small bridge glyph for over and under', () => {
    const over = guidanceDiagramInner({
      kind: 'bridge',
      lat: 10.8,
      lng: 106.66,
      relation: 'over',
    })
    const under = guidanceDiagramInner({
      kind: 'bridge',
      lat: 10.8,
      lng: 106.66,
      relation: 'under',
    })
    expect(over).toContain('Q16 -4 30 11')
    expect(under).toContain('Q16 -4 30 11')
    expect(over).not.toEqual(under)
  })
})
