import type { GuidanceCue } from './guidanceCues'

const TAKEN = '#ea580c'
const TAKEN_DARK = '#9a3412'
const ROAD = '#94a3b8'
const ROAD_FILL = '#d6dde6'
const INK = '#0f172a'

function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = (deg * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

/** Heading-up, Vietnam RHT: entry at bottom, 1st exit right, then top, then left. */
export function roundaboutTravelAngle(armDeg: number): number {
  return 90 - armDeg
}

function minArmGap(armDeg: number[]): number {
  if (armDeg.length < 2) return 360
  const sorted = [...armDeg]
    .map((deg) => ((deg % 360) + 360) % 360)
    .sort((a, b) => a - b)
  let gap = 360
  for (let i = 0; i < sorted.length; i++) {
    const next = sorted[(i + 1) % sorted.length]!
    const delta = (next - sorted[i]! + 360) % 360
    if (delta > 0 && delta < gap) gap = delta
  }
  return gap
}

function evenArms(count: number): number[] {
  return Array.from({ length: count }, (_, i) => (i * 360) / count)
}

export function resolveRoundaboutArms(cue: GuidanceCue, arms: number): number[] {
  const raw = (cue.arm_deg ?? []).filter((deg) => Number.isFinite(deg))
  if (raw.length < arms || minArmGap(raw.slice(0, arms)) < 40) {
    return evenArms(arms)
  }
  return raw.slice(0, arms)
}

function roadQuad(
  cx: number,
  cy: number,
  deg: number,
  r0: number,
  r1: number,
  hw: number,
): string {
  const rad = (deg * Math.PI) / 180
  const ux = Math.cos(rad)
  const uy = Math.sin(rad)
  const px = -uy
  const py = ux
  const corners = [
    [cx + ux * r0 + px * hw, cy + uy * r0 + py * hw],
    [cx + ux * r1 + px * hw, cy + uy * r1 + py * hw],
    [cx + ux * r1 - px * hw, cy + uy * r1 - py * hw],
    [cx + ux * r0 - px * hw, cy + uy * r0 - py * hw],
  ]
  return corners.map((p) => `${p[0]!.toFixed(1)},${p[1]!.toFixed(1)}`).join(' ')
}

function annularSector(
  cx: number,
  cy: number,
  rIn: number,
  rOut: number,
  a0: number,
  a1: number,
): string {
  // Walk decreasing polar angle: bottom → right → top (VN RHT, island on the left).
  // Polylines avoid SVG arc sweep-flag flipping on a 180° semicircle.
  let span = (a0 - a1 + 360) % 360
  if (span < 12) span = 90
  const steps = Math.max(12, Math.round(span / 8) + (Math.round(span / 8) % 2))
  const outer: string[] = []
  const inner: string[] = []
  for (let i = 0; i <= steps; i++) {
    const deg = a0 - (span * i) / steps
    const [ox, oy] = polar(cx, cy, rOut, deg)
    outer.push(`${ox.toFixed(1)} ${oy.toFixed(1)}`)
  }
  for (let i = steps; i >= 0; i--) {
    const deg = a0 - (span * i) / steps
    const [ix, iy] = polar(cx, cy, rIn, deg)
    inner.push(`${ix.toFixed(1)} ${iy.toFixed(1)}`)
  }
  return `M ${outer[0]} L ${outer.slice(1).join(' L ')} L ${inner.join(' L ')} Z`
}

function arrowHead(tip: [number, number], deg: number, size = 10): string {
  const rad = (deg * Math.PI) / 180
  const back = 12
  const base: [number, number] = [
    tip[0] - Math.cos(rad) * back,
    tip[1] - Math.sin(rad) * back,
  ]
  const left = polar(base[0], base[1], size, deg - 90)
  const right = polar(base[0], base[1], size, deg + 90)
  return `<polygon points="${tip[0].toFixed(1)},${tip[1].toFixed(1)} ${left[0].toFixed(1)},${left[1].toFixed(1)} ${right[0].toFixed(1)},${right[1].toFixed(1)}" fill="${TAKEN}" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>`
}

function youChevron(at: [number, number], deg: number): string {
  const rad = (deg * Math.PI) / 180
  const tip: [number, number] = [
    at[0] + Math.cos(rad) * 7,
    at[1] + Math.sin(rad) * 7,
  ]
  const back: [number, number] = [
    at[0] - Math.cos(rad) * 6,
    at[1] - Math.sin(rad) * 6,
  ]
  const left = polar(back[0], back[1], 6.5, deg - 90)
  const right = polar(back[0], back[1], 6.5, deg + 90)
  return `<polygon points="${tip[0].toFixed(1)},${tip[1].toFixed(1)} ${left[0].toFixed(1)},${left[1].toFixed(1)} ${right[0].toFixed(1)},${right[1].toFixed(1)}" fill="${INK}" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>`
}

function dualStroke(d: string, outer: number, inner: number): string {
  return `<path d="${d}" fill="none" stroke="${INK}" stroke-width="${outer}" stroke-linecap="round" stroke-linejoin="round"/><path d="${d}" fill="none" stroke="${TAKEN}" stroke-width="${inner}" stroke-linecap="round" stroke-linejoin="round"/>`
}

function roundaboutSvg(cue: GuidanceCue, emphasized: boolean): string {
  const arms = Math.max(3, Math.min(7, cue.arms ?? 4))
  const exit = Math.max(1, Math.min(arms - 1, cue.exit ?? 1))
  const armDeg = resolveRoundaboutArms(cue, arms)
  const cx = 60
  const cy = 60
  const ringR = 26
  const roadR = 56
  const hw = (emphasized ? 8.4 : 7.4) * (arms >= 5 ? 0.82 : 1)
  const casing = 1.7
  const rOut = ringR + hw
  const rIn = ringR - hw
  const entryA = roundaboutTravelAngle(0)
  const takenA = roundaboutTravelAngle(armDeg[exit] ?? 180)

  const greyArms = armDeg
    .map((deg) => {
      const a = roundaboutTravelAngle(deg)
      return `<polygon class="rb-arm" points="${roadQuad(cx, cy, a, ringR - 2, roadR, hw)}" fill="${ROAD_FILL}" stroke="${INK}" stroke-width="1.8" stroke-linejoin="round"/>`
    })
    .join('')

  const greyRing = `<circle cx="${cx}" cy="${cy}" r="${rOut.toFixed(1)}" fill="${ROAD_FILL}" stroke="${INK}" stroke-width="1.8"/><circle cx="${cx}" cy="${cy}" r="${rIn.toFixed(1)}" fill="#fff" stroke="${INK}" stroke-width="1.6"/>`

  const entryPts = roadQuad(cx, cy, entryA, rOut - 0.8, roadR, hw + casing)
  const exitPts = roadQuad(cx, cy, takenA, rOut - 0.8, roadR, hw + casing)
  const sectorCasing = annularSector(
    cx,
    cy,
    Math.max(6, rIn - casing),
    rOut + casing,
    entryA,
    takenA,
  )
  const entryFill = roadQuad(cx, cy, entryA, rOut - 1.2, roadR - 0.4, hw)
  const exitFill = roadQuad(cx, cy, takenA, rOut - 1.2, roadR - 0.4, hw)
  const sectorFill = annularSector(cx, cy, rIn, rOut, entryA, takenA)

  const paint = [
    `<polygon class="rb-taken-casing" points="${entryPts}" fill="${INK}"/>`,
    `<polygon class="rb-taken-casing" points="${exitPts}" fill="${INK}"/>`,
    `<path class="rb-taken-casing" d="${sectorCasing}" fill="${INK}"/>`,
    `<polygon class="rb-taken-paint" points="${entryFill}" fill="${TAKEN}"/>`,
    `<polygon class="rb-taken-paint" points="${exitFill}" fill="${TAKEN}"/>`,
    `<path class="rb-taken-paint" d="${sectorFill}" fill="${TAKEN}"/>`,
  ].join('')

  const numbers = armDeg
    .slice(1)
    .map((deg, i) => {
      const n = i + 1
      const badgeR = arms >= 5 ? 7.8 : 9.6
      const font = arms >= 5 ? 10.5 : 12
      const [x, y] = polar(cx, cy, arms >= 5 ? 39 : 41, roundaboutTravelAngle(deg))
      const active = n === exit
      return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${badgeR}" fill="${active ? TAKEN : '#fff'}" stroke="${active ? TAKEN_DARK : INK}" stroke-width="2.1"/><text x="${x.toFixed(1)}" y="${(y + (arms >= 5 ? 3.8 : 4.4)).toFixed(1)}" text-anchor="middle" font-size="${font}" font-weight="900" font-family="ui-sans-serif,system-ui,sans-serif" fill="${active ? '#fff' : INK}">${n}</text>`
    })
    .join('')

  const tip = polar(cx, cy, roadR - 1, takenA)
  const youAt = polar(cx, cy, 49, entryA)
  const island = `<circle cx="${cx}" cy="${cy}" r="${Math.max(7, rIn - 3).toFixed(1)}" fill="#fff" stroke="${INK}" stroke-width="1.2"/>`

  return `<rect x="2" y="2" width="116" height="116" rx="14" fill="#fff"/>${greyArms}${greyRing}${paint}${island}${arrowHead(tip, takenA)}${youChevron(youAt, entryA + 180)}${numbers}`
}

function laneSvg(cue: GuidanceCue, emphasized: boolean): string {
  const n = Math.max(3, Math.min(6, cue.lanes ?? 4))
  const turn = cue.turn === 'right' ? 'right' : 'left'
  const target = Math.min(n - 1, Math.max(0, cue.target ?? (turn === 'left' ? 0 : n - 1)))
  const pad = 8
  const top = 14
  const bottom = 106
  const width = (104 - pad) / n
  const lanes = Array.from({ length: n }, (_, i) => {
    const x = pad + i * width
    const active = i === target
    const fill = active ? '#fdba74' : '#cbd5e1'
    const stroke = active ? TAKEN_DARK : '#64748b'
    const sw = active ? (emphasized ? 4 : 3.2) : 1.4
    const labelY = bottom - 8
    return `<rect x="${x.toFixed(1)}" y="${top}" width="${(width - 2.5).toFixed(1)}" height="${bottom - top}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>${active ? '' : `<text x="${(x + (width - 2.5) / 2).toFixed(1)}" y="${labelY}" text-anchor="middle" font-size="8" font-weight="800" fill="#475569">${i + 1}</text>`}`
  }).join('')
  const dashes = Array.from({ length: n - 1 }, (_, i) => {
    const x = pad + (i + 1) * width - 1.2
    return `<line x1="${x.toFixed(1)}" y1="${top + 6}" x2="${x.toFixed(1)}" y2="${bottom - 6}" stroke="#fff" stroke-width="1.6" stroke-dasharray="5 4"/>`
  }).join('')
  const tx = pad + target * width + (width - 2.5) / 2
  const tipX = turn === 'left' ? tx - 22 : tx + 22
  const shaft = `M ${tx.toFixed(1)} 98 L ${tx.toFixed(1)} 32 L ${tipX.toFixed(1)} 32`
  const activeNum = `<circle cx="${tx.toFixed(1)}" cy="88" r="8.5" fill="${TAKEN}" stroke="${INK}" stroke-width="1.8"/><text x="${tx.toFixed(1)}" y="92.2" text-anchor="middle" font-size="11" font-weight="900" fill="#fff">${target + 1}</text>`
  return `<rect x="2" y="2" width="116" height="116" rx="14" fill="#0f172a"/>${lanes}${dashes}${dualStroke(shaft, emphasized ? 10 : 8.5, emphasized ? 6.5 : 5.2)}${arrowHead([tipX, 32], turn === 'left' ? 180 : 0, 8)}${activeNum}`
}

function bridgeSvg(cue: GuidanceCue, emphasized: boolean): string {
  const over = cue.relation !== 'under'
  const upper = over ? TAKEN : ROAD
  const lower = over ? ROAD : TAKEN
  const uw = over ? (emphasized ? 8 : 6.5) : 3.2
  const lw = over ? 3.2 : emphasized ? 8 : 6.5
  const icon = `<g transform="translate(44 12)" fill="none" stroke="${INK}" stroke-width="2.2" stroke-linecap="round"><path d="M2 18 L2 11 Q16 -4 30 11 L30 18"/><path d="M2 18 L30 18" stroke-width="2.6"/><path d="M9 18 L9 13"/><path d="M23 18 L23 13"/></g>`
  const upperLine = `M 12 58 L 108 58`
  const arch = `M 16 58 Q 60 40 104 58`
  const lowerLine = `M 16 90 L 104 90`
  return `<rect x="2" y="2" width="116" height="116" rx="14" fill="#fff"/>${icon}<path d="${upperLine}" fill="none" stroke="${INK}" stroke-width="${uw + 3}" stroke-linecap="round"/><path d="${upperLine}" fill="none" stroke="${upper}" stroke-width="${uw}" stroke-linecap="round"/><path d="${arch}" fill="none" stroke="${upper}" stroke-width="${over ? 3 : 1.8}" opacity="${over ? 1 : 0.45}"/><path d="${lowerLine}" fill="none" stroke="${INK}" stroke-width="${lw + 3}" stroke-linecap="round"/><path d="${lowerLine}" fill="none" stroke="${lower}" stroke-width="${lw}" stroke-linecap="round"/>`
}

export function guidanceDiagramInner(cue: GuidanceCue, emphasized = false): string {
  if (cue.kind === 'lane') return laneSvg(cue, emphasized)
  if (cue.kind === 'bridge') return bridgeSvg(cue, emphasized)
  return roundaboutSvg(cue, emphasized)
}
