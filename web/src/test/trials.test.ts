import { describe, expect, it } from 'vitest'
import { pointAlongRoute } from '../maneuver/geo'
import { speedStepsAhead } from '../maneuver/speedProfile'
import { summarizeTrials, trialsToCsv, type TrialRow } from '../offline/trials'

describe('speedStepsAhead', () => {
  it('shows remaining ladder from current target', () => {
    expect(speedStepsAhead(150)).toEqual([30, 25, 20])
    expect(speedStepsAhead(30)).toEqual([20])
  })
})

describe('pointAlongRoute', () => {
  it('interpolates between vertices', () => {
    const geom: [number, number][] = [
      [10, 106],
      [10, 106.01],
    ]
    const mid = pointAlongRoute(geom, 50)
    expect(mid).not.toBeNull()
    expect(mid![1]).toBeGreaterThan(106)
    expect(mid![1]).toBeLessThan(106.01)
  })
})

describe('trial log', () => {
  it('summarizes C vs K groups', () => {
    const rows: TrialRow[] = [
      {
        id: '1',
        at: 't',
        assistant: 'C',
        speed50: 22,
        speedMax: 30,
        blinkerOk: 'yes',
        notes: '',
      },
      {
        id: '2',
        at: 't',
        assistant: 'C',
        speed50: 20,
        speedMax: 28,
        blinkerOk: 'yes',
        notes: '',
      },
      {
        id: '3',
        at: 't',
        assistant: 'K',
        speed50: 32,
        speedMax: 40,
        blinkerOk: 'no',
        notes: '',
      },
    ]
    const summary = summarizeTrials(rows)
    const on = summary.find((s) => s.assistant === 'C')
    const off = summary.find((s) => s.assistant === 'K')
    expect(on?.n).toBe(2)
    expect(on?.mean50).toBe(21)
    expect(on?.pctBlinker).toBe(100)
    expect(off?.pctSlow).toBe(0)
    expect(trialsToCsv(rows).split('\n')).toHaveLength(4)
  })
})
