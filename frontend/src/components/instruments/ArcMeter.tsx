import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'
import { buildTicks, describeSemiArc, polar } from './instrumentGeometry'

/** Semi-circular precision meter with numbered graduations. */
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
  const uid = useId().replace(/:/g, '')
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size * 0.62
  const r = size * 0.36
  const track = describeSemiArc(cx, cy, r, 0, 180)
  const valuePath = describeSemiArc(cx, cy, r, 0, 180 * ratio)
  const dark = theme.palette.mode === 'dark'
  const faceEdge = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
  const tickColor = dark ? 'rgba(230,235,240,0.5)' : 'rgba(30,35,40,0.42)'

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: 0,
        sweep: 180,
        count: 20,
        majorEvery: 5,
        zeroAt: -180,
        labelMin: min,
        labelMax: max,
        labelPrecision: 0,
        labelR: r - 12,
      }),
    [cx, cy, r, min, max]
  )

  const tip = polar(cx, cy, r - 7, 180 * ratio, -180)

  return (
    <Box sx={{ width: size, textAlign: 'center', userSelect: 'none' }}>
      <Box sx={{ position: 'relative', width: size, height: size * 0.72 }}>
        <svg width={size} height={size * 0.72} viewBox={`0 0 ${size} ${size * 0.75}`}>
          <defs>
            <linearGradient id={`arcface-${uid}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)'} />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
            <linearGradient id={`arcbezel-${uid}`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={dark ? '#3a424c' : '#cfd5dc'} />
              <stop offset="50%" stopColor={dark ? '#1a1f26' : '#eef1f4'} />
              <stop offset="100%" stopColor={dark ? '#4a5560' : '#b8c0c8'} />
            </linearGradient>
          </defs>

          <path
            d={track}
            fill="none"
            stroke={`url(#arcbezel-${uid})`}
            strokeWidth={7}
            strokeLinecap="butt"
            opacity={0.55}
          />
          <path d={track} fill="none" stroke={faceEdge} strokeWidth={1.35} strokeLinecap="butt" />

          {ticks.map((t, i) => (
            <g key={i}>
              <line
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={tickColor}
                strokeWidth={t.major ? 1 : 0.45}
                opacity={t.major ? 0.9 : 0.4}
              />
              {t.label != null && t.lx != null && t.ly != null && (
                <text
                  x={t.lx}
                  y={t.ly}
                  fill={tickColor}
                  fontSize={Math.max(7, size * 0.06)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {t.label}
                </text>
              )}
            </g>
          ))}

          <motion.path
            d={valuePath}
            fill="none"
            stroke={stroke}
            strokeWidth={1.85}
            strokeLinecap="butt"
            initial={animate && !reduceMotion ? { pathLength: 0, opacity: 0.5 } : false}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.65, ease: 'easeOut' }}
          />

          {/* Pivot + tip marker */}
          <line x1={cx} y1={cy} x2={tip.x} y2={tip.y} stroke={stroke} strokeWidth={1.1} strokeLinecap="round" />
          <circle cx={cx} cy={cy} r={2.8} fill={dark ? '#3a424c' : '#c5CCD4'} stroke={stroke} strokeWidth={0.7} />
          <circle cx={tip.x} cy={tip.y} r={1.7} fill={stroke} />
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
              fontWeight: 600,
              fontSize: size * 0.16,
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
                color: 'text.secondary',
                fontWeight: 650,
                textTransform: 'uppercase',
                letterSpacing: 0.9,
                fontSize: Math.max(8, size * 0.065),
              }}
            >
              {label}
            </Typography>
          )}
          {subtitle && (
            <Typography variant="caption" sx={{ color: 'text.disabled', fontSize: 10, mt: 0.1 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default ArcMeter
