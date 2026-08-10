import React from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'

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
  const angle = -90 + 180 * ratio
  const cx = size / 2
  const cy = size * 0.62
  const r = size * 0.42

  return (
    <Box sx={{ width: size, textAlign: 'center' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.78 }}>
        <svg width={size} height={size * 0.78} viewBox={`0 0 ${size} ${size * 0.8}`}>
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none"
            stroke={theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
            strokeWidth={9}
            strokeLinecap="round"
          />
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none"
            stroke={stroke}
            strokeWidth={9}
            strokeLinecap="round"
            strokeDasharray={`${Math.PI * r}`}
            strokeDashoffset={`${Math.PI * r * (1 - ratio)}`}
            style={{ transition: reduceMotion ? undefined : 'stroke-dashoffset 0.8s ease' }}
            opacity={0.35}
          />
          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            initial={animate && !reduceMotion ? { rotate: -90 } : false}
            animate={{ rotate: angle }}
            transition={{ type: 'spring', stiffness: 90, damping: 16, mass: 0.6 }}
          >
            <line
              x1={cx}
              y1={cy}
              x2={cx}
              y2={cy - r + 8}
              stroke={stroke}
              strokeWidth={2.5}
              strokeLinecap="round"
            />
            <circle cx={cx} cy={cy} r={4.5} fill={stroke} />
            <circle cx={cx} cy={cy} r={2} fill={theme.palette.background.paper} />
          </motion.g>
        </svg>
        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 2, textAlign: 'center' }}>
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: size * 0.16,
              fontVariantNumeric: 'tabular-nums',
              color: 'text.primary',
              lineHeight: 1.1,
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
                fontSize: Math.max(9, size * 0.075),
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
