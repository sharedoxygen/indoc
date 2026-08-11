import React, { useEffect, useMemo, useState } from 'react'
import { Box, Chip, Stack, Tooltip, Typography } from '@mui/material'
import { motion } from 'framer-motion'
import { PrecisionDial, NeedleGauge, LiveTicker } from '../instruments'
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
    const id = window.setInterval(tick, 250)
    return () => window.clearInterval(id)
  }, [isLive, startedAt])

  const hardProgress = maxSteps > 0 ? Math.min(100, (steps.length / maxSteps) * 100) : 0
  // Soft progress while planning so the dial never feels frozen at 0%
  const softBoost =
    isLive && steps.length === 0
      ? Math.min(12, elapsed * 1.4)
      : isLive && phase === 'planning'
        ? Math.min(8, 3 + (elapsed % 10))
        : 0
  const progress = Math.min(99, hardProgress + (hardProgress >= 100 ? 0 : softBoost))

  const usedTools = useMemo(() => new Set(steps.map((s) => s.action)), [steps])
  const toolCatalog = tools.length ? tools : Object.keys(TOOL_HELP)
  const toolsPct =
    toolCatalog.length > 0 ? Math.min(100, (usedTools.size / toolCatalog.length) * 100) : 0
  const dialStatus =
    status === 'error' ? 'error' : status === 'completed' ? 'ok' : isLive ? 'active' : 'idle'

  const phaseLabel =
    phase === 'planning' || phase === 'connecting'
      ? 'PLANNING'
      : phase === 'tool'
        ? 'EXECUTING'
        : status.toUpperCase()

  const phaseChip =
    phase === 'planning' || phase === 'connecting'
      ? 'Planner thinking…'
      : phase === 'tool'
        ? `Running ${TOOL_HELP[activeAction || '']?.short || activeAction || 'tool'}…`
        : null

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1.5 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1.2, fontWeight: 700 }}>
            <HelpTip title={AGENT_HELP.controlTower}>Live research orchestration</HelpTip>
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 560 }} noWrap>
            {goal || 'Set an objective above, then Run'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Tooltip title={AGENT_HELP.status}>
            <Box sx={{ cursor: 'help' }}>
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
            </Box>
          </Tooltip>
          {isLive && (
            <Chip size="small" variant="outlined" label={`${elapsed}s`} sx={{ fontVariantNumeric: 'tabular-nums' }} />
          )}
          {stoppedReason && (
            <Tooltip title="Why the run stopped">
              <Chip size="small" label={stoppedReason} variant="outlined" />
            </Tooltip>
          )}
          {holding && isLive && phaseChip && (
            <Tooltip title={AGENT_HELP.holding}>
              <Chip size="small" color={phase === 'tool' ? 'warning' : 'info'} label={phaseChip} />
            </Tooltip>
          )}
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
        <Box sx={{ minHeight: 460, height: '100%' }}>
          <AgentTheaterScene
            status={status}
            phase={phase}
            tools={tools}
            steps={steps}
            holding={holding}
            finalAnswer={finalAnswer}
            activeAction={activeAction}
            activeThought={activeThought}
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
          <Tooltip title={AGENT_HELP.progress} arrow>
            <Box sx={{ cursor: 'help' }}>
              <PrecisionDial
                value={status === 'completed' ? 100 : progress}
                label="Progress"
                unit="%"
                precision={0}
                size={128}
                status={dialStatus as any}
              />
            </Box>
          </Tooltip>
          <Tooltip title={AGENT_HELP.toolsUsed} arrow>
            <Box sx={{ cursor: 'help' }}>
              <NeedleGauge
                value={toolsPct}
                label="Tools"
                unit="%"
                precision={0}
                size={118}
                status={isLive ? 'warn' : (dialStatus as any)}
                displayValue={`${usedTools.size}/${toolCatalog.length}`}
              />
            </Box>
          </Tooltip>
          <Tooltip title={AGENT_HELP.steps} arrow>
            <Box sx={{ textAlign: 'center', cursor: 'help' }}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700 }}>
                STEPS
              </Typography>
              <Typography sx={{ fontWeight: 800, fontVariantNumeric: 'tabular-nums', fontSize: 22 }}>
                {steps.length}/{maxSteps || '—'}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                max {maxSteps || 0} · iter {iterations || steps.length}
              </Typography>
            </Box>
          </Tooltip>
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
            <Tooltip
              key={s.step}
              title={
                <Box sx={{ maxWidth: 280 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, display: 'block' }}>
                    {AGENT_HELP.flightStep}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {TOOL_HELP[s.action]?.help || s.action}
                  </Typography>
                  {s.thought && (
                    <Typography variant="caption" sx={{ display: 'block', mt: 0.75, opacity: 0.9 }}>
                      Thought: {s.thought.slice(0, 200)}
                    </Typography>
                  )}
                </Box>
              }
              arrow
            >
              <Box
                component={motion.div}
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                sx={{
                  minWidth: 160,
                  p: 1,
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.paper',
                  cursor: 'help',
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main' }}>
                  STEP {s.step} · {TOOL_HELP[s.action]?.short || s.action}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }} noWrap>
                  {s.observation?.slice(0, 80) || s.thought?.slice(0, 80)}
                </Typography>
              </Box>
            </Tooltip>
          ))}
        </Box>
      )}
    </Box>
  )
}

export default AgentTheater
