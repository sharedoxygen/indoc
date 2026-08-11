import React, { useEffect, useMemo, useState } from 'react'
import { Box, Chip, Stack, Tooltip, Typography } from '@mui/material'
import { motion } from 'framer-motion'
import { ArcMeter, LiveTicker } from '../instruments'
import HelpTip from '../HelpTip'
import AgentTheaterScene from './AgentTheaterScene'
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
      ? Math.min(14, elapsed * 1.6)
      : isLive && phase === 'planning'
        ? Math.min(8, 2 + (elapsed % 9))
        : 0
  const progress = status === 'completed' ? 100 : Math.min(99, hardProgress + softBoost)

  const usedTools = useMemo(() => new Set(steps.map((s) => s.action)), [steps])
  const toolCatalog = tools.length ? tools : Object.keys(TOOL_HELP)

  const phaseLabel =
    phase === 'planning' || phase === 'connecting'
      ? 'PLANNING'
      : phase === 'tool'
        ? 'EXECUTING'
        : status.toUpperCase()

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1.25 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1.1, fontWeight: 700 }}>
            <HelpTip title={AGENT_HELP.controlTower}>Research console</HelpTip>
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 560 }} noWrap>
            {goal || 'Set an objective above, then Run'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <LiveTicker
            label="Phase"
            value={phaseLabel}
            live={isLive}
            accent={
              status === 'error'
                ? 'error.main'
                : status === 'completed'
                  ? 'success.main'
                  : phase === 'tool'
                    ? 'warning.main'
                    : 'primary.main'
            }
          />
          {isLive && (
            <Chip size="small" variant="outlined" label={`${elapsed}s`} sx={{ fontVariantNumeric: 'tabular-nums' }} />
          )}
          {stoppedReason && <Chip size="small" label={stoppedReason} variant="outlined" />}
        </Stack>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1fr 120px' },
          gap: 1.25,
          flex: 1,
          minHeight: 0,
        }}
      >
        <Box sx={{ minHeight: 420, height: '100%' }}>
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

        <Box
          component={motion.div}
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          sx={{
            display: 'flex',
            flexDirection: { xs: 'row', lg: 'column' },
            alignItems: 'center',
            justifyContent: 'space-around',
            gap: 1,
            p: 1.25,
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <Tooltip title={AGENT_HELP.progress} arrow>
            <Box sx={{ cursor: 'help' }}>
              <ArcMeter
                value={progress}
                label="Budget"
                unit="%"
                precision={0}
                size={96}
                status={status === 'error' ? 'error' : status === 'completed' ? 'ok' : 'active'}
              />
            </Box>
          </Tooltip>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
              STEPS
            </Typography>
            <Typography sx={{ fontWeight: 800, fontVariantNumeric: 'tabular-nums', fontSize: 20 }}>
              {steps.length}/{maxSteps || '—'}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.disabled', display: 'block' }}>
              {usedTools.size}/{toolCatalog.length} tools
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
        <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }}>
          {steps.map((s) => (
            <Box
              key={s.step}
              component={motion.div}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              sx={{
                minWidth: 148,
                p: 1,
                borderRadius: 1.5,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.paper',
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
