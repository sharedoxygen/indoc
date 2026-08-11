import React, { useId, useMemo } from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import type { InstrumentBaseProps } from './types'
import { clampRatio, formatInstrumentValue, useInstrumentColor } from './useInstrumentColor'
import { buildTicks, describeSemiArc, polar } from './instrumentGeometry'
import {
  CapJewel,
  InstrumentDefs,
  instrumentPalette,
} from './InstrumentChrome'
import { InstrumentTooltip } from './InstrumentHelp'

/** Semi-circular precision meter with numbered graduations and tip marker. */
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
  help,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const stroke = useInstrumentColor(status, color)
  const uid = useId().replace(/:/g, '')
  const ratio = clampRatio(value, min, max)
  const cx = size / 2
  const cy = size * 0.64
  const r = size * 0.38
  const track = describeSemiArc(cx, cy, r, 0, 180)
  const valuePath = describeSemiArc(cx, cy, r, 0, 180 * ratio)
  const dark = theme.palette.mode === 'dark'
  const p = instrumentPalette(dark)
  const tip = polar(cx, cy, r - 6, 180 * ratio, -180)

  const ticks = useMemo(
    () =>
      buildTicks({
        cx,
        cy,
        r,
        startAngle: 0,
        sweep: 180,
        count: 30,
        majorEvery: 5,
        zeroAt: -180,
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
      aria-label={label ? `${label} meter` : 'Arc meter'}
    >
      <Box sx={{ position: 'relative', width: size, height: size * 0.74 }}>
        <svg width={size} height={size * 0.74} viewBox={`0 0 ${size} ${size * 0.78}`}>
          <InstrumentDefs uid={uid} dark={dark} />

          {/* Bezel channel */}
          <path
            d={track}
            fill="none"
            stroke={`url(#bez-${uid})`}
            strokeWidth={9}
            strokeLinecap="butt"
            filter={`url(#depth-${uid})`}
            opacity={0.95}
          />
          <path
            d={track}
            fill="none"
            stroke={`url(#face-${uid})`}
            strokeWidth={5.5}
            strokeLinecap="butt"
          />
          <path d={track} fill="none" stroke={p.edge} strokeWidth={1.15} strokeLinecap="butt" />

          {ticks.map((t, i) => (
            <g key={i}>
              <line
                x1={t.x1}
                y1={t.y1}
                x2={t.x2}
                y2={t.y2}
                stroke={t.major ? p.tick : p.tickMinor}
                strokeWidth={t.major ? 1 : 0.4}
              />
              {t.label != null && t.lx != null && t.ly != null && (
                <text
                  x={t.lx}
                  y={t.ly}
                  fill={p.tick}
                  fontSize={Math.max(6.5, size * 0.055)}
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
            strokeWidth={1.7}
            strokeLinecap="butt"
            initial={animate && !reduceMotion ? { pathLength: 0, opacity: 0.5 } : false}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{ duration: reduceMotion ? 0 : 0.7, ease: 'easeOut' }}
          />

          <line
            x1={cx}
            y1={cy}
            x2={tip.x}
            y2={tip.y}
            stroke={stroke}
            strokeWidth={1.05}
            strokeLinecap="round"
            filter={`url(#needle-sh-${uid})`}
          />
          <circle cx={tip.x} cy={tip.y} r={2} fill={stroke} stroke="#f4f7fa" strokeWidth={0.4} />
          <CapJewel uid={uid} cx={cx} cy={cy} accent={stroke} r={3.2} />
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
              fontSize: size * 0.15,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '-0.03em',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              color: 'text.primary',
              textShadow: dark ? '0 1px 2px rgba(0,0,0,0.65)' : undefined,
            }}
          >
            {formatInstrumentValue(value, precision, unit)}
          </Typography>
          {label && (
            <Typography
              variant="caption"
              sx={{
                color: 'text.secondary',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: 1,
                fontSize: Math.max(7.5, size * 0.06),
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
    </InstrumentTooltip>
  )
}

export default ArcMeter
