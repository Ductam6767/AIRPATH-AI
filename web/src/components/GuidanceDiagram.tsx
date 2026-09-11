import type { GuidanceCue } from '../maneuver/guidanceCues'
import { guidanceDiagramInner } from '../maneuver/guidanceDiagramSvg'

interface GuidanceDiagramProps {
  cue: GuidanceCue
  size?: 'map' | 'hud'
  emphasized?: boolean
}

export function GuidanceDiagram({
  cue,
  size = 'hud',
  emphasized = false,
}: GuidanceDiagramProps) {
  const px = size === 'hud' ? 216 : 88
  return (
    <svg
      className={`guidance-diagram guidance-diagram--${size}${emphasized ? ' is-active' : ''}`}
      viewBox="0 0 120 120"
      width={px}
      height={px}
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: guidanceDiagramInner(cue, emphasized) }}
    />
  )
}
