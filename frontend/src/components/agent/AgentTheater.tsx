import React from 'react'
import { Box, Chip, Stack, Typography } from '@mui/material'
import { motion } from 'framer-motion'
import { PrecisionDial, NeedleGauge, LiveTicker } from '../instruments'
import AgentTheaterScene from './AgentTheaterScene'
import type { AgentStep, AgentStreamStatus } from '../../hooks/useAgentStream'

interface AgentTheaterProps {
  status: AgentStreamStatus
  tools: string[]
  steps: AgentStep[]
  holding: boolean
  finalAnswer: string | null
  maxSteps: number
  iterations: number
  stoppedReason: string | null
  error: string | null
  goal?: string
}

export const AgentTheater: React.FC<AgentTheaterProps> = ({
  status,
  tools,
  steps,
  holding,
  finalAnswer,
  maxSteps,
  iterations,
  stoppedReason,
  error,
  goal,
}) => {
  const progress = maxSteps > 0 ? (steps.length / maxSteps) * 100 : 0
  const load = Math.min(100, progress)
  const dialStatus =
    status === 'error' ? 'error' : status === 'completed' ? 'ok' : status === 'running' ? 'active' : 'idle'

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1.5 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1.2, fontWeight: 700 }}>
            Agent Control Tower
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 520 }} noWrap>
            {goal || 'Awaiting clearance'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <LiveTicker
            label="Status"
            value={status.toUpperCase()}
            live={status === 'running' || status === 'connecting'}
            accent={status === 'error' ? 'error.main' : status === 'completed' ? 'success.main' : 'primary.main'}
          />
          {stoppedReason && <Chip size="small" label={stoppedReason} variant="outlined" />}
          {holding && status === 'running' && <Chip size="small" color="warning" label="Holding pattern" />}
        </Stack>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1fr 150px' },
          gap: 1.5,
          flex: 1,
          minHeight: 0,
        }}
      >
        <Box sx={{ minHeight: 420, height: '100%' }}>
          <AgentTheaterScene
            status={status}
            tools={tools}
            steps={steps}
            holding={holding}
            finalAnswer={finalAnswer}
          />
        </Box>

        <Box
          component={motion.div}
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          sx={{
            display: 'flex',
            flexDirection: { xs: 'row', lg: 'column' },
            alignItems: 'center',
            justifyContent: 'space-around',
            gap: 1,
            p: 1.5,
            borderRadius: 3,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <PrecisionDial
            value={progress}
            label="Mission"
            unit="%"
            precision={1}
            size={128}
            status={dialStatus as any}
          />
          <NeedleGauge
            value={load}
            label="Cognitive"
            unit="%"
            precision={0}
            size={118}
            status={status === 'running' ? 'warn' : dialStatus as any}
          />
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
              STEPS
            </Typography>
            <Typography sx={{ fontWeight: 800, fontVariantNumeric: 'tabular-nums', fontSize: 22 }}>
              {steps.length}/{maxSteps}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.disabled' }}>
              iter {iterations || steps.length}
            </Typography>
          </Box>
        </Box>
      </Box>

      {error && (
        <Typography color="error" variant="body2">
          {error}
        </Typography>
      )}

      {steps.length > 0 && (
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            overflowX: 'auto',
            pb: 0.5,
          }}
        >
          {steps.map((s) => (
            <Box
              key={s.step}
              component={motion.div}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              sx={{
                minWidth: 160,
                p: 1,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main' }}>
                FLIGHT {s.step} · {s.action}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }} noWrap>
                {s.observation?.slice(0, 80) || s.thought?.slice(0, 80)}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}

export default AgentTheater
