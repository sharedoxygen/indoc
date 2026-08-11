/** Shared geometry helpers for precision instrument faces. */

export function polar(cx: number, cy: number, r: number, angleDeg: number, zeroAt = -90) {
  const rad = ((angleDeg + zeroAt) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

/** SVG arc path. Angles in degrees; 0 = east, increasing clockwise when sweepFlag=1. */
export function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  zeroAt = -90
) {
  const start = polar(cx, cy, r, endAngle, zeroAt)
  const end = polar(cx, cy, r, startAngle, zeroAt)
  const delta = ((endAngle - startAngle) % 360 + 360) % 360
  const largeArc = delta > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

export function describeSemiArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  // Semi gauges use 0=left (-180 math) → 180=right; convert to standard polar with zeroAt=-180
  const start = polar(cx, cy, r, startDeg, -180)
  const end = polar(cx, cy, r, endDeg, -180)
  const large = endDeg - startDeg > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`
}

export type Tick = {
  x1: number
  y1: number
  x2: number
  y2: number
  major: boolean
  label?: string
  lx?: number
  ly?: number
}

export function buildTicks(opts: {
  cx: number
  cy: number
  r: number
  startAngle: number
  sweep: number
  count: number
  majorEvery: number
  zeroAt?: number
  labelMin?: number
  labelMax?: number
  labelPrecision?: number
  labelR?: number
}): Tick[] {
  const {
    cx,
    cy,
    r,
    startAngle,
    sweep,
    count,
    majorEvery,
    zeroAt = -90,
    labelMin,
    labelMax,
    labelPrecision = 0,
    labelR,
  } = opts
  const items: Tick[] = []
  for (let i = 0; i <= count; i++) {
    const major = i % majorEvery === 0
    const a = startAngle + (sweep * i) / count
    const outer = polar(cx, cy, r + (major ? 4.5 : 2.5), a, zeroAt)
    const inner = polar(cx, cy, r - (major ? 6 : 2.5), a, zeroAt)
    const tick: Tick = { x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y, major }
    if (major && labelMin != null && labelMax != null && labelR) {
      const t = i / count
      const value = labelMin + (labelMax - labelMin) * t
      const lp = polar(cx, cy, labelR, a, zeroAt)
      tick.label = value.toFixed(labelPrecision)
      tick.lx = lp.x
      tick.ly = lp.y
    }
    items.push(tick)
  }
  return items
}
