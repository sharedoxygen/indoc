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

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: start,
        sweep,
        count: 54,
        majorEvery: 6,
        labelMin: min,
        labelMax: max,
        labelPrecision: 0,
        labelR: r - 11,
      }),
    [cx, cy, r, min, max]
  )

  return (
    <InstrumentTooltip help={help}>
    <Box
      sx={{ width: size, textAlign: 'center', userSelect: 'none', cursor: help ? 'help' : 'default' }}
      aria-label={label ? `${label} dial` : 'Precision dial'}
    >
      <Box sx={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <InstrumentDefs uid={uid} dark={dark} />
          <CircularHousing uid={uid} cx={cx} cy={cy} outerR={outerR} faceR={faceR} dark={dark} />

          {/* Inner scale rail */}
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
                  fontSize={Math.max(6.5, size * 0.048)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                  opacity={0.9}
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

        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: size * 0.2,
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: size * 0.125,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.03em',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              color: 'text.primary',
              textShadow: dark ? '0 1px 2px rgba(0,0,0,0.65)' : '0 1px 1px rgba(255,255,255,0.8)',
            }}
          >
            {formatInstrumentValue(value, precision, unit)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              sx={{
                mt: 0.3,
                display: 'block',
                color: 'text.secondary',
                fontWeight: 700,
                letterSpacing: 1.2,
                textTransform: 'uppercase',
                fontSize: Math.max(7.5, size * 0.05),
              }}
            >
              {label}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
    </InstrumentTooltip>
  )
}

export default PrecisionDial
