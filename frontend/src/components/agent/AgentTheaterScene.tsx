import React, { useEffect, useMemo, useState } from 'react'
import { Box, Stack, Typography, useTheme, LinearProgress, Chip } from '@mui/material'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import type { AgentPhase, AgentStep, AgentStreamStatus } from '../../hooks/useAgentStream'
import { TOOL_HELP } from './agentHelp'

const DEFAULT_TOOLS = [
  'list_documents',
  'search_documents',
  'read_document',
  'summarize_document',
  'compare_documents',
  'finish',
]

interface AgentTheaterSceneProps {
  status: AgentStreamStatus
  phase: AgentPhase
  tools: string[]
  steps: AgentStep[]
  holding: boolean
  finalAnswer: string | null
  activeAction?: string | null
  activeThought?: string | null
  elapsed?: number
  maxSteps?: number
}

type FeedItem = { id: string; t: number; kind: 'sys' | 'plan' | 'tool' | 'ok' | 'err'; text: string }

function useTypewriter(text: string, active: boolean, cps = 42) {
  const [shown, setShown] = useState('')
  useEffect(() => {
    if (!active) {
      setShown(text || '')
      return
    }
    setShown('')
    if (!text) return
    let i = 0
    const id = window.setInterval(() => {
      i += 1
      setShown(text.slice(0, i))
      if (i >= text.length) window.clearInterval(id)
    }, Math.max(12, 1000 / cps))
    return () => window.clearInterval(id)
  }, [text, active, cps])
  return shown
}

