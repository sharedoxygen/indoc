import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
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
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import { useAgentStream } from '../../hooks/useAgentStream'
import HelpTip from '../HelpTip'
import AgentTheater from './AgentTheater'
import BriefBoard, { type AgentRunRecord } from './BriefBoard'
import { AGENT_HELP } from './agentHelp'

export type { AgentRunRecord }

const RUNS_KEY = 'indoc.agent.runs'

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
  const [focusRunId, setFocusRunId] = useState<string | null>(null)
  const lastHandledRef = useRef<string | null>(null)
  const running = agent.status === 'running' || agent.status === 'connecting'

  const boardRuns = useMemo(() => {
    if (!agent.finalAnswer) return priorRuns
    const live: AgentRunRecord = {
      id: 'live',
      goal: agent.goal,
      answer: agent.finalAnswer,
      at: new Date().toISOString(),
      steps: agent.steps.length || agent.iterations,
    }
    const rest = priorRuns.filter((r) => r.goal !== agent.goal || r.answer !== agent.finalAnswer)
    return [live, ...rest]
  }, [agent.finalAnswer, agent.goal, agent.steps.length, agent.iterations, priorRuns])

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
    setFocusRunId(run.id)
    setPriorRuns((prev) => {
      const next = [run, ...prev].slice(0, 20)
      saveRuns(next)
      return next
    })
    onFinalAnswer?.(agent.goal, agent.finalAnswer, run)
  }, [agent.status, agent.finalAnswer, agent.goal, agent.iterations, agent.steps.length, onFinalAnswer])

  const clearBriefs = () => {
    setPriorRuns([])
    setFocusRunId(null)
    sessionStorage.removeItem(RUNS_KEY)
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        gap: 1.5,
        minHeight: 0,
      }}
    >
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

      <Box sx={{ flex: '1 1 42%', minHeight: { xs: 260, md: 300 }, overflow: 'hidden' }}>
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
            flexShrink: 0,
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

      <Box sx={{ flex: '1.15 1 46%', minHeight: { xs: 300, md: 340 }, minWidth: 0 }}>
        <BriefBoard
          runs={boardRuns}
          focusRunId={agent.finalAnswer ? 'live' : focusRunId}
          onAskFollowUp={onAskFollowUp}
          onReuseGoal={setGoal}
          onClear={clearBriefs}
        />
      </Box>
    </Box>
  )
}

export default AgentModePanel
