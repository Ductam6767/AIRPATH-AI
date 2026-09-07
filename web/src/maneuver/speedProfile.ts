/**
 * Stepped speed advisory before a maneuver (demo scale, km/h).
 * Matches competition storytelling: gradual reduction, not hard braking.
 */
export function suggestedSpeedKmh(distanceToManeuverM: number): number {
  if (distanceToManeuverM >= 300) return 45
  if (distanceToManeuverM >= 200) return 40
  if (distanceToManeuverM >= 120) return 30
  if (distanceToManeuverM >= 60) return 25
  return 20
}

/** Ordered steps for UI display (e.g. ↓40 → ↓30). */
export function speedStepsAhead(distanceToManeuverM: number): number[] {
  const target = suggestedSpeedKmh(distanceToManeuverM)
  const ladder = [45, 40, 30, 25, 20]
  const idx = ladder.indexOf(target)
  if (idx <= 0) return [target]
  return ladder.slice(0, idx + 1)
}
