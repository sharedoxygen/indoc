import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import { buildTicks, polar } from './instrumentGeometry'
import {
  CircularHousing,
  InstrumentDefs,
  instrumentPalette,
} from './InstrumentChrome'
import { InstrumentTooltip, type InstrumentHelpProp } from './InstrumentHelp'

export type SegmentStatus = 'pending' | 'active' | 'complete' | 'failed'

export interface RingSegment {
  key: string
  label: string
  status: SegmentStatus
  value?: number
  help?: InstrumentHelpProp
}

interface SegmentRingProps {
  segments: RingSegment[]
  size?: number
  centerLabel?: string
  centerValue?: string
  /** Hide the stage list under the ring (cluster layouts). */
  showLegend?: boolean
  /** Hover help for the chronograph face. */
  help?: InstrumentHelpProp
}

/** Chronograph-style stage dial — knurled bezel, fine ticks, thin stage arcs (not chunky donut). */
export const SegmentRing: React.FC<SegmentRingProps> = ({
  segments,
  size = 180,
  centerLabel,
  centerValue,
  showLegend = true,
  help,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const uid = useId().replace(/:/g, '')
  const dark = theme.palette.mode === 'dark'
  const p = instrumentPalette(dark)
  const cx = size / 2
  const cy = size / 2
  const outerR = size * 0.48
  const faceR = size * 0.385
  const r = size * 0.3
  const n = Math.max(segments.length, 1)
  const gap = 4
  const sweep = 360 / n - gap

  const statusColor = (status: SegmentStatus) => {
    switch (status) {
      case 'complete':
        return theme.palette.success.main
      case 'active':
        return theme.palette.warning.main
      case 'failed':
        return theme.palette.error.main
      default:
        return dark ? 'rgba(255,255,255,0.16)' : 'rgba(0,0,0,0.14)'
    }
  }

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r: r + 2,
        startAngle: 0,
        sweep: 360,
        count: 60,
        majorEvery: 5,
        zeroAt: -90,
      }),
    [cx, cy, r]
  )

  return (
    <Box sx={{ width: '100%', maxWidth: size + 40 }}>
      <InstrumentTooltip help={help}>
      <Box
        sx={{ width: size, position: 'relative', mx: 'auto', cursor: help ? 'help' : 'default' }}
        aria-label="Instrument chronograph"
      >
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <InstrumentDefs uid={uid} dark={dark} />
          <CircularHousing uid={uid} cx={cx} cy={cy} outerR={outerR} faceR={faceR} dark={dark} />

          {/* Minute track */}
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={p.edge} strokeWidth={0.9} />
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={dark ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.08)'}
            strokeWidth={5}
            opacity={0.7}
          />

          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={t.major ? p.tick : p.tickMinor}
              strokeWidth={t.major ? 0.9 : 0.35}
            />
          ))}

          {segments.map((seg, i) => {
            const start = -90 + i * (360 / n) + gap / 2
            const radStart = (start * Math.PI) / 180
            const radEnd = ((start + sweep) * Math.PI) / 180
            const x1 = cx + r * Math.cos(radStart)
            const y1 = cy + r * Math.sin(radStart)
            const x2 = cx + r * Math.cos(radEnd)
            const y2 = cy + r * Math.sin(radEnd)
            const d = `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`
            const color = statusColor(seg.status)
            const mid = polar(cx, cy, r - 14, start + sweep / 2 + 90)
            return (
              <g key={seg.key}>
                <motion.path
                  d={d}
                  fill="none"
                  stroke={color}
                  strokeWidth={seg.status === 'active' ? 2.4 : 1.65}
                  strokeLinecap="butt"
                  initial={reduceMotion ? false : { opacity: 0.4 }}
                  animate={{
                    opacity: seg.status === 'active' ? [0.55, 1, 0.55] : seg.status === 'pending' ? 0.35 : 0.95,
                  }}
                  transition={
                    seg.status === 'active' && !reduceMotion
                      ? { duration: 1.7, repeat: Infinity, ease: 'easeInOut' }
                      : { duration: 0.35 }
                  }
                />
                {/* Micro stage index on face */}
                <text
                  x={mid.x}
                  y={mid.y}
                  fill={seg.status === 'pending' ? p.tickMinor : p.tick}
                  fontSize={Math.max(6, size * 0.042)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                  opacity={seg.status === 'pending' ? 0.45 : 0.85}
                >
                  {i + 1}
                </text>
              </g>
            )
          })}

          {/* Inner chronograph well */}
          <circle
            cx={cx}
            cy={cy}
            r={r * 0.42}
            fill={dark ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.06)'}
            stroke={p.edge}
            strokeWidth={0.7}
          />
        </svg>

        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          {centerValue && (
            <Typography
              sx={{
                fontWeight: 650,
                fontSize: size * 0.145,
                fontVariantNumeric: 'tabular-nums',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                lineHeight: 1,
                letterSpacing: '-0.04em',
                textShadow: dark ? '0 1px 3px rgba(0,0,0,0.7)' : undefined,
              }}
            >
              {centerValue}
            </Typography>
          )}
          {centerLabel && (
            <Typography
              variant="caption"
              sx={{
                mt: 0.35,
                color: 'text.secondary',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: 1.4,
                fontSize: Math.max(8, size * 0.048),
              }}
            >
              {centerLabel}
            </Typography>
          )}
        </Box>
      </Box>
      </InstrumentTooltip>

      {showLegend && (
        <Box sx={{ mt: 1.25, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {segments.map((seg) => {
            const color = statusColor(seg.status)
            const row = (
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '8px 1fr auto',
                  alignItems: 'center',
                  gap: 1,
                  px: 0.25,
                  cursor: seg.help ? 'help' : 'default',
                }}
              >
                <Box
                  sx={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    bgcolor: color,
                    boxShadow: seg.status === 'active' ? `0 0 0 2px ${color}33` : 'none',
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{
                    color: seg.status === 'pending' ? 'text.disabled' : 'text.primary',
                    fontWeight: seg.status === 'active' ? 700 : 500,
                    letterSpacing: 0.2,
                  }}
                >
                  {seg.label}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    color: 'text.secondary',
                    fontVariantNumeric: 'tabular-nums',
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    fontSize: 11,
                  }}
                >
                  {typeof seg.value === 'number' ? seg.value : '—'}
                </Typography>
              </Box>
            )
            return (
              <InstrumentTooltip key={seg.key} help={seg.help} placement="left">
                {row}
              </InstrumentTooltip>
            )
          })}
        </Box>
      )}
    </Box>
  )
}

export default SegmentRing
