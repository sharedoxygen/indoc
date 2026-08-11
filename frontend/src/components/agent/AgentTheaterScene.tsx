import React, { useEffect, useMemo, useState } from 'react'
import { Box, Tooltip, Typography, useTheme } from '@mui/material'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import type { AgentPhase, AgentStep, AgentStreamStatus } from '../../hooks/useAgentStream'
import { AGENT_HELP, TOOL_HELP } from './agentHelp'

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
}

function toolPosition(index: number, total: number, cx: number, cy: number, r: number) {
  const angle = -Math.PI / 2 + (index / Math.max(total, 1)) * Math.PI * 2
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), angle }
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
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const [visible, setVisible] = useState(true)
  const [tick, setTick] = useState(0)
  const W = 960
  const H = 540
  const cx = W / 2
  const cy = H / 2 + 10
  const ringR = 175

  useEffect(() => {
    const onVis = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  // Drive subtle UI pulse clock while running (paused when tab hidden)
  useEffect(() => {
    if (!visible || reduceMotion || (status !== 'running' && status !== 'connecting')) return
    const id = window.setInterval(() => setTick((t) => t + 1), 80)
    return () => window.clearInterval(id)
  }, [visible, reduceMotion, status])

  const activeTools = tools.length ? tools : DEFAULT_TOOLS
  const pads = useMemo(
    () => activeTools.map((t, i) => ({ tool: t, ...toolPosition(i, activeTools.length, cx, cy, ringR) })),
    [activeTools, cx, cy, ringR]
  )

  const latest = steps[steps.length - 1]
  const liveAction = activeAction || latest?.action || null
  const isRunning = status === 'running' || status === 'connecting'
  const isPlanning = phase === 'planning' || phase === 'connecting'
  const isTool = phase === 'tool'
  const isDone = status === 'completed'
  const isError = status === 'error'

  const particles = useMemo(
    () =>
      Array.from({ length: reduceMotion || !visible ? 10 : 42 }, (_, i) => ({
        id: i,
        x: (i * 97 + tick * (0.4 + (i % 3) * 0.15)) % W,
        y: (i * 53 + Math.sin((tick + i) * 0.08) * 8) % H,
        r: 1 + (i % 3) * 0.4,
      })),
    [reduceMotion, visible, tick]
  )

  const sky =
    theme.palette.mode === 'dark'
      ? 'radial-gradient(ellipse at 50% 18%, #1c2f52 0%, #0b1224 52%, #060912 100%)'
      : 'radial-gradient(ellipse at 50% 12%, #d7e7ff 0%, #eef3f8 48%, #d5dde8 100%)'

  const radioText = isError
    ? 'Signal interrupted — research channel error.'
    : activeThought ||
      latest?.thought ||
      (isPlanning && isRunning
        ? 'Planner deliberating — selecting the next instrument…'
        : isTool
          ? `Executing ${TOOL_HELP[liveAction || '']?.short || liveAction || 'tool'}…`
          : isDone
            ? 'Brief complete. Delivery on the board below.'
            : 'Ready. Set an objective and press Run.')

  const activePad = pads.find((p) => p.tool === liveAction)

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 460,
        borderRadius: 3,
        overflow: 'hidden',
        background: sky,
        border: `1px solid ${theme.palette.divider}`,
        boxShadow: theme.shadows[10],
      }}
    >
      {/* Ambient energy field */}
      <Box
        component={motion.div}
        animate={
          reduceMotion || !visible
            ? undefined
            : {
                opacity: isRunning ? [0.35, 0.65, 0.35] : [0.2, 0.35, 0.2],
                scale: isRunning ? [1, 1.04, 1] : [1, 1.01, 1],
              }
        }
        transition={{ duration: isRunning ? 3.2 : 8, repeat: Infinity, ease: 'easeInOut' }}
        sx={{
          position: 'absolute',
          inset: '-15%',
          background:
            theme.palette.mode === 'dark'
              ? 'radial-gradient(circle at 35% 40%, rgba(56,140,255,0.22), transparent 42%), radial-gradient(circle at 70% 55%, rgba(0,200,170,0.14), transparent 38%)'
              : 'radial-gradient(circle at 35% 40%, rgba(25,118,210,0.14), transparent 42%), radial-gradient(circle at 70% 55%, rgba(0,150,120,0.1), transparent 38%)',
          pointerEvents: 'none',
        }}
      />

      <Tooltip title={AGENT_HELP.radar} arrow placement="top">
        <Box
          sx={{
            position: 'absolute',
            top: 12,
            left: 16,
            zIndex: 2,
            cursor: 'help',
            px: 1.25,
            py: 0.5,
            borderRadius: 1,
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(8,12,22,0.6)' : 'rgba(255,255,255,0.75)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.secondary', letterSpacing: 0.8 }}>
            LIVE ORCHESTRATION
          </Typography>
        </Box>
      </Tooltip>

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={theme.palette.primary.main} stopOpacity="0.55" />
            <stop offset="100%" stopColor={theme.palette.primary.main} stopOpacity="0" />
          </radialGradient>
          <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Grid rings */}
        <g opacity={theme.palette.mode === 'dark' ? 0.28 : 0.2}>
          {[55, 110, 165, 220].map((r) => (
            <circle key={r} cx={cx} cy={cy} r={r} fill="none" stroke={theme.palette.info.main} strokeWidth={0.7} />
          ))}
          {[0, 30, 60, 90, 120, 150].map((a) => {
            const rad = (a * Math.PI) / 180
            return (
              <line
                key={a}
                x1={cx - 240 * Math.cos(rad)}
                y1={cy - 240 * Math.sin(rad)}
                x2={cx + 240 * Math.cos(rad)}
                y2={cy + 240 * Math.sin(rad)}
                stroke={theme.palette.info.main}
                strokeWidth={0.45}
              />
            )
          })}
        </g>

        {/* Sweep — faster while planning/tool */}
        {!reduceMotion && visible && (
          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            animate={{ rotate: 360 }}
            transition={{
              duration: isTool ? 2.4 : isPlanning && isRunning ? 3.2 : 9,
              repeat: Infinity,
              ease: 'linear',
            }}
          >
            <path
              d={`M ${cx} ${cy} L ${cx} ${cy - 250} A 250 250 0 0 1 ${cx + 140} ${cy - 208} Z`}
              fill={
                theme.palette.mode === 'dark'
                  ? 'rgba(120,190,255,0.16)'
                  : 'rgba(25,118,210,0.12)'
              }
            />
          </motion.g>
        )}

        {/* Energy beam to active tool */}
        {activePad && isRunning && (
          <motion.line
            x1={cx}
            y1={cy}
            x2={activePad.x}
            y2={activePad.y}
            stroke={isTool ? theme.palette.warning.main : theme.palette.primary.light}
            strokeWidth={2.5}
            strokeLinecap="round"
            filter="url(#softGlow)"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{
              opacity: [0.35, 1, 0.35],
              strokeDashoffset: [0, -24],
            }}
            transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
            strokeDasharray="8 6"
          />
        )}

        {/* Tool nodes */}
        {pads.map((pad) => {
          const active = liveAction === pad.tool && isRunning
          const used = steps.some((s) => s.action === pad.tool) || (isDone && pad.tool === 'finish')
          const meta = TOOL_HELP[pad.tool]
          const fill = active
            ? theme.palette.warning.main
            : used
              ? theme.palette.success.main
              : theme.palette.mode === 'dark'
                ? '#1e293b'
                : '#cbd5e1'
          return (
            <g key={pad.tool}>
              {active && !reduceMotion && (
                <>
                  <motion.circle
                    cx={pad.x}
                    cy={pad.y}
                    r={34}
                    fill="none"
                    stroke={theme.palette.warning.main}
                    strokeWidth={2}
                    initial={{ opacity: 0.9, scale: 0.7 }}
                    animate={{ opacity: 0, scale: 1.8 }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                  />
                  <motion.circle
                    cx={pad.x}
                    cy={pad.y}
                    r={26}
                    fill="none"
                    stroke={theme.palette.secondary.main}
                    strokeWidth={1.5}
                    initial={{ opacity: 0.7, scale: 0.85 }}
                    animate={{ opacity: 0, scale: 1.55 }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: 0.35 }}
                  />
                </>
              )}
              <motion.circle
                cx={pad.x}
                cy={pad.y}
                r={active ? 24 : used ? 18 : 15}
                fill={fill}
                stroke={theme.palette.background.paper}
                strokeWidth={2}
                filter={active ? 'url(#softGlow)' : undefined}
                animate={
                  active && !reduceMotion
                    ? { scale: [1, 1.14, 1] }
                    : { scale: 1 }
                }
                transition={{ duration: 0.9, repeat: active ? Infinity : 0 }}
              />
              <text
                x={pad.x}
                y={pad.y + 40}
                textAnchor="middle"
                fill={theme.palette.text.primary}
                fontSize={11}
                fontWeight={800}
                style={{ letterSpacing: 0.7 }}
              >
                {meta?.short || pad.tool.slice(0, 6).toUpperCase()}
              </text>
              <title>{meta?.help || pad.tool}</title>
            </g>
          )
        })}

        {/* Planner hub */}
        <circle cx={cx} cy={cy} r={58} fill="url(#hubGlow)" opacity={isPlanning && isRunning ? 0.95 : 0.55} />
        <motion.circle
          cx={cx}
          cy={cy}
          r={36}
          fill={theme.palette.mode === 'dark' ? '#0f172a' : '#ffffff'}
          stroke={
            isError
              ? theme.palette.error.main
              : isDone
                ? theme.palette.success.main
                : isTool
                  ? theme.palette.warning.main
                  : theme.palette.primary.main
          }
          strokeWidth={3.5}
          filter="url(#softGlow)"
          animate={
            isPlanning && isRunning && !reduceMotion
              ? { scale: [1, 1.08, 1], rotate: [0, 6, -6, 0] }
              : { scale: 1 }
          }
          transition={{ duration: 1.6, repeat: isPlanning && isRunning ? Infinity : 0 }}
          style={{ transformOrigin: `${cx}px ${cy}px` }}
        />
        <text x={cx} y={cy - 4} textAnchor="middle" fill={theme.palette.text.primary} fontSize={11} fontWeight={800}>
          {isPlanning && isRunning ? 'PLANNING' : isTool ? 'EXECUTING' : isDone ? 'COMPLETE' : 'PLANNER'}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill={theme.palette.text.secondary} fontSize={9}>
          INSIGHT BRIDGE
        </text>

        {/* Packet / craft traveling to active pad */}
        {activePad && isRunning && !reduceMotion && (
          <motion.g
            animate={{
              x: [cx, (cx + activePad.x) / 2 + 20, activePad.x],
              y: [cy, (cy + activePad.y) / 2 - 30, activePad.y],
            }}
            transition={{ duration: 1.35, repeat: Infinity, ease: 'easeInOut' }}
          >
            <polygon
              points="0,-9 7,7 0,3 -7,7"
              fill={isTool ? theme.palette.warning.main : theme.palette.info.main}
              stroke={theme.palette.background.paper}
              strokeWidth={1}
            />
          </motion.g>
        )}

        {/* Completed flight trails */}
        {steps.map((step, idx) => {
          const pad = pads.find((p) => p.tool === step.action) || pads[idx % pads.length]
          return (
            <motion.path
              key={`trail-${step.step}`}
              d={`M ${cx} ${cy} Q ${(cx + pad.x) / 2 + 35} ${(cy + pad.y) / 2 - 45} ${pad.x} ${pad.y}`}
              fill="none"
              stroke={theme.palette.info.main}
              strokeWidth={1.4}
              strokeDasharray="5 5"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.45 }}
              transition={{ duration: 0.8 }}
            />
          )
        })}

        {/* Particles */}
        {particles.map((p) => (
          <circle key={p.id} cx={p.x} cy={p.y} r={p.r} fill={theme.palette.info.light} opacity={0.35} />
        ))}

        {isDone && (
          <motion.rect
            x={0}
            y={0}
            width={W}
            height={H}
            fill={theme.palette.success.main}
            initial={{ opacity: 0.28 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 1.5 }}
          />
        )}
      </svg>

      {/* Thinking panel */}
      <Box
        sx={{
          position: 'absolute',
          left: 16,
          bottom: 16,
          right: { xs: 16, md: 'auto' },
          maxWidth: 440,
          p: 1.5,
          borderRadius: 2,
          bgcolor: theme.palette.mode === 'dark' ? 'rgba(8,12,22,0.78)' : 'rgba(255,255,255,0.82)',
          backdropFilter: 'blur(12px)',
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Typography
          variant="caption"
          sx={{ color: 'text.secondary', fontWeight: 800, letterSpacing: 1, textTransform: 'uppercase' }}
        >
          {isPlanning && isRunning ? 'Planner' : isTool ? 'Instrument feed' : 'Status'}
        </Typography>
        <AnimatePresence mode="wait">
          <Typography
            component={motion.div}
            key={radioText.slice(0, 48)}
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            sx={{ mt: 0.5, fontSize: 13, lineHeight: 1.45, minHeight: 40 }}
          >
            {radioText}
          </Typography>
        </AnimatePresence>
        {latest?.observation && (
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mt: 1,
              color: 'text.secondary',
              maxHeight: 52,
              overflow: 'hidden',
            }}
          >
            Result: {latest.observation.slice(0, 180)}
            {latest.observation.length > 180 ? '…' : ''}
          </Typography>
        )}
      </Box>

      {finalAnswer && (
        <Box
          component={motion.div}
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          sx={{
            position: 'absolute',
            right: 16,
            top: 16,
            maxWidth: 340,
            p: 1.5,
            borderRadius: 2,
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(12,28,18,0.88)' : 'rgba(232,245,233,0.94)',
            border: `1px solid ${theme.palette.success.main}`,
            backdropFilter: 'blur(10px)',
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 800, color: 'success.main', letterSpacing: 1 }}>
            BRIEF DELIVERED
          </Typography>
          <Typography sx={{ mt: 0.5, fontSize: 13, lineHeight: 1.4, maxHeight: 140, overflow: 'auto' }}>
            {finalAnswer.slice(0, 420)}
            {finalAnswer.length > 420 ? '…' : ''}
          </Typography>
        </Box>
      )}

      {holding && isRunning && (
        <Box
          component={motion.div}
          animate={{ opacity: [0.55, 1, 0.55] }}
          transition={{ duration: 1.2, repeat: Infinity }}
          sx={{
            position: 'absolute',
            top: 12,
            right: 16,
            px: 1.25,
            py: 0.5,
            borderRadius: 1,
            bgcolor: isTool ? 'warning.main' : 'info.main',
            color: 'common.white',
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: 0.6,
          }}
        >
          {isTool ? 'TOOL LIVE' : 'PLANNING'}
        </Box>
      )}
    </Box>
  )
}

export default AgentTheaterScene
