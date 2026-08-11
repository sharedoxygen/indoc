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
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
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
  const theme = useTheme()
  const stacked = useMediaQuery(theme.breakpoints.down('lg'))
  const agent = useAgentStream()
  const [goal, setGoal] = useState('')
  const [maxSteps, setMaxSteps] = useState(6)
  const [priorRuns, setPriorRuns] = useState<AgentRunRecord[]>(() => loadRuns())
  const [focusRunId, setFocusRunId] = useState<string | null>(null)
  const [mobileTab, setMobileTab] = useState(0)
  const lastHandledRef = useRef<string | null>(null)
  const running = agent.status === 'running' || agent.status === 'connecting'
  const isLive = running

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
    if (stacked) setMobileTab(0)
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
    if (stacked) setMobileTab(1)
    setPriorRuns((prev) => {
      const next = [run, ...prev].slice(0, 20)
      saveRuns(next)
      return next
    })
    onFinalAnswer?.(agent.goal, agent.finalAnswer, run)
  }, [
    agent.status,
    agent.finalAnswer,
    agent.goal,
    agent.iterations,
    agent.steps.length,
    onFinalAnswer,
    stacked,
  ])

  const clearBriefs = () => {
    setPriorRuns([])
    setFocusRunId(null)
    sessionStorage.removeItem(RUNS_KEY)
  }

  const consolePane = (
    <Box sx={{ height: '100%', minHeight: 0, minWidth: 0, overflow: 'hidden' }}>
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
  )

  const briefPane = (
    <Box sx={{ height: '100%', minHeight: 0, minWidth: 0 }}>
      <BriefBoard
        runs={boardRuns}
        focusRunId={agent.finalAnswer ? 'live' : focusRunId}
        onAskFollowUp={onAskFollowUp}
        onReuseGoal={setGoal}
        onClear={clearBriefs}
      />
    </Box>
  )

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        gap: 1.25,
        minHeight: 0,
      }}
    >
      {/* Compact command bar */}
      <Paper
        component={motion.div as any}
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        sx={{
          px: 1.5,
          py: 1.1,
          borderRadius: 2,
          border: '1px solid',
          borderColor: 'divider',
          flexShrink: 0,
          bgcolor: (t) =>
            t.palette.mode === 'dark' ? 'rgba(18,24,34,0.92)' : 'rgba(255,255,255,0.96)',
        }}
      >
        <Stack direction="row" spacing={1} alignItems="flex-start">
          <Tooltip title={AGENT_HELP.missionGoal} arrow>
            <TextField
              fullWidth
              size="small"
              placeholder="Research objective — e.g. Summarize key risks across these contracts"
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
                  : `${documentIds.length} doc${documentIds.length === 1 ? '' : 's'} · max ${maxSteps} steps`
              }
              FormHelperTextProps={{ sx: { mx: 0.5, mt: 0.4 } }}
              sx={{
                '& .MuiOutlinedInput-root': { borderRadius: 1.5 },
              }}
            />
          </Tooltip>
          <Stack direction="row" spacing={0.75} sx={{ pt: 0.15 }} flexShrink={0}>
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
                  startIcon={<RunIcon />}
                  onClick={handleLaunch}
                  disabled={!goal.trim() || running || documentIds.length === 0}
                  sx={{
                    minWidth: 96,
                    borderRadius: 1.5,
                    textTransform: 'none',
                    fontWeight: 750,
                  }}
                >
                  {running ? 'Running…' : 'Run'}
                </Button>
              </span>
            </Tooltip>
            {running && (
              <Tooltip title={AGENT_HELP.abort}>
                <Button
                  variant="outlined"
                  color="inherit"
                  startIcon={<StopIcon />}
                  onClick={agent.stop}
                  sx={{ borderRadius: 1.5, textTransform: 'none' }}
                >
                  Stop
                </Button>
              </Tooltip>
            )}
          </Stack>
        </Stack>
        <Accordion
          disableGutters
          elevation={0}
          sx={{ mt: 0.25, bgcolor: 'transparent', '&:before': { display: 'none' } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 28, px: 0.25, '& .MuiAccordionSummary-content': { my: 0.5 } }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
              <HelpTip title={AGENT_HELP.advanced} underline={false}>
                Advanced
              </HelpTip>
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 0.25, pt: 0, pb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
              <HelpTip title={AGENT_HELP.maxSteps}>Max reasoning steps: {maxSteps}</HelpTip>
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
              size="small"
            />
          </AccordionDetails>
        </Accordion>
      </Paper>

      {agent.error && (
        <Paper
          sx={{
            px: 1.5,
            py: 1,
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'error.main',
            bgcolor: (t) => (t.palette.mode === 'dark' ? 'rgba(244,67,54,0.08)' : 'rgba(244,67,54,0.06)'),
            flexShrink: 0,
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'error.main' }}>
            Run failed
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.35, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {agent.error}
          </Typography>
        </Paper>
      )}

      {/* Desktop: console | briefs side-by-side. Mobile: tabs. */}
      {stacked ? (
        <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <Tabs
            value={mobileTab}
            onChange={(_, v) => setMobileTab(v)}
            sx={{
              minHeight: 36,
              flexShrink: 0,
              mb: 1,
              '& .MuiTab-root': { minHeight: 36, textTransform: 'none', fontWeight: 700 },
            }}
          >
            <Tab label={isLive ? 'Console · live' : 'Console'} />
            <Tab label={`Briefs${boardRuns.length ? ` · ${boardRuns.length}` : ''}`} />
          </Tabs>
          <Box sx={{ flex: 1, minHeight: 0 }}>{mobileTab === 0 ? consolePane : briefPane}</Box>
        </Box>
      ) : (
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)',
            gap: 1.25,
          }}
        >
          {consolePane}
          {briefPane}
        </Box>
      )}
    </Box>
  )
}

export default AgentModePanel
