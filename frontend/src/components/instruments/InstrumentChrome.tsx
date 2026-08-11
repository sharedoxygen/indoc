import React from 'react'
import { polar } from './instrumentGeometry'

/** Shared machined-bezel / glass-face chrome for laboratory-grade dials. */

export function instrumentPalette(dark: boolean) {
  return {
    bezelHi: dark ? '#8a949e' : '#f8fafc',
    bezelMid: dark ? '#3a424c' : '#c5ccd4',
    bezelLo: dark ? '#0e1217' : '#8a939d',
    faceHi: dark ? '#222933' : '#ffffff',
    faceMid: dark ? '#141a22' : '#eef1f4',
    faceLo: dark ? '#07090c' : '#d5dae0',
    tick: dark ? 'rgba(228,234,240,0.62)' : 'rgba(28,34,40,0.48)',
    tickMinor: dark ? 'rgba(228,234,240,0.28)' : 'rgba(28,34,40,0.22)',
    edge: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
    recess: dark ? 'rgba(0,0,0,0.55)' : 'rgba(0,0,0,0.12)',
    screw: dark ? '#2c333c' : '#aeb6c0',
    screwHi: dark ? '#6a7380' : '#f0f3f6',
  }
}

export function InstrumentDefs({
  uid,
  dark,
}: {
  uid: string
  dark: boolean
}) {
  const p = instrumentPalette(dark)
  return (
    <defs>
      <linearGradient id={`bez-${uid}`} x1="12%" y1="8%" x2="88%" y2="92%">
        <stop offset="0%" stopColor={p.bezelHi} />
        <stop offset="28%" stopColor={p.bezelMid} />
        <stop offset="62%" stopColor={p.bezelLo} />
        <stop offset="100%" stopColor={p.bezelHi} />
      </linearGradient>
      <linearGradient id={`bez-knurl-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor={dark ? '#5c6672' : '#e8ecf0'} />
        <stop offset="50%" stopColor={dark ? '#1a2028' : '#b0b8c2'} />
        <stop offset="100%" stopColor={dark ? '#6a7480' : '#dfe4e9'} />
      </linearGradient>
      <radialGradient id={`face-${uid}`} cx="36%" cy="30%" r="72%">
        <stop offset="0%" stopColor={p.faceHi} />
        <stop offset="48%" stopColor={p.faceMid} />
        <stop offset="100%" stopColor={p.faceLo} />
      </radialGradient>
      <radialGradient id={`vignette-${uid}`} cx="50%" cy="48%" r="58%">
        <stop offset="55%" stopColor="transparent" />
        <stop offset="100%" stopColor={dark ? 'rgba(0,0,0,0.55)' : 'rgba(0,0,0,0.14)'} />
      </radialGradient>
      <linearGradient id={`glass-${uid}`} x1="20%" y1="0%" x2="80%" y2="100%">
        <stop offset="0%" stopColor="rgba(255,255,255,0.28)" />
        <stop offset="22%" stopColor="rgba(255,255,255,0.08)" />
        <stop offset="48%" stopColor="rgba(255,255,255,0)" />
        <stop offset="100%" stopColor={dark ? 'rgba(0,0,0,0.28)' : 'rgba(0,0,0,0.08)'} />
      </linearGradient>
      <linearGradient id={`needle-${uid}`} x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#f4f7fa" />
        <stop offset="55%" stopColor="#c8d0d8" />
        <stop offset="100%" stopColor="#6a7380" />
      </linearGradient>
      <radialGradient id={`jewel-${uid}`} cx="35%" cy="30%" r="65%">
        <stop offset="0%" stopColor={dark ? '#7a8490' : '#ffffff'} />
        <stop offset="45%" stopColor={dark ? '#3a424c' : '#c5ccd4'} />
        <stop offset="100%" stopColor={dark ? '#12161c' : '#8a939d'} />
      </radialGradient>
      <filter id={`depth-${uid}`} x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="1.6" stdDeviation="1.8" floodOpacity={dark ? 0.55 : 0.28} />
      </filter>
      <filter id={`needle-sh-${uid}`} x="-40%" y="-40%" width="180%" height="180%">
        <feDropShadow dx="0.6" dy="1.1" stdDeviation="0.9" floodOpacity={dark ? 0.65 : 0.35} />
      </filter>
    </defs>
  )
}

/** Full circular housing: knurled outer ring, recessed face, glass, corner screws. */
export function CircularHousing({
  uid,
  cx,
  cy,
  outerR,
  faceR,
  dark,
  screws = true,
}: {
  uid: string
  cx: number
  cy: number
  outerR: number
  faceR: number
  dark: boolean
  screws?: boolean
}) {
  const p = instrumentPalette(dark)
  const knurlCount = 72
  const knurls = Array.from({ length: knurlCount }, (_, i) => {
    const a = (360 * i) / knurlCount
    const o = polar(cx, cy, outerR - 0.5, a)
    const inn = polar(cx, cy, outerR - 3.2, a)
    return { o, inn, major: i % 6 === 0 }
  })
  const screwAngles = [45, 135, 225, 315]
  const screwR = (outerR + faceR) / 2 + 1.5

  return (
    <g>
      <circle
        cx={cx}
        cy={cy}
        r={outerR}
        fill={`url(#bez-${uid})`}
        filter={`url(#depth-${uid})`}
      />
      <circle cx={cx} cy={cy} r={outerR - 1.2} fill={`url(#bez-knurl-${uid})`} />
      {knurls.map((k, i) => (
        <line
          key={i}
          x1={k.inn.x}
          y1={k.inn.y}
          x2={k.o.x}
          y2={k.o.y}
          stroke={k.major ? p.bezelHi : p.edge}
          strokeWidth={k.major ? 0.7 : 0.35}
          opacity={k.major ? 0.55 : 0.28}
        />
      ))}
      {/* Recess lip */}
      <circle cx={cx} cy={cy} r={faceR + 2.4} fill={p.recess} opacity={0.85} />
      <circle cx={cx} cy={cy} r={faceR + 1.1} fill="none" stroke={p.edge} strokeWidth={0.6} />
      <circle cx={cx} cy={cy} r={faceR} fill={`url(#face-${uid})`} />
      <circle cx={cx} cy={cy} r={faceR} fill={`url(#vignette-${uid})`} />
      {/* Specular glass crescent */}
      <ellipse
        cx={cx - faceR * 0.12}
        cy={cy - faceR * 0.28}
        rx={faceR * 0.72}
        ry={faceR * 0.38}
        fill={`url(#glass-${uid})`}
        opacity={0.55}
        style={{ mixBlendMode: dark ? 'screen' : 'soft-light' } as React.CSSProperties}
      />
      {screws &&
        screwAngles.map((a) => {
          const s = polar(cx, cy, screwR, a)
          return (
            <g key={a}>
              <circle cx={s.x} cy={s.y} r={2.1} fill={p.screw} stroke={p.screwHi} strokeWidth={0.45} />
              <line
                x1={s.x - 1.1}
                y1={s.y}
                x2={s.x + 1.1}
                y2={s.y}
                stroke={p.screwHi}
                strokeWidth={0.45}
                opacity={0.7}
              />
              <line
                x1={s.x}
                y1={s.y - 1.1}
                x2={s.x}
                y2={s.y + 1.1}
                stroke={p.screwHi}
                strokeWidth={0.45}
                opacity={0.7}
              />
            </g>
          )
        })}
    </g>
  )
}

/** Cap-jewel pivot (watch/avionics hub). */
export function CapJewel({
  uid,
  cx,
  cy,
  accent,
  r = 4.2,
}: {
  uid: string
  cx: number
  cy: number
  accent: string
  r?: number
}) {
  return (
    <g filter={`url(#needle-sh-${uid})`}>
      <circle cx={cx} cy={cy} r={r + 1.4} fill="rgba(0,0,0,0.35)" opacity={0.45} />
      <circle cx={cx} cy={cy} r={r} fill={`url(#jewel-${uid})`} stroke={accent} strokeWidth={0.85} />
      <circle cx={cx} cy={cy} r={r * 0.38} fill="#f2f5f8" opacity={0.9} />
      <circle cx={cx + r * 0.18} cy={cy - r * 0.22} r={r * 0.16} fill="#ffffff" opacity={0.55} />
    </g>
  )
}

/** Tapered hairline needle pointing up from pivot (rotate via transform). */
export function HairlineNeedle({
  uid,
  cx,
  cy,
  length,
  accent,
  counterweight = 10,
}: {
  uid: string
  cx: number
  cy: number
  length: number
  accent: string
  counterweight?: number
}) {
  const tipY = cy - length
  return (
    <g filter={`url(#needle-sh-${uid})`}>
      <line
        x1={cx}
        y1={cy + counterweight}
        x2={cx}
        y2={cy + 2}
        stroke={`url(#needle-${uid})`}
        strokeWidth={2.2}
        strokeLinecap="round"
        opacity={0.85}
      />
      <polygon
        points={`${cx - 1.15},${cy + 1} ${cx + 1.15},${cy + 1} ${cx + 0.35},${tipY + 6} ${cx},${tipY} ${cx - 0.35},${tipY + 6}`}
        fill={accent}
      />
      <line
        x1={cx}
        y1={cy + 1}
        x2={cx}
        y2={tipY + 8}
        stroke="rgba(255,255,255,0.35)"
        strokeWidth={0.35}
      />
    </g>
  )
}
