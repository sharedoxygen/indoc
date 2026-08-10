import React, { useMemo } from 'react'
import { Box, Chip, Stack, Tooltip, Typography } from '@mui/material'
import { motion } from 'framer-motion'
import { PrecisionDial, NeedleGauge, LiveTicker } from '../instruments'
import HelpTip from '../HelpTip'
import AgentTheaterScene from './AgentTheaterScene'
import { AGENT_HELP, TOOL_HELP } from './agentHelp'
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
  const progress = maxSteps > 0 ? Math.min(100, (steps.length / maxSteps) * 100) : 0
  const usedTools = useMemo(() => new Set(steps.map((s) => s.action)), [steps])
  const toolCatalog = tools.length ? tools : Object.keys(TOOL_HELP)
  const toolsPct =
    toolCatalog.length > 0 ? Math.min(100, (usedTools.size / toolCatalog.length) * 100) : 0
  const dialStatus =
    status === 'error' ? 'error' : status === 'completed' ? 'ok' : status === 'running' ? 'active' : 'idle'

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1.5 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 1.2, fontWeight: 700 }}>
            <HelpTip title={AGENT_HELP.controlTower}>Live agent run</HelpTip>
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 520 }} noWrap>
            {goal || 'Waiting for a goal — type one above and Launch'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Tooltip title={AGENT_HELP.status}>
            <Box sx={{ cursor: 'help' }}>
              <LiveTicker
                label="Status"
                value={status.toUpperCase()}
                live={status === 'running' || status === 'connecting'}
                accent={status === 'error' ? 'error.main' : status === 'completed' ? 'success.main' : 'primary.main'}
              />
            </Box>
          </Tooltip>
          {stoppedReason && (
            <Tooltip title="Why the run stopped">
              <Chip size="small" label={stoppedReason} variant="outlined" />
            </Tooltip>
          )}
          {holding && status === 'running' && (
            <Tooltip title={AGENT_HELP.holding}>
              <Chip size="small" color="warning" label="Waiting on tool…" />
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
          <Tooltip title={AGENT_HELP.progress} arrow>
            <Box sx={{ cursor: 'help' }}>
              <PrecisionDial
                value={progress}
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
                status={status === 'running' ? 'warn' : (dialStatus as any)}
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
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            overflowX: 'auto',
            pb: 0.5,
          }}
        >
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
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
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
