import React, { useEffect, useMemo, useState } from 'react'
import { Box, Paper, Stack, Typography, useTheme } from '@mui/material'
import { motion, useReducedMotion } from 'framer-motion'
import { ArcMeter, LiveTicker, NeedleGauge, PrecisionDial, SegmentRing } from '../instruments'
import type { SegmentStatus } from '../instruments'
import type { AgentPhase, AgentStep, AgentStreamStatus } from '../../hooks/useAgentStream'
import { TOOL_HELP } from './agentHelp'

const PIPELINE = [
  'list_documents',
  'search_documents',
  'read_document',
  'summarize_document',
  'compare_documents',
  'finish',
] as const

interface AgentInstrumentClusterProps {
  status: AgentStreamStatus
  phase: AgentPhase
  steps: AgentStep[]
  tools: string[]
  maxSteps: number
  elapsed: number
  progress: number
  activeAction?: string | null
}

function formatClock(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

/** Live precision cluster — budget, tempo, coverage, instrument pipeline. */
export const AgentInstrumentCluster: React.FC<AgentInstrumentClusterProps> = ({
  status,
  phase,
  steps,
  tools,
  maxSteps,
  elapsed,
  progress,
  activeAction,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const dark = theme.palette.mode === 'dark'
  const isLive = status === 'running' || status === 'connecting'
  const isDone = status === 'completed'
  const isError = status === 'error'

  // Smooth soft needle so the cluster never looks frozen between SSE events
  const [pulse, setPulse] = useState(0)
  useEffect(() => {
    if (!isLive || reduceMotion) {
      setPulse(0)
      return
    }
    const id = window.setInterval(() => setPulse((p) => (p + 1) % 100), 180)
    return () => window.clearInterval(id)
  }, [isLive, reduceMotion])

  const catalog = tools.length ? tools : [...PIPELINE]
  const used = useMemo(() => new Set(steps.map((s) => s.action)), [steps])
  const toolCoverage = catalog.length ? (used.size / catalog.length) * 100 : 0
  const tempo =
    elapsed > 0 ? Math.min(100, (steps.length / Math.max(elapsed / 60, 0.15)) * 12) : isLive ? 8 + (pulse % 12) : 0
  const liveBudget = Math.min(99, progress + (isLive && phase === 'planning' ? (pulse % 5) * 0.35 : 0))

  const segments = PIPELINE.map((tool) => {
    let segStatus: SegmentStatus = 'pending'
    if (isError && activeAction === tool) segStatus = 'failed'
    else if (activeAction === tool && isLive) segStatus = 'active'
    else if (used.has(tool) || (isDone && tool === 'finish')) segStatus = 'complete'
    const short = TOOL_HELP[tool]?.short || tool.slice(0, 4).toUpperCase()
    const hits = steps.filter((s) => s.action === tool).length
    return {
      key: tool,
      label: short,
      status: segStatus,
      value: hits || (segStatus === 'complete' || segStatus === 'active' ? 1 : 0),
    }
  })

  const dialStatus = isError ? 'error' : isDone ? 'ok' : isLive ? 'active' : 'idle'
  const phaseLabel =
    phase === 'planning' || phase === 'connecting'
      ? 'PLANNING'
      : phase === 'tool'
        ? 'EXECUTING'
        : status.toUpperCase()

  return (
    <Paper
      component={motion.div}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      sx={{
        p: { xs: 1.5, md: 2 },
        borderRadius: 2.5,
        border: '1px solid',
        borderColor: 'divider',
        background: dark
          ? 'linear-gradient(180deg, rgba(18,24,34,0.98) 0%, rgba(10,13,18,0.95) 100%)'
          : 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,247,251,0.95) 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Ambient sweep while live */}
      {isLive && !reduceMotion && (
        <Box
          component={motion.div}
          aria-hidden
          animate={{ x: ['-30%', '130%'] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: 'linear' }}
          sx={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            width: '28%',
            background:
              'linear-gradient(90deg, transparent, rgba(56,189,248,0.07), transparent)',
            pointerEvents: 'none',
          }}
        />
      )}

      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 1.25, position: 'relative' }}
        flexWrap="wrap"
        gap={1}
      >
        <Typography
          variant="caption"
          sx={{ fontWeight: 750, letterSpacing: 1.2, color: 'text.secondary' }}
        >
          LIVE INSTRUMENT CLUSTER
        </Typography>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <LiveTicker
            label="Phase"
            value={phaseLabel}
            live={isLive}
            accent={
              isError
                ? 'error.main'
                : isDone
                  ? 'success.main'
                  : phase === 'tool'
                    ? 'warning.main'
                    : 'primary.main'
            }
          />
          <LiveTicker label="Elapsed" value={formatClock(elapsed)} live={isLive} accent="info.main" />
          <LiveTicker
            label="Steps"
            value={`${steps.length}/${maxSteps}`}
            live={false}
            accent="text.secondary"
          />
        </Stack>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr 1fr',
            md: '140px 140px 140px 1fr',
          },
          gap: { xs: 1.5, md: 2 },
          alignItems: 'center',
          position: 'relative',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <PrecisionDial
            value={isDone ? 100 : liveBudget}
            label="Budget"
            unit="%"
            precision={0}
            size={128}
            status={dialStatus}
            animate
          />
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <NeedleGauge
            value={Math.min(100, tempo)}
            label="Tempo"
            displayValue={elapsed > 0 ? `${(steps.length / Math.max(elapsed / 60, 0.01)).toFixed(1)}/m` : '—'}
            size={120}
            status={isLive ? 'active' : isDone ? 'ok' : 'idle'}
          />
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <ArcMeter
            value={toolCoverage}
            label="Coverage"
            subtitle={`${used.size}/${catalog.length} tools`}
            unit="%"
            precision={0}
            size={118}
            status={toolCoverage >= 50 ? 'ok' : isLive ? 'warn' : 'idle'}
          />
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 0 }}>
          <SegmentRing
            segments={segments}
            size={168}
            centerLabel={isLive ? 'Live' : isDone ? 'Done' : 'Idle'}
            centerValue={String(steps.length)}
            showLegend={false}
          />
          <Stack
            direction="row"
            spacing={0.75}
            useFlexGap
            flexWrap="wrap"
            justifyContent="center"
            sx={{ mt: 0.75, maxWidth: 280 }}
          >
            {segments.map((seg) => (
              <Typography
                key={seg.key}
                variant="caption"
                sx={{
                  fontSize: 10,
                  fontWeight: seg.status === 'active' ? 800 : 600,
                  color:
                    seg.status === 'complete'
                      ? 'success.main'
                      : seg.status === 'active'
                        ? 'warning.main'
                        : seg.status === 'failed'
                          ? 'error.main'
                          : 'text.disabled',
                  letterSpacing: 0.4,
                }}
              >
                {seg.label}
              </Typography>
            ))}
          </Stack>
        </Box>
      </Box>
    </Paper>
  )
}

export default AgentInstrumentCluster
