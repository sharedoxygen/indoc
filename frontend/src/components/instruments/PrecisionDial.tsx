import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'
import { buildTicks, describeArc } from './instrumentGeometry'

/** 270° Swiss-style precision dial — bezel, graduated ticks, hairline needle. */
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
  const uid = useId().replace(/:/g, '')
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.34
  const start = 135
  const sweep = 270
  const valueEnd = start + sweep * ratio
  const track = describeArc(cx, cy, r, start, start + sweep)
  const valueArc = describeArc(cx, cy, r, start, valueEnd)
  const dark = theme.palette.mode === 'dark'
  const bezel = dark ? '#2a3038' : '#d8dde3'
  const bezelInner = dark ? '#12161c' : '#f3f5f7'
  const tickColor = dark ? 'rgba(230,235,240,0.55)' : 'rgba(30,35,40,0.45)'
  const faceEdge = dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: start,
        sweep,
        count: 40,
        majorEvery: 5,
        labelMin: min,
        labelMax: max,
        labelPrecision: max - min <= 10 ? 0 : 0,
        labelR: r - 14,
      }),
    [cx, cy, r, min, max]
  )

  return (
    <Box sx={{ width: size, textAlign: 'center', userSelect: 'none' }}>
      <Box sx={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <defs>
            <radialGradient id={`face-${uid}`} cx="38%" cy="32%" r="70%">
              <stop offset="0%" stopColor={dark ? '#1c222b' : '#ffffff'} />
              <stop offset="55%" stopColor={bezelInner} />
              <stop offset="100%" stopColor={dark ? '#0a0d11' : '#e8ebef'} />
            </radialGradient>
            <linearGradient id={`bezel-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={dark ? '#5a6570' : '#f7f8fa'} />
              <stop offset="45%" stopColor={bezel} />
              <stop offset="100%" stopColor={dark ? '#15191f' : '#aeb6c0'} />
            </linearGradient>
            <linearGradient id={`glass-${uid}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="rgba(255,255,255,0.22)" />
              <stop offset="40%" stopColor="rgba(255,255,255,0.04)" />
              <stop offset="100%" stopColor="rgba(0,0,0,0.12)" />
            </linearGradient>
            <filter id={`soft-${uid}`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="1.2" floodOpacity="0.35" />
            </filter>
          </defs>

          {/* Outer machined bezel */}
          <circle cx={cx} cy={cy} r={r + 16} fill={`url(#bezel-${uid})`} filter={`url(#soft-${uid})`} />
          <circle cx={cx} cy={cy} r={r + 12.5} fill="none" stroke={faceEdge} strokeWidth={0.75} />
          <circle cx={cx} cy={cy} r={r + 11} fill={`url(#face-${uid})`} />
          <circle cx={cx} cy={cy} r={r + 11} fill={`url(#glass-${uid})`} />

          {/* Fine track */}
          <path d={track} fill="none" stroke={faceEdge} strokeWidth={1.25} strokeLinecap="butt" />

          {ticks.map((t, i) => (
            <g key={i}>
              <line
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={tickColor}
                strokeWidth={t.major ? 1.05 : 0.45}
                opacity={t.major ? 0.9 : 0.4}
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
                  opacity={0.85}
                >
                  {t.label}
                </text>
              )}
            </g>
          ))}

          <motion.path
            d={valueArc}
            fill="none"
            stroke={stroke}
            strokeWidth={1.75}
            strokeLinecap="butt"
            initial={animate && !reduceMotion ? { pathLength: 0 } : false}
            animate={{ pathLength: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.75, ease: [0.22, 1, 0.36, 1] }}
          />

          {/* Needle — drawn vertical, rotated to value angle */}
          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            initial={animate && !reduceMotion ? { rotate: start } : false}
            animate={{ rotate: valueEnd }}
            transition={{ type: 'spring', stiffness: 120, damping: 18 }}
          >
            <line
              x1={cx}
              y1={cy + 9}
              x2={cx}
              y2={cy - r + 10}
              stroke={stroke}
              strokeWidth={1.15}
              strokeLinecap="round"
            />
            <circle cx={cx} cy={cy} r={4} fill={dark ? '#3a424c' : '#c5CCD4'} stroke={stroke} strokeWidth={0.8} />
            <circle cx={cx} cy={cy} r={1.6} fill={theme.palette.background.paper} />
          </motion.g>
        </svg>

        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: size * 0.18,
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: size * 0.14,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.03em',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              color: 'text.primary',
            }}
          >
            {formatInstrumentValue(value, precision, unit)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              sx={{
                mt: 0.35,
                display: 'block',
                color: 'text.secondary',
                fontWeight: 650,
                letterSpacing: 1.1,
                textTransform: 'uppercase',
                fontSize: Math.max(8, size * 0.055),
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
