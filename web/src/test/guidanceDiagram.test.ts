import { describe, expect, it } from 'vitest'
import { guidanceDiagramInner } from '../maneuver/guidanceDiagramSvg'

describe('guidance diagrams', () => {
  it('numbers roundabout exits and bolds the taken path', () => {
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
    expect(svg).toContain('>1</text>')
    expect(svg).toContain('>2</text>')
    expect(svg).toContain('>3</text>')
    expect(svg).toContain('#0f766e')
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
    expect(svg).toContain('#99f6e4')
    expect(svg).toContain('#0f766e')
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
    expect(over).toContain('Q14 -2 26 10')
    expect(under).toContain('Q14 -2 26 10')
    expect(over).not.toEqual(under)
  })
})
