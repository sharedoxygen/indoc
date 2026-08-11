import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polar(cx, cy, r, endAngle)
  const end = polar(cx, cy, r, startAngle)
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

/** 270° precision dial — fine ticks, thin track, no glow. */
export const PrecisionDial: React.FC<InstrumentBaseProps> = ({
  value,
  max = 100,
  min = 0,
  label,
  unit = '%',
  precision = 1,
  size = 140,
  status = 'idle',
  animate = true,
  color,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const stroke = useInstrumentColor(status, color)
  const uid = useId()
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.36
  const track = describeArc(cx, cy, r, 135, 405)
  const sweep = 270 * ratio
  const valueArc = describeArc(cx, cy, r, 135, 135 + sweep)
  const trackColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)'
  const tickColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)'

  const ticks = useMemo(() => {
    const items: { x1: number; y1: number; x2: number; y2: number; major: boolean }[] = []
    for (let i = 0; i <= 40; i++) {
      const major = i % 5 === 0
      const a = 135 + (270 * i) / 40
      const outer = polar(cx, cy, r + (major ? 5 : 3), a)
      const inner = polar(cx, cy, r - (major ? 5 : 2), a)
      items.push({ x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y, major })
    }
    return items
  }, [cx, cy, r])

  const needleAngle = 135 + sweep
  const needleTip = polar(cx, cy, r - 8, needleAngle)
  const needleTail = polar(cx, cy, 8, needleAngle + 180)

  return (
    <Box sx={{ width: size, textAlign: 'center', userSelect: 'none' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.88 }}>
        <svg width={size} height={size * 0.88} viewBox={`0 0 ${size} ${size}`}>
          <defs>
            <linearGradient id={`${uid}-face`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop
                offset="0%"
                stopColor={theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)'}
              />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
          </defs>
          <circle cx={cx} cy={cy} r={r + 10} fill={`url(#${uid}-face)`} stroke={trackColor} strokeWidth={0.75} />
          <path d={track} fill="none" stroke={trackColor} strokeWidth={2.5} strokeLinecap="butt" />
          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={tickColor}
              strokeWidth={t.major ? 1.1 : 0.55}
              opacity={t.major ? 0.85 : 0.45}
            />
          ))}
          <motion.path
            d={valueArc}
            fill="none"
            stroke={stroke}
            strokeWidth={2.75}
            strokeLinecap="butt"
            initial={animate && !reduceMotion ? { pathLength: 0 } : false}
            animate={{ pathLength: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.7, ease: [0.22, 1, 0.36, 1] }}
          />
          <motion.g
            initial={false}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            <line
              x1={needleTail.x}
              y1={needleTail.y}
              x2={needleTip.x}
              y2={needleTip.y}
              stroke={stroke}
              strokeWidth={1.4}
              strokeLinecap="round"
            />
            <circle cx={cx} cy={cy} r={3.2} fill={stroke} />
            <circle cx={cx} cy={cy} r={1.4} fill={theme.palette.background.paper} />
          </motion.g>
        </svg>
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pt: `${size * 0.12}px`,
            pointerEvents: 'none',
          }}
        >
          <Typography
            sx={{
              fontWeight: 650,
              fontSize: size * 0.155,
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
                mt: 0.4,
                color: 'text.secondary',
                fontWeight: 600,
                letterSpacing: 0.8,
                textTransform: 'uppercase',
                fontSize: Math.max(9, size * 0.062),
              }}
            >
              {label}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default PrecisionDial