export const AgentTheaterScene: React.FC<AgentTheaterSceneProps> = ({
  status,
  phase,
  tools,
  steps,
  holding,
  finalAnswer,
  activeAction,
  activeThought,
  elapsed = 0,
  maxSteps = 6,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const isLive = status === 'running' || status === 'connecting'
  const isPlanning = phase === 'planning' || phase === 'connecting'
  const isTool = phase === 'tool'
  const isDone = status === 'completed'
  const isError = status === 'error'

  const catalog = tools.length ? tools : DEFAULT_TOOLS
  const liveAction = activeAction || steps[steps.length - 1]?.action || null
  const typedThought = useTypewriter(
    activeThought || steps[steps.length - 1]?.thought || '',
    isLive && !reduceMotion
  )

  const planningLines = useMemo(
    () => [
      'Resolving corpus access…',
      'Building retrieval plan…',
      'Ranking candidate instruments…',
      'Estimating evidence coverage…',
      'Committing next action…',
    ],
    []
  )

  const [feed, setFeed] = useState<FeedItem[]>([
    { id: 'boot', t: 0, kind: 'sys', text: 'Console ready — waiting for a run' },
  ])
  const [planIdx, setPlanIdx] = useState(0)

  // Continuous planning chatter so the UI never goes silent between SSE events
  useEffect(() => {
    if (!isLive) return
    if (isPlanning) {
      const id = window.setInterval(() => {
        setPlanIdx((p) => {
          const next = (p + 1) % planningLines.length
          setFeed((prev) =>
            [
              {
                id: `plan-${Date.now()}`,
                t: Date.now(),
                kind: 'plan' as const,
                text: planningLines[next],
              },
              ...prev,
            ].slice(0, 40)
          )
          return next
        })
      }, 1600)
      return () => window.clearInterval(id)
    }
  }, [isLive, isPlanning, planningLines])

  // Mirror real phase/tool/step events into the feed
  useEffect(() => {
    if (status === 'connecting' || status === 'running') {
      setFeed((prev) => {
        if (prev[0]?.text === 'Run started') return prev
        const item: FeedItem = {
          id: `start-${Date.now()}`,
          t: Date.now(),
          kind: 'sys',
          text: 'Run started',
        }
        return [item, ...prev].slice(0, 40)
      })
    }
  }, [status])

  useEffect(() => {
    if (!isTool || !liveAction) return
    const label = TOOL_HELP[liveAction]?.short || liveAction
    setFeed((prev) =>
      [
        {
          id: `tool-${liveAction}-${Date.now()}`,
          t: Date.now(),
          kind: 'tool' as const,
          text: `Instrument ${label} engaged`,
        },
        ...prev,
      ].slice(0, 40)
    )
  }, [isTool, liveAction])

  useEffect(() => {
    if (!steps.length) return
    const s = steps[steps.length - 1]
    const label = TOOL_HELP[s.action]?.short || s.action
    setFeed((prev) =>
      [
        {
          id: `step-${s.step}-${Date.now()}`,
          t: Date.now(),
          kind: 'ok' as const,
          text: `Step ${s.step} · ${label} returned ${Math.min(s.observation?.length || 0, 9999)} chars`,
        },
        ...prev,
      ].slice(0, 40)
    )
  }, [steps.length])

  useEffect(() => {
    if (isDone) {
      setFeed((prev) =>
        [{ id: `done-${Date.now()}`, t: Date.now(), kind: 'ok' as const, text: 'Brief finalized' }, ...prev].slice(0, 40)
      )
    }
    if (isError) {
      setFeed((prev) =>
        [{ id: `err-${Date.now()}`, t: Date.now(), kind: 'err' as const, text: 'Run failed' }, ...prev].slice(0, 40)
      )
    }
  }, [isDone, isError])

  const nodeState = (tool: string): 'idle' | 'active' | 'done' | 'error' => {
    if (isError && liveAction === tool) return 'error'
    if (liveAction === tool && isLive) return 'active'
    if (steps.some((s) => s.action === tool) || (isDone && tool === 'finish')) return 'done'
    return 'idle'
  }

  const hardPct = maxSteps > 0 ? (steps.length / maxSteps) * 100 : 0
  const softPct = isLive && steps.length === 0 ? Math.min(18, elapsed * 2) : isLive ? Math.min(6, 2 + (elapsed % 8)) : 0
  const barPct = isDone ? 100 : Math.min(99, hardPct + softPct)

  const accent = theme.palette.primary.main
  const surface =
    theme.palette.mode === 'dark'
      ? 'linear-gradient(180deg, #121722 0%, #0c1018 100%)'
      : 'linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%)'

  const kindColor = (kind: FeedItem['kind']) => {
    switch (kind) {
      case 'plan':
        return theme.palette.info.main
      case 'tool':
        return theme.palette.warning.main
      case 'ok':
        return theme.palette.success.main
      case 'err':
        return theme.palette.error.main
      default:
        return theme.palette.text.secondary
    }
  }

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 420,
        borderRadius: 2.5,
        overflow: 'hidden',
        background: surface,
        border: `1px solid ${theme.palette.divider}`,
        boxShadow:
          theme.palette.mode === 'dark'
            ? '0 24px 60px rgba(0,0,0,0.35)'
            : '0 18px 40px rgba(15,23,42,0.08)',
        display: 'grid',
        gridTemplateRows: 'auto auto 1fr auto',
        gap: 0,
      }}
    >
      {/* Top progress rail */}
      <Box sx={{ px: 2, pt: 1.5, pb: 1 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.75 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary' }}>
            EXECUTION RAIL
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            {isLive && (
              <Chip
                size="small"
                color={isTool ? 'warning' : 'info'}
                label={isTool ? `${TOOL_HELP[liveAction || '']?.short || 'TOOL'} LIVE` : 'PLANNING'}
                sx={{ fontWeight: 700, height: 22 }}
              />
            )}
            <Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums', color: 'text.secondary' }}>
              {elapsed}s · {steps.length}/{maxSteps}
            </Typography>
          </Stack>
        </Stack>
        <LinearProgress
          variant="determinate"
          value={barPct}
          sx={{
            height: 4,
            borderRadius: 2,
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
            '& .MuiLinearProgress-bar': {
              borderRadius: 2,
              background: isDone
                ? theme.palette.success.main
                : `linear-gradient(90deg, ${accent}, ${theme.palette.info.main})`,
              transition: 'transform 0.35s ease',
            },
          }}
        />
      </Box>

      {/* Horizontal instrument pipeline — compact technical steps, not cartoon nodes */}
      <Box sx={{ px: 2, pb: 1.25 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: `repeat(${catalog.length}, minmax(0, 1fr))`,
            gap: 0.5,
          }}
        >
          {catalog.map((tool) => {
            const state = nodeState(tool)
            const short = TOOL_HELP[tool]?.short || tool.slice(0, 4).toUpperCase()
            const color =
              state === 'active'
                ? theme.palette.warning.main
                : state === 'done'
                  ? theme.palette.success.main
                  : state === 'error'
                    ? theme.palette.error.main
                    : theme.palette.mode === 'dark'
                      ? 'rgba(255,255,255,0.22)'
                      : 'rgba(0,0,0,0.22)'
            return (
              <Box
                key={tool}
                sx={{
                  px: 0.75,
                  py: 0.65,
                  borderRadius: 0.75,
                  border: `1px solid ${
                    state === 'idle'
                      ? theme.palette.divider
                      : color
                  }`,
                  bgcolor:
                    state === 'idle'
                      ? 'transparent'
                      : theme.palette.mode === 'dark'
                        ? `${color}14`
                        : `${color}12`,
                  minWidth: 0,
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.6, mb: 0.35 }}>
                  <Box
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: '1px',
                      bgcolor: color,
                      flexShrink: 0,
                      opacity: state === 'idle' ? 0.45 : 1,
                    }}
                  />
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: state === 'active' ? 750 : 650,
                      color: state === 'idle' ? 'text.secondary' : color,
                      fontSize: 10,
                      letterSpacing: 0.5,
                      textTransform: 'uppercase',
                      lineHeight: 1.1,
                    }}
                    noWrap
                  >
                    {short}
                  </Typography>
                </Box>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    color: 'text.disabled',
                    fontSize: 9,
                    textTransform: 'capitalize',
                    lineHeight: 1.2,
                  }}
                  noWrap
                >
                  {state === 'active' ? 'running' : state === 'done' ? 'done' : state === 'error' ? 'error' : 'idle'}
                </Typography>
              </Box>
            )
          })}
        </Box>
      </Box>

      {/* Main split: thought + feed */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1.35fr 1fr' },
          gap: 0,
          minHeight: 0,
          borderTop: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box
          sx={{
            p: 2,
            borderRight: { md: `1px solid ${theme.palette.divider}` },
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary', mb: 1 }}>
            REASONING STREAM
          </Typography>
          <Box
            sx={{
              flex: 1,
              minHeight: 140,
              p: 1.5,
              borderRadius: 1.5,
              bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.28)' : 'rgba(255,255,255,0.65)',
              border: `1px solid ${theme.palette.divider}`,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              fontSize: 13,
              lineHeight: 1.55,
              color: 'text.primary',
              overflow: 'auto',
            }}
          >
            {isLive && !typedThought && (
              <Typography component="span" sx={{ color: 'text.secondary' }}>
                {planningLines[planIdx]}
                {!reduceMotion && (
                  <Box
                    component={motion.span}
                    animate={{ opacity: [0.2, 1, 0.2] }}
                    transition={{ duration: 0.9, repeat: Infinity }}
                    sx={{ ml: 0.25 }}
                  >
                    ▍
                  </Box>
                )}
              </Typography>
            )}
            {typedThought && (
              <Typography component="span">
                {typedThought}
                {isLive && !reduceMotion && typedThought.length < (activeThought || '').length && (
                  <Box component="span" sx={{ opacity: 0.7 }}>
                    ▍
                  </Box>
                )}
              </Typography>
            )}
            {!isLive && !typedThought && (
              <Typography component="span" sx={{ color: 'text.secondary' }}>
                Idle. Set an objective and press Run — this stream fills as the model reasons.
              </Typography>
            )}
          </Box>

          {steps[steps.length - 1]?.observation && (
            <Box sx={{ mt: 1.25 }}>
              <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary' }}>
                LAST OBSERVATION
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  mt: 0.5,
                  color: 'text.secondary',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {steps[steps.length - 1].observation}
              </Typography>
            </Box>
          )}
        </Box>

        <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary', mb: 1 }}>
            ACTIVITY
          </Typography>
          <Box sx={{ flex: 1, overflow: 'auto', minHeight: 140, pr: 0.5 }}>
            <AnimatePresence initial={false}>
              {feed.map((item) => (
                <Box
                  component={motion.div}
                  key={item.id}
                  initial={reduceMotion ? false : { opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  sx={{
                    display: 'flex',
                    gap: 1,
                    alignItems: 'flex-start',
                    py: 0.65,
                    borderBottom: `1px solid ${theme.palette.divider}`,
                  }}
                >
                  <Box
                    sx={{
                      mt: 0.6,
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      bgcolor: kindColor(item.kind),
                      flexShrink: 0,
                    }}
                  />
                  <Typography
                    variant="caption"
                    sx={{
                      color: 'text.primary',
                      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                      lineHeight: 1.4,
                    }}
                  >
                    {item.text}
                  </Typography>
                </Box>
              ))}
            </AnimatePresence>
          </Box>
        </Box>
      </Box>

      {/* Live status line — full brief lives on the Brief Board below */}
      <Box
        sx={{
          px: 2,
          py: 0.85,
          borderTop: `1px solid ${theme.palette.divider}`,
          bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.18)' : 'rgba(255,255,255,0.4)',
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ fontVariantNumeric: 'tabular-nums' }}>
          {finalAnswer
            ? isError || /could not complete|failed|error/i.test(finalAnswer)
              ? 'Run ended — see Brief Board for the delivered answer.'
              : 'Brief ready — see Brief Board below.'
            : holding && isLive
              ? isTool
                ? 'Streaming tool output…'
                : 'Model deliberating…'
              : 'Awaiting run.'}
        </Typography>
      </Box>
    </Box>
  )
}

export default AgentTheaterScene
