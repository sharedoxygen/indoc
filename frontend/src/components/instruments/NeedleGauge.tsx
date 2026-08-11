import React, { useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 180) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

/** Classic needle gauge — hairline arc, graduated ticks, slim needle. */
export const NeedleGauge: React.FC<InstrumentBaseProps & { displayValue?: string }> = ({
  value,
  max = 100,
  min = 0,
  label,
  unit = '',
  precision = 0,
  size = 120,
  status = 'idle',
  animate = true,
  color,
  displayValue,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const stroke = useInstrumentColor(status, color)
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size * 0.62
  const r = size * 0.4
  const angle = 180 * ratio
  const trackColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'
  const tickColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)'

  const ticks = useMemo(() => {
    const items: { x1: number; y1: number; x2: number; y2: number; major: boolean }[] = []
    for (let i = 0; i <= 20; i++) {
      const major = i % 5 === 0
      const a = (180 * i) / 20
      const outer = polar(cx, cy, r + (major ? 4 : 2.5), a)
      const inner = polar(cx, cy, r - (major ? 5 : 2), a)
      items.push({ x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y, major })
    }
    return items
  }, [cx, cy, r])

  const tip = polar(cx, cy, r - 7, angle)
  const start = polar(cx, cy, r, 0)
  const end = polar(cx, cy, r, 180)
  const track = `M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${end.x} ${end.y}`

  return (
    <Box sx={{ width: size, textAlign: 'center' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.78 }}>
        <svg width={size} height={size * 0.78} viewBox={`0 0 ${size} ${size * 0.8}`}>
          <path d={track} fill="none" stroke={trackColor} strokeWidth={1.75} strokeLinecap="butt" />
          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={tickColor}
              strokeWidth={t.major ? 1.05 : 0.5}
              opacity={t.major ? 0.85 : 0.4}
            />
          ))}
          {/* Danger / warn bands for failure-style meters */}
          {status === 'error' || status === 'warn' ? (
            <path
              d={track}
              fill="none"
              stroke={stroke}
              strokeWidth={1.75}
              strokeLinecap="butt"
              strokeDasharray={`${Math.PI * r * 0.25} ${Math.PI * r}`}
              strokeDashoffset={0}
              opacity={0.35}
            />
          ) : null}
          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            initial={animate && !reduceMotion ? { rotate: -90 } : false}
            animate={{ rotate: -90 + angle }}
            transition={{ type: 'spring', stiffness: 110, damping: 18, mass: 0.55 }}
          >
            <line
              x1={cx}
              y1={cy}
              x2={cx}
              y2={cy - r + 10}
              stroke={stroke}
              strokeWidth={1.5}
              strokeLinecap="round"
            />
            <circle cx={cx} cy={cy} r={3.4} fill={stroke} />
            <circle cx={cx} cy={cy} r={1.5} fill={theme.palette.background.paper} />
          </motion.g>
          <circle cx={tip.x} cy={tip.y} r={1.6} fill={stroke} opacity={0.9} />
        </svg>
        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 2, textAlign: 'center' }}>
          <Typography
            sx={{
              fontWeight: 650,
              fontSize: size * 0.15,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.02em',
              color: 'text.primary',
              lineHeight: 1.1,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            }}
          >
            {displayValue ?? formatInstrumentValue(value, precision, unit)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              sx={{
                color: 'text.secondary',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 0.7,
                fontSize: Math.max(9, size * 0.068),
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

export default NeedleGauge
