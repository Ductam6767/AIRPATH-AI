import { describe, expect, it } from 'vitest'
import { localFetchRoutes, localFetchScenarios } from '../offline/localDemo'

describe('bundled demo pack', () => {
  it('serves frozen scenarios and a walking route for od_01', async () => {
    const scenarios = await localFetchScenarios()
    expect(scenarios.scenarios).toHaveLength(8)
    const payload = await localFetchRoutes({
      scenarioId: 'od_01',
      mode: 'walking',
      deltaMinutes: 3,
    })
    expect(payload.fastest_route.is_fastest).toBe(true)
    expect(payload.fastest_route.geometry.length).toBeGreaterThan(1)
  })
})
