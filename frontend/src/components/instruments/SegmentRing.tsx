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
  const r = size * 0.36
  const stroke = size * 0.07
  const gap = 4
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
        return theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'
    }
  }

  return (
    <Box sx={{ width: size, position: 'relative' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
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
              strokeLinecap="round"
              initial={reduceMotion ? false : { opacity: 0.4 }}
              animate={{
                opacity: seg.status === 'active' ? [0.55, 1, 0.55] : 1,
                strokeWidth: seg.status === 'active' ? [stroke, stroke + 1.5, stroke] : stroke,
              }}
              transition={
                seg.status === 'active' && !reduceMotion
                  ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' }
                  : { duration: 0.4 }
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
          <Typography sx={{ fontWeight: 700, fontSize: size * 0.14, fontVariantNumeric: 'tabular-nums' }}>
            {centerValue}
          </Typography>
        )}
        {centerLabel && (
          <Typography
            variant="caption"
            sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase', fontSize: 10 }}
          >
            {centerLabel}
          </Typography>
        )}
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, justifyContent: 'center', mt: 1 }}>
        {segments.map((seg) => (
          <Typography
            key={seg.key}
            variant="caption"
            sx={{
              px: 0.75,
              py: 0.25,
              borderRadius: 1,
              border: `1px solid ${statusColor(seg.status)}`,
              color: statusColor(seg.status),
              fontWeight: 600,
              fontSize: 10,
            }}
          >
            {seg.label}
            {typeof seg.value === 'number' ? ` ${seg.value}` : ''}
          </Typography>
        ))}
      </Box>
    </Box>
  )
}

export default SegmentRing
