import React from 'react'
import { Box, Typography } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'

interface LiveTickerProps {
  value: string | number
  label?: string
  accent?: string
  live?: boolean
}

export const LiveTicker: React.FC<LiveTickerProps> = ({ value, label, accent, live = true }) => {
  const reduceMotion = useReducedMotion()
  const key = String(value)

  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 1 }}>
      {live && (
        <Box
          component={motion.div}
          animate={reduceMotion ? undefined : { opacity: [1, 0.35, 1], scale: [1, 0.85, 1] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          sx={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: accent || 'success.main',
          }}
        />
      )}
      <Box>
        {label && (
          <Typography
            variant="caption"
            sx={{ display: 'block', color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase', fontSize: 10 }}
          >
            {label}
          </Typography>
        )}
        <Typography
          component={motion.div}
          key={key}
          initial={reduceMotion ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          sx={{
            fontWeight: 650,
            fontVariantNumeric: 'tabular-nums',
            lineHeight: 1.2,
            letterSpacing: '-0.02em',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          }}
        >
          {value}
        </Typography>
      </Box>
    </Box>
  )
}

export default LiveTicker
