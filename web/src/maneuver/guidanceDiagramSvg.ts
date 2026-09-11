import type { GuidanceCue } from './guidanceCues'

function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = (deg * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

function svgAngle(armDeg: number): number {
  return 90 + armDeg
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
  const ringR = 22
  const roadR = 48
  const numbered = armDeg
    .map((deg, index) => ({ deg, index }))
    .filter((arm) => arm.deg % 360 !== 0)
    .sort((a, b) => (a.deg % 360) - (b.deg % 360))
  const roads = armDeg
    .map((deg) => {
      const a = polar(cx, cy, 8, svgAngle(deg))
      const b = polar(cx, cy, roadR, svgAngle(deg))
      return `<line x1="${a[0].toFixed(1)}" y1="${a[1].toFixed(1)}" x2="${b[0].toFixed(1)}" y2="${b[1].toFixed(1)}" stroke="#94a3b8" stroke-width="9" stroke-linecap="butt"/>`
    })
    .join('')
  const taken = numbered[exit - 1] ?? numbered[0]
  const takenDeg = taken?.deg ?? 180
  const start = polar(cx, cy, ringR, svgAngle(0))
  const endRing = polar(cx, cy, ringR, svgAngle(takenDeg))
  const endRoad = polar(cx, cy, roadR - 2, svgAngle(takenDeg))
  const entry = polar(cx, cy, roadR - 2, svgAngle(0))
  const large = takenDeg > 180 ? 1 : 0
  const stroke = emphasized ? 5.5 : 4.2
  const path = [
    `M ${entry[0].toFixed(1)} ${entry[1].toFixed(1)}`,
    `L ${start[0].toFixed(1)} ${start[1].toFixed(1)}`,
    `A ${ringR} ${ringR} 0 ${large} 1 ${endRing[0].toFixed(1)} ${endRing[1].toFixed(1)}`,
    `L ${endRoad[0].toFixed(1)} ${endRoad[1].toFixed(1)}`,
  ].join(' ')
  const numbers = numbered
    .map((arm, i) => {
      const n = i + 1
      const [x, y] = polar(cx, cy, 36, svgAngle(arm.deg))
      const active = n === exit
      return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="7.2" fill="${active ? '#0f766e' : '#fff'}" stroke="${active ? '#134e4a' : '#0f172a'}" stroke-width="1.4"/><text x="${x.toFixed(1)}" y="${(y + 3.4).toFixed(1)}" text-anchor="middle" font-size="9" font-weight="800" fill="${active ? '#fff' : '#0f172a'}">${n}</text>`
    })
    .join('')
  return `${roads}<circle cx="${cx}" cy="${cy}" r="${ringR + 7}" fill="#e2e8f0" stroke="#64748b" stroke-width="11"/><circle cx="${cx}" cy="${cy}" r="${ringR - 7}" fill="#fff"/><path d="${path}" fill="none" stroke="#0f766e" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round"/>${numbers}`
}

function laneSvg(cue: GuidanceCue, emphasized: boolean): string {
  const n = Math.max(3, Math.min(6, cue.lanes ?? 4))
  const turn = cue.turn === 'right' ? 'right' : 'left'
  const target = Math.min(n - 1, Math.max(0, cue.target ?? (turn === 'left' ? 0 : n - 1)))
  const pad = 10
  const top = 18
  const bottom = 108
  const width = (100 - pad * 2) / n
  const lanes = Array.from({ length: n }, (_, i) => {
    const x = pad + i * width
    const active = i === target
    const fill = active ? '#99f6e4' : '#e2e8f0'
    const stroke = active ? '#0f766e' : '#94a3b8'
    const sw = active ? (emphasized ? 3.2 : 2.4) : 1.1
    return `<rect x="${x.toFixed(1)}" y="${top}" width="${(width - 3).toFixed(1)}" height="${bottom - top}" rx="3" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`
  }).join('')
  const tx = pad + target * width + (width - 3) / 2
  const arrow =
    turn === 'left'
      ? `M ${tx.toFixed(1)} 96 L ${tx.toFixed(1)} 34 L ${(tx - 14).toFixed(1)} 34`
      : `M ${tx.toFixed(1)} 96 L ${tx.toFixed(1)} 34 L ${(tx + 14).toFixed(1)} 34`
  return `${lanes}<path d="${arrow}" fill="none" stroke="#0f766e" stroke-width="${emphasized ? 5 : 4}" stroke-linecap="round" stroke-linejoin="round"/><polygon points="${turn === 'left' ? `${tx - 20},34 ${tx - 10},28 ${tx - 10},40` : `${tx + 20},34 ${tx + 10},28 ${tx + 10},40`}" fill="#0f766e"/>`
}

function bridgeSvg(cue: GuidanceCue, emphasized: boolean): string {
  const over = cue.relation !== 'under'
  const upper = over ? '#0f766e' : '#94a3b8'
  const lower = over ? '#94a3b8' : '#0f766e'
  const uw = over ? (emphasized ? 6 : 5) : 3
  const lw = over ? 3 : emphasized ? 6 : 5
  const icon = `<g transform="translate(48 18)" fill="none" stroke="#0f172a" stroke-width="1.8" stroke-linecap="round"><path d="M2 16 L2 10 Q14 -2 26 10 L26 16"/><path d="M2 16 L26 16"/><path d="M8 16 L8 12"/><path d="M20 16 L20 12"/></g>`
  return `${icon}<line x1="14" y1="58" x2="106" y2="58" stroke="${upper}" stroke-width="${uw}" stroke-linecap="round"/><path d="M18 58 Q60 42 102 58" fill="none" stroke="${upper}" stroke-width="${over ? 2.4 : 1.6}" opacity="${over ? 1 : 0.55}"/><line x1="18" y1="88" x2="102" y2="88" stroke="${lower}" stroke-width="${lw}" stroke-linecap="round"/><path d="M34 88 L46 72 L74 72 L86 88" fill="none" stroke="${lower}" stroke-width="2" opacity="${over ? 0.45 : 1}"/>`
}

export function guidanceDiagramInner(cue: GuidanceCue, emphasized = false): string {
  if (cue.kind === 'lane') return laneSvg(cue, emphasized)
  if (cue.kind === 'bridge') return bridgeSvg(cue, emphasized)
  return roundaboutSvg(cue, emphasized)
}
