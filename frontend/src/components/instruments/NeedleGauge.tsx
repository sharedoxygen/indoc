import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'
import { buildTicks, describeSemiArc } from './instrumentGeometry'
import {
  CapJewel,
  HairlineNeedle,
  InstrumentDefs,
  instrumentPalette,
} from './InstrumentChrome'
import { InstrumentTooltip } from './InstrumentHelp'

/** Classic analog needle gauge — recessed housing, graduated scale, counterweighted blade. */
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
  help,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const stroke = useInstrumentColor(status, color)
  const uid = useId().replace(/:/g, '')
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size * 0.62
  const r = size * 0.4
  const angle = 180 * ratio
  const dark = theme.palette.mode === 'dark'
  const p = instrumentPalette(dark)
  const track = describeSemiArc(cx, cy, r, 0, 180)
  const housingOuter = describeSemiArc(cx, cy, r + 12, 0, 180)
  const housingInner = describeSemiArc(cx, cy, r + 7, 0, 180)
  const compact = size < 130
  const faceH = size * 0.72

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: 0,
        sweep: 180,
        count: compact ? 24 : 36,
        majorEvery: compact ? 6 : 6,
        zeroAt: -180,
        labelMin: min,
        labelMax: max,
        labelPrecision: 0,
        labelR: r - (compact ? 14 : 12),
        labelEveryMajors: compact ? 2 : 1,
      }),
    [cx, cy, r, min, max, compact]
  )

  const readout = displayValue ?? formatInstrumentValue(value, precision, unit)

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
        aria-label={label ? `${label} gauge` : 'Needle gauge'}
      >
        <Box sx={{ position: 'relative', width: size, height: faceH }}>
          <svg width={size} height={faceH} viewBox={`0 0 ${size} ${size * 0.78}`}>
            <InstrumentDefs uid={uid} dark={dark} />

            <path
              d={`${housingOuter} L ${cx + r + 12} ${cy + 8} L ${cx - r - 12} ${cy + 8} Z`}
              fill={`url(#bez-${uid})`}
              filter={`url(#depth-${uid})`}
            />
            <path
              d={`${housingInner} L ${cx + r + 7} ${cy + 5} L ${cx - r - 7} ${cy + 5} Z`}
              fill={`url(#face-${uid})`}
            />
            <path
              d={`${track} L ${cx + r} ${cy + 3} L ${cx - r} ${cy + 3} Z`}
              fill={`url(#vignette-${uid})`}
              opacity={0.85}
            />
            <ellipse
              cx={cx}
              cy={cy - r * 0.35}
              rx={r * 0.78}
              ry={r * 0.32}
              fill={`url(#glass-${uid})`}
              opacity={0.45}
            />

            <path d={track} fill="none" stroke={p.edge} strokeWidth={1.15} strokeLinecap="butt" />

            {(status === 'warn' || status === 'error') && (
              <path
                d={describeSemiArc(cx, cy, r, 140, 180)}
                fill="none"
                stroke={stroke}
                strokeWidth={2.2}
                strokeLinecap="butt"
                opacity={0.22}
              />
            )}

            {ticks.map((t, i) => (
              <g key={i}>
                <line
                  x1={t.x1}
                  y1={t.y1}
                  x2={t.x2}
                  y2={t.y2}
                  stroke={t.major ? p.tick : p.tickMinor}
                  strokeWidth={t.major ? 1.05 : 0.38}
                />
                {t.label != null && t.lx != null && t.ly != null && (
                  <text
                    x={t.lx}
                    y={t.ly}
                    fill={p.tick}
                    fontSize={Math.max(8, size * 0.058)}
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

            <motion.g
              style={{ transformOrigin: `${cx}px ${cy}px` }}
              initial={animate && !reduceMotion ? { rotate: -90 } : false}
              animate={{ rotate: -90 + angle }}
              transition={{ type: 'spring', stiffness: 108, damping: 16, mass: 0.6 }}
            >
              <HairlineNeedle uid={uid} cx={cx} cy={cy} length={r - 9} accent={stroke} counterweight={11} />
            </motion.g>
            <CapJewel uid={uid} cx={cx} cy={cy} accent={stroke} r={3.8} />

            <rect
              x={cx - r - 10}
              y={cy + 1}
              width={(r + 10) * 2}
              height={5}
              rx={1}
              fill={`url(#bez-${uid})`}
              opacity={0.9}
            />
          </svg>
        </Box>

        <Box sx={{ mt: 0.6, px: 0.5, textAlign: 'center', width: '100%' }}>
          <Typography
            title={readout}
            sx={{
              fontWeight: 700,
              fontSize: Math.max(15, size * 0.145),
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.03em',
              color: 'text.primary',
              lineHeight: 1.15,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              maxWidth: '100%',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {readout}
          </Typography>
          {label && (
            <Typography
              title={label}
              sx={{
                mt: 0.3,
                color: 'text.secondary',
                fontWeight: 750,
                textTransform: 'uppercase',
                letterSpacing: 0.8,
                fontSize: Math.max(11, size * 0.078),
                lineHeight: 1.2,
                display: 'block',
                maxWidth: '100%',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
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

export default NeedleGauge
