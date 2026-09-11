import type { GuidanceCue } from './guidanceCues'

const TAKEN = '#ea580c'
const TAKEN_DARK = '#9a3412'
const ROAD = '#94a3b8'
const ROAD_FILL = '#e2e8f0'
const INK = '#0f172a'

function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = (deg * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

function svgAngle(armDeg: number): number {
  return 90 + armDeg
}

function dualStroke(d: string, outer: number, inner: number): string {
  return `<path d="${d}" fill="none" stroke="${INK}" stroke-width="${outer}" stroke-linecap="round" stroke-linejoin="round"/><path d="${d}" fill="none" stroke="${TAKEN}" stroke-width="${inner}" stroke-linecap="round" stroke-linejoin="round"/>`
}

function arrowHead(tip: [number, number], deg: number, size = 9): string {
  const rad = (deg * Math.PI) / 180
  const back = 11
  const base: [number, number] = [
    tip[0] - Math.cos(rad) * back,
    tip[1] - Math.sin(rad) * back,
  ]
  const left = polar(base[0], base[1], size, deg - 90)
  const right = polar(base[0], base[1], size, deg + 90)
  return `<polygon points="${tip[0].toFixed(1)},${tip[1].toFixed(1)} ${left[0].toFixed(1)},${left[1].toFixed(1)} ${right[0].toFixed(1)},${right[1].toFixed(1)}" fill="${TAKEN}" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>`
}

function roundaboutSvg(cue: GuidanceCue, emphasized: boolean): string {
  const arms = Math.max(3, Math.min(7, cue.arms ?? 4))
  const exit = Math.max(1, Math.min(arms - 1, cue.exit ?? 1))
  let armDeg = (cue.arm_deg ?? []).filter((d) => Number.isFinite(d))
  if (armDeg.length < arms) {
    armDeg = Array.from({ length: arms }, (_, i) => (i * 360) / arms)
  } else {
    armDeg = armDeg.slice(0, arms)
  }
  const cx = 60
  const cy = 60
  const ringR = 24
  const roadR = 52
  const numbered = armDeg
    .map((deg) => deg)
    .filter((deg) => deg % 360 !== 0)
    .sort((a, b) => (a % 360) - (b % 360))
  const roads = armDeg
    .map((deg) => {
      const a = polar(cx, cy, 10, svgAngle(deg))
      const b = polar(cx, cy, roadR, svgAngle(deg))
      return `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" stroke="${INK}" stroke-width="13" stroke-linecap="butt"/><line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" stroke="${ROAD_FILL}" stroke-width="9" stroke-linecap="butt"/>`
    })
    .join('')
  const takenDeg = numbered[exit - 1] ?? 180
  const start = polar(cx, cy, ringR, svgAngle(0))
  const endRing = polar(cx, cy, ringR, svgAngle(takenDeg))
  const endRoad = polar(cx, cy, roadR - 1, svgAngle(takenDeg))
  const entry = polar(cx, cy, roadR - 1, svgAngle(0))
  const large = takenDeg > 180 ? 1 : 0
  const path = [
    `M ${entry[0].toFixed(1)} ${entry[1].toFixed(1)}`,
    `L ${start[0].toFixed(1)} ${start[1].toFixed(1)}`,
    `A ${ringR} ${ringR} 0 ${large} 1 ${endRing[0].toFixed(1)} ${endRing[1].toFixed(1)}`,
    `L ${endRoad[0].toFixed(1)} ${endRoad[1].toFixed(1)}`,
  ].join(' ')
  const outer = emphasized ? 11 : 9.5
  const inner = emphasized ? 7 : 5.8
  const numbers = numbered
    .map((deg, i) => {
      const n = i + 1
      const [x, y] = polar(cx, cy, 38, svgAngle(deg))
      const active = n === exit
      return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="9.2" fill="${active ? TAKEN : '#fff'}" stroke="${active ? TAKEN_DARK : INK}" stroke-width="2.2"/><text x="${x.toFixed(1)}" y="${(y + 4.2).toFixed(1)}" text-anchor="middle" font-size="11.5" font-weight="900" font-family="ui-sans-serif,system-ui,sans-serif" fill="${active ? '#fff' : INK}">${n}</text>`
    })
    .join('')
  return `<rect x="2" y="2" width="116" height="116" rx="14" fill="#fff"/>${roads}<circle cx="${cx}" cy="${cy}" r="${ringR + 8}" fill="${ROAD_FILL}" stroke="${INK}" stroke-width="12"/><circle cx="${cx}" cy="${cy}" r="${ringR + 8}" fill="none" stroke="${ROAD}" stroke-width="8"/><circle cx="${cx}" cy="${cy}" r="${ringR - 8}" fill="#fff" stroke="${INK}" stroke-width="1.4"/>${dualStroke(path, outer, inner)}${arrowHead(endRoad, svgAngle(takenDeg))}${numbers}`
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
