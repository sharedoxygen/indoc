import React, { useEffect, useState } from 'react'
import { Box, Chip, Stack, Typography } from '@mui/material'
import HelpTip from '../HelpTip'
import AgentTheaterScene from './AgentTheaterScene'
import AgentInstrumentCluster from './AgentInstrumentCluster'
import { AGENT_HELP } from './agentHelp'
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
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1, minHeight: 0 }}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        sx={{ minWidth: 0, flexShrink: 0 }}
      >
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            variant="caption"
            sx={{ color: 'text.secondary', letterSpacing: 0.7, fontWeight: 750, textTransform: 'uppercase' }}
          >
            <HelpTip title={AGENT_HELP.controlTower}>Console</HelpTip>
          </Typography>
          <Typography
            variant="body2"
            title={goal || undefined}
            sx={{
              color: 'text.secondary',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {goal || 'Run an objective to watch instruments and reasoning'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.75} alignItems="center" flexShrink={0}>
          {isLive && (
            <Chip
              size="small"
              color={phase === 'tool' ? 'warning' : 'info'}
              label={phase === 'tool' ? 'Tool' : 'Planning'}
              sx={{ fontWeight: 750, height: 22 }}
            />
          )}
          {stoppedReason && (
            <Chip
              size="small"
              label={stoppedReason}
              variant="outlined"
              sx={{ height: 22, maxWidth: 120, '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' } }}
            />
          )}
          <Chip
            size="small"
            variant="outlined"
            label={`${iterations || steps.length}/${maxSteps}`}
            sx={{ fontVariantNumeric: 'tabular-nums', height: 22 }}
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
        <Typography color="error" variant="body2" sx={{ flexShrink: 0, wordBreak: 'break-word' }}>
          {error}
        </Typography>
      )}
    </Box>
  )
}

export default AgentTheater
