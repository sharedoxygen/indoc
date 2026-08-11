import React from 'react'
import { Box, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'

export type SegmentStatus = 'pending' | 'active' | 'complete' | 'failed'

export interface RingSegment {
  key: string
  label: string
  status: SegmentStatus
  value?: number
}

interface SegmentRingProps {
  segments: RingSegment[]
  size?: number
  centerLabel?: string
  centerValue?: string
}

/** Segmented ring + readable stage list (no crowded pill strip). */
export const SegmentRing: React.FC<SegmentRingProps> = ({
  segments,
  size = 180,
  centerLabel,
  centerValue,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.34
  const stroke = size * 0.045
  const gap = 3.5
  const n = Math.max(segments.length, 1)
  const sweep = 360 / n - gap

  const statusColor = (status: SegmentStatus) => {
    switch (status) {
      case 'complete':
        return theme.palette.success.main
      case 'active':
        return theme.palette.primary.main
      case 'failed':
        return theme.palette.error.main
      default:
        return theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.14)' : 'rgba(0,0,0,0.12)'
    }
  }

  return (
    <Box sx={{ width: '100%', maxWidth: size + 40 }}>
      <Box sx={{ width: size, position: 'relative', mx: 'auto' }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}
            strokeWidth={stroke}
          />
          {segments.map((seg, i) => {
            const start = -90 + i * (360 / n) + gap / 2
            const radStart = (start * Math.PI) / 180
            const radEnd = ((start + sweep) * Math.PI) / 180
            const x1 = cx + r * Math.cos(radStart)
            const y1 = cy + r * Math.sin(radStart)
            const x2 = cx + r * Math.cos(radEnd)
            const y2 = cy + r * Math.sin(radEnd)
            const d = `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`
            const color = statusColor(seg.status)
            return (
              <motion.path
                key={seg.key}
                d={d}
                fill="none"
                stroke={color}
                strokeWidth={stroke}
                strokeLinecap="butt"
                initial={reduceMotion ? false : { opacity: 0.45 }}
                animate={{
                  opacity: seg.status === 'active' ? [0.55, 1, 0.55] : 1,
                }}
                transition={
                  seg.status === 'active' && !reduceMotion
                    ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' }
                    : { duration: 0.35 }
                }
              />
            )
          })}
        </svg>
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          {centerValue && (
            <Typography
              sx={{
                fontWeight: 650,
                fontSize: size * 0.13,
                fontVariantNumeric: 'tabular-nums',
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              }}
            >
              {centerValue}
            </Typography>
          )}
          {centerLabel && (
            <Typography
              variant="caption"
              sx={{
                color: 'text.secondary',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 0.7,
                fontSize: 10,
              }}
            >
              {centerLabel}
            </Typography>
          )}
        </Box>
      </Box>

      <Box sx={{ mt: 1.25, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {segments.map((seg) => {
          const color = statusColor(seg.status)
          return (
            <Box
              key={seg.key}
              sx={{
                display: 'grid',
                gridTemplateColumns: '8px 1fr auto',
                alignItems: 'center',
                gap: 1,
                px: 0.25,
              }}
            >
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  bgcolor: color,
                  boxShadow: seg.status === 'active' ? `0 0 0 2px ${color}33` : 'none',
                }}
              />
              <Typography
                variant="caption"
                sx={{
                  color: seg.status === 'pending' ? 'text.disabled' : 'text.primary',
                  fontWeight: seg.status === 'active' ? 700 : 500,
                  letterSpacing: 0.2,
                }}
              >
                {seg.label}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: 'text.secondary',
                  fontVariantNumeric: 'tabular-nums',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                  fontSize: 11,
                }}
              >
                {typeof seg.value === 'number' ? seg.value : '—'}
              </Typography>
            </Box>
          )
        })}
      </Box>
    </Box>
  )
}

export default SegmentRing
