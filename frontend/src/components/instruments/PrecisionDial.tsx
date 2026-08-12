import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'
import { buildTicks, describeArc } from './instrumentGeometry'
import {
  CapJewel,
  CircularHousing,
  HairlineNeedle,
  InstrumentDefs,
  instrumentPalette,
} from './InstrumentChrome'
import { InstrumentTooltip } from './InstrumentHelp'

/** 270° laboratory precision dial — knurled bezel, glass face, graduated scale, hairline needle. */
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
  help,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const stroke = useInstrumentColor(status, color)
  const uid = useId().replace(/:/g, '')
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size / 2
  const outerR = size * 0.48
  const faceR = size * 0.38
  const r = size * 0.29
  const start = 135
  const sweep = 270
  const valueEnd = start + sweep * ratio
  const track = describeArc(cx, cy, r, start, start + sweep)
  const valueArc = describeArc(cx, cy, r, start, valueEnd)
  const dark = theme.palette.mode === 'dark'
  const p = instrumentPalette(dark)
  const compact = size < 132

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: start,
        sweep,
        count: compact ? 36 : 54,
        majorEvery: compact ? 9 : 6,
        labelMin: min,
        labelMax: max,
        labelPrecision: 0,
        // Keep numerals near the rim so the open face stays clear
        labelR: r + (compact ? 9 : 10),
        labelEveryMajors: compact ? 2 : 1,
      }),
    [cx, cy, r, min, max, compact]
  )

  return (
    <InstrumentTooltip help={help}>
      <Box
        sx={{
          width: size,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          userSelect: 'none',
          cursor: help ? 'help' : 'default',
        }}
        aria-label={label ? `${label} dial` : 'Precision dial'}
      >
        <Box sx={{ position: 'relative', width: size, height: size }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <InstrumentDefs uid={uid} dark={dark} />
            <CircularHousing uid={uid} cx={cx} cy={cy} outerR={outerR} faceR={faceR} dark={dark} />

            <path d={track} fill="none" stroke={p.edge} strokeWidth={1.1} strokeLinecap="butt" />
            <path
              d={track}
              fill="none"
              stroke={dark ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.08)'}
              strokeWidth={4.5}
              strokeLinecap="butt"
              opacity={0.55}
            />

            {ticks.map((t, i) => (
              <g key={i}>
                <line
                  x1={t.x1}
                  y1={t.y1}
                  x2={t.x2}
                  y2={t.y2}
                  stroke={t.major ? p.tick : p.tickMinor}
                  strokeWidth={t.major ? 1.05 : 0.4}
                />
                {t.label != null && t.lx != null && t.ly != null && (
                  <text
                    x={t.lx}
                    y={t.ly}
                    fill={p.tick}
                    fontSize={Math.max(8, size * 0.055)}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                    opacity={0.75}
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
              strokeWidth={1.55}
              strokeLinecap="butt"
              initial={animate && !reduceMotion ? { pathLength: 0 } : false}
              animate={{ pathLength: 1 }}
              transition={{ duration: reduceMotion ? 0 : 0.8, ease: [0.22, 1, 0.36, 1] }}
              opacity={0.92}
            />

            <motion.g
              style={{ transformOrigin: `${cx}px ${cy}px` }}
              initial={animate && !reduceMotion ? { rotate: start } : false}
              animate={{ rotate: valueEnd }}
              transition={{ type: 'spring', stiffness: 110, damping: 18, mass: 0.65 }}
            >
              <HairlineNeedle uid={uid} cx={cx} cy={cy} length={r - 8} accent={stroke} />
            </motion.g>
            <CapJewel uid={uid} cx={cx} cy={cy} accent={stroke} r={4} />
          </svg>
        </Box>

        <Box sx={{ mt: 0.75, px: 0.5, textAlign: 'center', width: '100%' }}>
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: Math.max(16, size * 0.155),
              lineHeight: 1.1,
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
              sx={{
                mt: 0.35,
                color: 'text.secondary',
                fontWeight: 750,
                letterSpacing: 0.8,
                textTransform: 'uppercase',
                fontSize: Math.max(11, size * 0.08),
                lineHeight: 1.2,
              }}
            >
              {label}
            </Typography>
          )}
        </Box>
      </Box>
    </InstrumentTooltip>
  )
}

export default PrecisionDial
