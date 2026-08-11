import React, { useEffect, useRef, useState } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  Paper,
  Slider,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  AutoAwesome as RunIcon,
  ExpandMore as ExpandMoreIcon,
  Stop as StopIcon,
  Chat as ChatIcon,
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import { useAgentStream } from '../../hooks/useAgentStream'
import HelpTip from '../HelpTip'
import AgentTheater from './AgentTheater'
import { AGENT_HELP } from './agentHelp'

const RUNS_KEY = 'indoc.agent.runs'

export interface AgentRunRecord {
  id: string
  goal: string
  answer: string
  at: string
  steps: number
}

interface AgentModePanelProps {
  documentIds: string[]
  onFinalAnswer?: (goal: string, answer: string, run: AgentRunRecord) => void
  onAskFollowUp?: (run: AgentRunRecord) => void
}

function loadRuns(): AgentRunRecord[] {
  try {
    const raw = sessionStorage.getItem(RUNS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveRuns(runs: AgentRunRecord[]) {
  sessionStorage.setItem(RUNS_KEY, JSON.stringify(runs.slice(0, 20)))
}

export const AgentModePanel: React.FC<AgentModePanelProps> = ({
  documentIds,
  onFinalAnswer,
  onAskFollowUp,
}) => {
  const agent = useAgentStream()
  const [goal, setGoal] = useState('')
  const [maxSteps, setMaxSteps] = useState(6)
  const [priorRuns, setPriorRuns] = useState<AgentRunRecord[]>(() => loadRuns())
  const lastHandledRef = useRef<string | null>(null)
  const running = agent.status === 'running' || agent.status === 'connecting'

  const handleLaunch = async () => {
    const trimmed = goal.trim()
    if (!trimmed || running) return
    lastHandledRef.current = null
    await agent.run({ goal: trimmed, documentIds, maxSteps })
  }

  useEffect(() => {
    if (agent.status !== 'completed' || !agent.finalAnswer) return
    const dedupeKey = `${agent.goal}::${agent.finalAnswer.slice(0, 80)}::${agent.iterations}`
    if (lastHandledRef.current === dedupeKey) return
    lastHandledRef.current = dedupeKey

    const run: AgentRunRecord = {
      id: `${Date.now()}`,
      goal: agent.goal,
      answer: agent.finalAnswer,
      at: new Date().toISOString(),
      steps: agent.steps.length || agent.iterations,
    }
    setPriorRuns((prev) => {
      const next = [run, ...prev].slice(0, 20)
      saveRuns(next)
      return next
    })
    onFinalAnswer?.(agent.goal, agent.finalAnswer, run)
  }, [agent.status, agent.finalAnswer, agent.goal, agent.iterations, agent.steps.length, onFinalAnswer])

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1.5 }}>
      <Paper
        component={motion.div as any}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        sx={{
          p: 1.75,
          borderRadius: 2.5,
          border: '1px solid',
          borderColor: 'divider',
          background: (t) =>
            t.palette.mode === 'dark'
              ? 'linear-gradient(135deg, rgba(56,189,248,0.08) 0%, rgba(18,24,34,0.95) 40%, rgba(12,16,22,0.95) 100%)'
              : 'linear-gradient(135deg, rgba(14,165,233,0.08) 0%, rgba(255,255,255,0.95) 45%, rgba(248,250,252,0.95) 100%)',
          backdropFilter: 'blur(14px)',
        }}
      >
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
          <Tooltip title={AGENT_HELP.missionGoal} arrow>
            <TextField
              fullWidth
              size="small"
              label="Research objective"
              placeholder="e.g. Summarize key risks across these contracts"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleLaunch()
                }
              }}
              disabled={running}
              helperText={
                documentIds.length === 0
                  ? 'Include documents in corpus scope'
                  : `${documentIds.length} document${documentIds.length === 1 ? '' : 's'} in corpus`
              }
            />
          </Tooltip>
          <Tooltip
            title={
              !goal.trim()
                ? 'Enter an objective first'
                : documentIds.length === 0
                  ? 'Confirm corpus scope first'
                  : AGENT_HELP.launch
            }
          >
            <span>
              <Button
                variant="contained"
                color="primary"
                startIcon={<RunIcon />}
                onClick={handleLaunch}
                disabled={!goal.trim() || running || documentIds.length === 0}
                sx={{
                  minWidth: 140,
                  whiteSpace: 'nowrap',
                  borderRadius: 999,
                  textTransform: 'none',
                  fontWeight: 750,
                  boxShadow: '0 10px 28px rgba(25,118,210,0.35)',
                }}
              >
                {running ? 'Running…' : 'Run'}
              </Button>
            </span>
          </Tooltip>
          {running && (
            <Tooltip title={AGENT_HELP.abort}>
              <Button variant="outlined" color="inherit" startIcon={<StopIcon />} onClick={agent.stop}>
                Stop
              </Button>
            </Tooltip>
          )}
        </Stack>
        <Accordion disableGutters elevation={0} sx={{ mt: 1, bgcolor: 'transparent', '&:before': { display: 'none' } }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 36, px: 0 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
              <HelpTip title={AGENT_HELP.advanced} underline={false}>
                Advanced · max steps {maxSteps} · scope {documentIds.length || 0} docs
              </HelpTip>
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 0 }}>
            <Typography variant="caption" color="text.secondary" component="div">
              <HelpTip title={AGENT_HELP.maxSteps}>Max reasoning steps</HelpTip>
            </Typography>
            <Slider
              value={maxSteps}
              min={1}
              max={12}
              step={1}
              marks
              valueLabelDisplay="auto"
              onChange={(_, v) => setMaxSteps(v as number)}
              disabled={running}
            />
          </AccordionDetails>
        </Accordion>
      </Paper>

      <Box sx={{ flex: 1, minHeight: 0 }}>
        <AgentTheater
          status={agent.status}
          phase={agent.phase}
          tools={agent.tools}
          steps={agent.steps}
          holding={agent.holding}
          finalAnswer={agent.finalAnswer}
          maxSteps={agent.maxSteps}
          iterations={agent.iterations}
          stoppedReason={agent.stoppedReason}
          error={agent.error}
          goal={agent.goal}
          activeAction={agent.activeAction}
          activeThought={agent.activeThought}
          startedAt={agent.startedAt}
        />
      </Box>

      {agent.error && (
        <Paper
          sx={{
            p: 1.5,
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'error.main',
            bgcolor: (t) => (t.palette.mode === 'dark' ? 'rgba(244,67,54,0.08)' : 'rgba(244,67,54,0.06)'),
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'error.main', letterSpacing: 0.6 }}>
            RUN FAILED
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
            {agent.error}
          </Typography>
        </Paper>
      )}

      <Paper sx={{ p: 1.5, borderRadius: 3, maxHeight: 160, overflow: 'auto' }}>
        <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 0.8, color: 'text.secondary' }}>
          <HelpTip title={AGENT_HELP.arrivalBoard}>BRIEF BOARD · completed research</HelpTip>
        </Typography>
        {priorRuns.length === 0 && !agent.finalAnswer && !agent.error && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Finished briefs land here for reuse this session.
          </Typography>
        )}
        <Stack spacing={1} sx={{ mt: 1 }}>
          {(agent.finalAnswer
            ? [
                {
                  id: 'live',
                  goal: agent.goal,
                  answer: agent.finalAnswer,
                  at: new Date().toISOString(),
                  steps: agent.steps.length,
                } as AgentRunRecord,
                ...priorRuns.filter((r) => r.goal !== agent.goal || r.answer !== agent.finalAnswer),
              ]
            : priorRuns
          )
            .slice(0, 5)
            .map((run) => (
              <Box
                key={run.id}
                component={motion.div}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                sx={{
                  p: 1,
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.default',
                }}
              >
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                  <Tooltip title="Tool steps taken in this run">
                    <Chip
                      size="small"
                      variant="outlined"
                      label={`${run.steps || 0} steps`}
                      sx={{ height: 22, borderRadius: 0.75, fontWeight: 600 }}
                    />
                  </Tooltip>
                  {/could not complete|planning_failed|failed|error/i.test(run.answer) ? (
                    <Chip
                      size="small"
                      color="warning"
                      label="PARTIAL"
                      sx={{ height: 22, borderRadius: 0.75, fontWeight: 700 }}
                    />
                  ) : (
                    <Chip
                      size="small"
                      color="success"
                      variant="outlined"
                      label="BRIEF"
                      sx={{ height: 22, borderRadius: 0.75, fontWeight: 700 }}
                    />
                  )}
                  <Typography variant="caption" color="text.secondary" noWrap sx={{ flex: 1 }}>
                    {run.goal}
                  </Typography>
                </Stack>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {run.answer.slice(0, 360)}
                  {run.answer.length > 360 ? '…' : ''}
                </Typography>
                {onAskFollowUp && (
                  <Box sx={{ mt: 1 }}>
                    <Tooltip title={AGENT_HELP.askFollowUp}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<ChatIcon />}
                        onClick={() => onAskFollowUp(run)}
                        sx={{ borderRadius: 999, textTransform: 'none', fontWeight: 650 }}
                      >
                        Ask follow-up
                      </Button>
                    </Tooltip>
                  </Box>
                )}
              </Box>
            ))}
        </Stack>
      </Paper>
    </Box>
  )
}

export default AgentModePanel
