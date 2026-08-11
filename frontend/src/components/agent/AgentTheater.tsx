import React, { useEffect, useMemo, useState } from 'react'
import { Box, Chip, Stack, Typography, useTheme } from '@mui/material'
import { motion } from 'framer-motion'
import HelpTip from '../HelpTip'
import AgentTheaterScene from './AgentTheaterScene'
import AgentInstrumentCluster from './AgentInstrumentCluster'
import { AGENT_HELP, TOOL_HELP } from './agentHelp'
import type { AgentPhase, AgentStep, AgentStreamStatus } from '../../hooks/useAgentStream'

interface AgentTheaterProps {
  status: AgentStreamStatus
  phase: AgentPhase
  tools: string[]
  steps: AgentStep[]
  holding: boolean
  finalAnswer: string | null
  maxSteps: number
  iterations: number
  stoppedReason: string | null
  error: string | null
  goal?: string
  activeAction?: string | null
  activeThought?: string | null
  startedAt?: number | null
}

export const AgentTheater: React.FC<AgentTheaterProps> = ({
  status,
  phase,
  tools,
  steps,
  holding,
  finalAnswer,
  maxSteps,
  iterations,
  stoppedReason,
  error,
  goal,
  activeAction,
  activeThought,
  startedAt,
}) => {
  const theme = useTheme()
  const [elapsed, setElapsed] = useState(0)
  const isLive = status === 'running' || status === 'connecting'

  useEffect(() => {
    if (!isLive || !startedAt) {
      setElapsed(0)
      return
    }
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)))
    tick()
    const id = window.setInterval(tick, 200)
    return () => window.clearInterval(id)
  }, [isLive, startedAt])

  const hardProgress = maxSteps > 0 ? Math.min(100, (steps.length / maxSteps) * 100) : 0
  const softBoost =
    isLive && steps.length === 0
      ? Math.min(16, elapsed * 1.8)
      : isLive && phase === 'planning'
        ? Math.min(9, 2 + (elapsed % 10))
        : 0
  const progress = status === 'completed' ? 100 : Math.min(99, hardProgress + softBoost)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1.25, minHeight: 0 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1.1, fontWeight: 700 }}>
            <HelpTip title={AGENT_HELP.controlTower}>Research console</HelpTip>
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 640 }} noWrap>
            {goal || 'Set an objective above, then Run — instruments update as the agent works'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          {isLive && (
            <Chip
              size="small"
              color={phase === 'tool' ? 'warning' : 'info'}
              label={phase === 'tool' ? 'TOOL LIVE' : 'PLANNING'}
              sx={{ fontWeight: 750 }}
            />
          )}
          {stoppedReason && <Chip size="small" label={stoppedReason} variant="outlined" />}
          <Chip
            size="small"
            variant="outlined"
            label={`iter ${iterations || steps.length}`}
            sx={{ fontVariantNumeric: 'tabular-nums' }}
          />
        </Stack>
      </Stack>

      {/* Dominant live graphics — always visible */}
      <AgentInstrumentCluster
        status={status}
        phase={phase}
        steps={steps}
        tools={tools}
        maxSteps={maxSteps}
        elapsed={elapsed}
        progress={progress}
        activeAction={activeAction}
      />

      <Box sx={{ flex: 1, minHeight: 0, minWidth: 0 }}>
        <AgentTheaterScene
          status={status}
          phase={phase}
          tools={tools}
          steps={steps}
          holding={holding}
          finalAnswer={finalAnswer}
          activeAction={activeAction}
          activeThought={activeThought}
          elapsed={elapsed}
          maxSteps={maxSteps}
        />
      </Box>

      {error && (
        <Typography color="error" variant="body2">
          {error}
        </Typography>
      )}

      {steps.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }}>
          {steps.map((s) => (
            <Box
              key={s.step}
              component={motion.div}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              sx={{
                minWidth: 160,
                p: 1.1,
                borderRadius: 1.5,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor:
                  theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'background.paper',
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main' }}>
                {s.step} · {TOOL_HELP[s.action]?.short || s.action}
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.35 }} noWrap>
                {s.observation?.slice(0, 72) || s.thought?.slice(0, 72)}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}

export default AgentTheater
