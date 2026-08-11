import React, { useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 180) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function arcPath(cx: number, cy: number, r: number, start: number, end: number) {
  const s = polar(cx, cy, r, start)
  const e = polar(cx, cy, r, end)
  const large = end - start > 180 ? 1 : 0
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`
}

/** Semi-circular meter with tick marks — thin, instrument-grade. */
export const ArcMeter: React.FC<InstrumentBaseProps & { subtitle?: string }> = ({
  value,
  max = 100,
  min = 0,
  label,
  subtitle,
  unit = '',
  precision = 0,
  size = 110,
  status = 'idle',
  animate = true,
  color,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const stroke = useInstrumentColor(status, color)
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size * 0.58
  const r = size * 0.38
  const track = arcPath(cx, cy, r, 0, 180)
  const valuePath = arcPath(cx, cy, r, 0, 180 * ratio)
  const trackColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'
  const tickColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.32)' : 'rgba(0,0,0,0.32)'

  const ticks = useMemo(() => {
    const items: { x1: number; y1: number; x2: number; y2: number; major: boolean }[] = []
    for (let i = 0; i <= 20; i++) {
      const major = i % 5 === 0
      const a = (180 * i) / 20
      const outer = polar(cx, cy, r + (major ? 4 : 2.5), a)
      const inner = polar(cx, cy, r - (major ? 4 : 1.5), a)
      items.push({ x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y, major })
    }
    return items
  }, [cx, cy, r])

  const tip = polar(cx, cy, r - 6, 180 * ratio)

  return (
    <Box sx={{ width: size, textAlign: 'center' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.7 }}>
        <svg width={size} height={size * 0.7} viewBox={`0 0 ${size} ${size * 0.72}`}>
          <path d={track} fill="none" stroke={trackColor} strokeWidth={2.25} strokeLinecap="butt" />
          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={tickColor}
              strokeWidth={t.major ? 1 : 0.5}
              opacity={t.major ? 0.8 : 0.4}
            />
          ))}
          <motion.path
            d={valuePath}
            fill="none"
            stroke={stroke}
            strokeWidth={2.5}
            strokeLinecap="butt"
            initial={animate && !reduceMotion ? { pathLength: 0, opacity: 0.5 } : false}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.65, ease: 'easeOut' }}
          />
          <circle cx={tip.x} cy={tip.y} r={2.2} fill={stroke} />
          <circle cx={cx} cy={cy} r={2.5} fill={trackColor} />
        </svg>
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Typography
            sx={{
              fontWeight: 650,
              fontSize: size * 0.175,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.02em',
              color: 'text.primary',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            }}
          >
            {formatInstrumentValue(value, precision, unit)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              sx={{
                color: 'text.secondary',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 0.7,
                fontSize: Math.max(9, size * 0.07),
              }}
            >
              {label}
            </Typography>
          )}
          {subtitle && (
            <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: 10, mt: 0.15 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default ArcMeter
