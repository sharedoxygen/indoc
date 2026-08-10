import React from 'react'
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
  const cy = size * 0.62
  const r = size * 0.4
  const track = arcPath(cx, cy, r, 0, 180)
  const valuePath = arcPath(cx, cy, r, 0, 180 * ratio)

  return (
    <Box sx={{ width: size, textAlign: 'center' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.72 }}>
        <svg width={size} height={size * 0.72} viewBox={`0 0 ${size} ${size * 0.75}`}>
          <path
            d={track}
            fill="none"
            stroke={theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
            strokeWidth={8}
            strokeLinecap="round"
          />
          <motion.path
            d={valuePath}
            fill="none"
            stroke={stroke}
            strokeWidth={8}
            strokeLinecap="round"
            initial={animate && !reduceMotion ? { pathLength: 0, opacity: 0.6 } : false}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.7, ease: 'easeOut' }}
          />
        </svg>
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: size * 0.2,
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
                color: 'text.secondary',
                fontWeight: 600,
                textTransform: 'uppercase',
                fontSize: Math.max(9, size * 0.08),
                letterSpacing: 0.3,
              }}
            >
              {label}
            </Typography>
          )}
          {subtitle && (
            <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: 10 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default ArcMeter
