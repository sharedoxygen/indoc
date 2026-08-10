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
  Typography,
} from '@mui/material'
import { ExpandMore as ExpandMoreIcon, FlightTakeoff as LaunchIcon, Stop as StopIcon } from '@mui/icons-material'
import { motion } from 'framer-motion'
import { useAgentStream } from '../../hooks/useAgentStream'
import AgentTheater from './AgentTheater'

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

export const AgentModePanel: React.FC<AgentModePanelProps> = ({ documentIds, onFinalAnswer }) => {
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
        sx={{ p: 1.5, borderRadius: 3 }}
      >
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
          <TextField
            fullWidth
            size="small"
            label="Mission goal"
            placeholder="e.g. Summarize key risks across my indexed contracts"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleLaunch()
              }
            }}
            disabled={running}
          />
          <Button
            variant="contained"
            color="primary"
            startIcon={<LaunchIcon />}
            onClick={handleLaunch}
            disabled={!goal.trim() || running}
            sx={{ minWidth: 140, whiteSpace: 'nowrap' }}
          >
            {running ? 'In flight…' : 'Launch'}
          </Button>
          {running && (
            <Button variant="outlined" color="inherit" startIcon={<StopIcon />} onClick={agent.stop}>
              Abort
            </Button>
          )}
        </Stack>
        <Accordion disableGutters elevation={0} sx={{ mt: 1, bgcolor: 'transparent', '&:before': { display: 'none' } }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 36, px: 0 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
              Advanced · max steps {maxSteps} · scope {documentIds.length || 'all accessible'} docs
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 0 }}>
            <Typography variant="caption" color="text.secondary">
              Max reasoning steps
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
          tools={agent.tools}
          steps={agent.steps}
          holding={agent.holding}
          finalAnswer={agent.finalAnswer}
          maxSteps={agent.maxSteps}
          iterations={agent.iterations}
          stoppedReason={agent.stoppedReason}
          error={agent.error}
          goal={agent.goal}
        />
      </Box>

      {/* Arrival / prior-run transcript strip */}
      <Paper sx={{ p: 1.5, borderRadius: 3, maxHeight: 160, overflow: 'auto' }}>
        <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 0.8, color: 'text.secondary' }}>
          ARRIVAL BOARD · MISSION LOG
        </Typography>
        {priorRuns.length === 0 && !agent.finalAnswer && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Completed flights land here — goal + final answer for reuse.
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
                  <Chip size="small" label={`${run.steps || 0} steps`} />
                  <Typography variant="caption" color="text.secondary" noWrap sx={{ flex: 1 }}>
                    {run.goal}
                  </Typography>
                </Stack>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {run.answer.slice(0, 360)}
                  {run.answer.length > 360 ? '…' : ''}
                </Typography>
              </Box>
            ))}
        </Stack>
      </Paper>
    </Box>
  )
}

export default AgentModePanel
