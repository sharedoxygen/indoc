import React, { useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'

const Polar = ({
  cx,
  cy,
  r,
  angleDeg,
}: {
  cx: number
  cy: number
  r: number
  angleDeg: number
}) => {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = Polar({ cx, cy, r, angleDeg: endAngle })
  const end = Polar({ cx, cy, r, angleDeg: startAngle })
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

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
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.38
  const track = describeArc(cx, cy, r, 135, 405)
  const sweep = 270 * ratio
  const valueArc = describeArc(cx, cy, r, 135, 135 + sweep)
  const ticks = useMemo(() => {
    const items: { x1: number; y1: number; x2: number; y2: number }[] = []
    for (let i = 0; i <= 20; i++) {
      const a = 135 + (270 * i) / 20
      const outer = Polar({ cx, cy, r: r + 6, angleDeg: a })
      const inner = Polar({ cx, cy, r: i % 5 === 0 ? r - 4 : r - 1, angleDeg: a })
      items.push({ x1: inner.x, y1: inner.y, x2: outer.x, y2: outer.y })
    }
    return items
  }, [cx, cy, r])

  return (
    <Box sx={{ width: size, textAlign: 'center', userSelect: 'none' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.85 }}>
        <svg width={size} height={size * 0.85} viewBox={`0 0 ${size} ${size}`}>
          <defs>
            <filter id={`dialGlow-${stroke}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path
            d={track}
            fill="none"
            stroke={theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}
            strokeWidth={10}
            strokeLinecap="round"
          />
          {ticks.map((t, i) => (
            <line
              key={i}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={theme.palette.text.disabled}
              strokeWidth={i % 5 === 0 ? 1.5 : 0.8}
              opacity={0.55}
            />
          ))}
          <motion.path
            d={valueArc}
            fill="none"
            stroke={stroke}
            strokeWidth={10}
            strokeLinecap="round"
            filter={`url(#dialGlow-${stroke})`}
            initial={animate && !reduceMotion ? { pathLength: 0 } : false}
            animate={{ pathLength: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.85, ease: [0.22, 1, 0.36, 1] }}
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
            pt: 1,
          }}
        >
          <Typography
            component={motion.div}
            key={formatInstrumentValue(value, precision, unit)}
            initial={reduceMotion ? false : { opacity: 0.4, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            sx={{
              fontWeight: 700,
              fontSize: size * 0.18,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              color: 'text.primary',
            }}
          >
            {formatInstrumentValue(value, precision, unit)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              sx={{
                mt: 0.5,
                color: 'text.secondary',
                fontWeight: 600,
                letterSpacing: 0.4,
                textTransform: 'uppercase',
                fontSize: Math.max(9, size * 0.07),
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
