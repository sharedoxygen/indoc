import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'
import { buildTicks, describeSemiArc, polar } from './instrumentGeometry'

/** Classic analog needle gauge — graduated scale, counterweighted needle, bezel. */
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
  const uid = useId().replace(/:/g, '')
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size * 0.64
  const r = size * 0.38
  const angle = 180 * ratio
  const dark = theme.palette.mode === 'dark'
  const faceEdge = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
  const tickColor = dark ? 'rgba(230,235,240,0.52)' : 'rgba(30,35,40,0.42)'
  const track = describeSemiArc(cx, cy, r, 0, 180)

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: 0,
        sweep: 180,
        count: 24,
        majorEvery: 4,
        zeroAt: -180,
        labelMin: min,
        labelMax: max,
        labelPrecision: max > 100 ? 0 : 0,
        labelR: r - 13,
      }),
    [cx, cy, r, min, max]
  )

  return (
    <Box sx={{ width: size, textAlign: 'center', userSelect: 'none' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.8 }}>
        <svg width={size} height={size * 0.8} viewBox={`0 0 ${size} ${size * 0.82}`}>
          <defs>
            <linearGradient id={`ngbezel-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={dark ? '#66707a' : '#f4f6f8'} />
              <stop offset="50%" stopColor={dark ? '#2a3038' : '#c9d0d7'} />
              <stop offset="100%" stopColor={dark ? '#12161c' : '#9aa3ad'} />
            </linearGradient>
            <radialGradient id={`ngface-${uid}`} cx="40%" cy="30%" r="70%">
              <stop offset="0%" stopColor={dark ? '#1b2129' : '#ffffff'} />
              <stop offset="100%" stopColor={dark ? '#0b0e12' : '#e7ebef'} />
            </radialGradient>
          </defs>

          {/* Housing */}
          <path
            d={`${track} L ${cx + r + 10} ${cy} A ${r + 10} ${r + 10} 0 0 0 ${cx - r - 10} ${cy} Z`}
            fill={`url(#ngbezel-${uid})`}
            opacity={0.9}
          />
          <path
            d={`${track} L ${cx + r + 6} ${cy} A ${r + 6} ${r + 6} 0 0 0 ${cx - r - 6} ${cy} Z`}
            fill={`url(#ngface-${uid})`}
          />

          <path d={track} fill="none" stroke={faceEdge} strokeWidth={1.2} strokeLinecap="butt" />

          {/* Zone band (warn/error) */}
          {(status === 'warn' || status === 'error') && (
            <path
              d={describeSemiArc(cx, cy, r, 135, 180)}
              fill="none"
              stroke={stroke}
              strokeWidth={2}
              strokeLinecap="butt"
              opacity={0.28}
            />
          )}

          {ticks.map((t, i) => (
            <g key={i}>
              <line
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={tickColor}
                strokeWidth={t.major ? 1.05 : 0.4}
                opacity={t.major ? 0.9 : 0.38}
              />
              {t.label != null && t.lx != null && t.ly != null && (
                <text
                  x={t.lx}
                  y={t.ly}
                  fill={tickColor}
                  fontSize={Math.max(7, size * 0.055)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {t.label}
                </text>
              )}
            </g>
          ))}

          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            initial={animate && !reduceMotion ? { rotate: -90 } : false}
            animate={{ rotate: -90 + angle }}
            transition={{ type: 'spring', stiffness: 115, damping: 17, mass: 0.55 }}
          >
            {/* Counterweight + blade */}
            <line x1={cx} y1={cy + 9} x2={cx} y2={cy - r + 11} stroke={stroke} strokeWidth={1.2} strokeLinecap="round" />
            <polygon
              points={`${cx - 1.1},${cy - r + 14} ${cx + 1.1},${cy - r + 14} ${cx},${cy - r + 8}`}
              fill={stroke}
            />
            <circle cx={cx} cy={cy} r={3.6} fill={dark ? '#3a424c' : '#c5CCD4'} stroke={stroke} strokeWidth={0.75} />
            <circle cx={cx} cy={cy} r={1.4} fill={theme.palette.background.paper} />
          </motion.g>
        </svg>

        <Box sx={{ position: 'absolute', left: 0, right: 0, bottom: 2, textAlign: 'center' }}>
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: size * 0.145,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.03em',
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
                fontWeight: 650,
                textTransform: 'uppercase',
                letterSpacing: 0.9,
                fontSize: Math.max(8, size * 0.06),
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
