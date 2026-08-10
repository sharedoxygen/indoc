import React, { useEffect, useMemo, useState } from 'react'
import { Box, Chip, Stack, Tooltip, Typography, useTheme } from '@mui/material'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import type { AgentStep, AgentStreamStatus } from '../../hooks/useAgentStream'
import HelpTip from '../HelpTip'
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
  tools: string[]
  steps: AgentStep[]
  holding: boolean
  finalAnswer: string | null
}

function toolPosition(index: number, total: number, cx: number, cy: number, r: number) {
  const angle = -Math.PI / 2 + (index / Math.max(total, 1)) * Math.PI * 2
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle), angle }
}

export const AgentTheaterScene: React.FC<AgentTheaterSceneProps> = ({
  status,
  tools,
  steps,
  holding,
  finalAnswer,
}) => {
  const theme = useTheme()
  const reduceMotion = useReducedMotion()
  const [visible, setVisible] = useState(true)
  const W = 960
  const H = 540
  const cx = W / 2
  const cy = H / 2 + 10
  const ringR = 170

  useEffect(() => {
    const onVis = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  const activeTools = tools.length ? tools : DEFAULT_TOOLS
  const pads = useMemo(
    () => activeTools.map((t, i) => ({ tool: t, ...toolPosition(i, activeTools.length, cx, cy, ringR) })),
    [activeTools, cx, cy, ringR]
  )

  const latest = steps[steps.length - 1]
  const activeTool = latest?.action
  const particles = useMemo(
    () =>
      Array.from({ length: reduceMotion || !visible ? 8 : 28 }, (_, i) => ({
        id: i,
        x: (i * 97) % W,
        y: (i * 53) % H,
        d: 4 + (i % 5),
        delay: (i % 7) * 0.35,
      })),
    [reduceMotion, visible]
  )

  const isRunning = status === 'running' || status === 'connecting'
  const isDone = status === 'completed'
  const isError = status === 'error'

  const sky =
    theme.palette.mode === 'dark'
      ? 'radial-gradient(ellipse at 50% 20%, #1a2744 0%, #0b1020 55%, #070a12 100%)'
      : 'radial-gradient(ellipse at 50% 15%, #d9e8ff 0%, #eef3f8 45%, #d5dde8 100%)'

  const radioText = isError
    ? 'Error talking to the agent. Check the message below or try again.'
    : latest?.thought ||
      (isRunning
        ? 'Thinking — choosing the next tool…'
        : isDone
          ? 'Done. Final answer is on the Arrival card / board.'
          : 'Ready. Enter a goal above and press Launch.')

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 420,
        borderRadius: 3,
        overflow: 'hidden',
        background: sky,
        border: `1px solid ${theme.palette.divider}`,
        boxShadow: theme.shadows[8],
      }}
    >
      <Tooltip title={AGENT_HELP.radar} arrow placement="top">
        <Box
          sx={{
            position: 'absolute',
            top: 12,
            left: 16,
            zIndex: 2,
            cursor: 'help',
            px: 1,
            py: 0.5,
            borderRadius: 1,
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(8,12,22,0.55)' : 'rgba(255,255,255,0.7)',
            backdropFilter: 'blur(6px)',
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: 0.6 }}>
            TOOL RADAR · hover pads for help
          </Typography>
        </Box>
      </Tooltip>

      {/* Parallax haze layers */}
      <Box
        component={motion.div}
        animate={reduceMotion || !visible ? undefined : { x: [0, 12, 0], opacity: [0.35, 0.5, 0.35] }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        sx={{
          position: 'absolute',
          inset: '-10%',
          background:
            theme.palette.mode === 'dark'
              ? 'radial-gradient(circle at 30% 40%, rgba(56,120,200,0.18), transparent 40%), radial-gradient(circle at 70% 60%, rgba(40,160,140,0.12), transparent 35%)'
              : 'radial-gradient(circle at 30% 40%, rgba(25,118,210,0.12), transparent 40%), radial-gradient(circle at 70% 55%, rgba(0,150,120,0.08), transparent 35%)',
          pointerEvents: 'none',
        }}
      />

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
        {/* Radar grid */}
        <g opacity={theme.palette.mode === 'dark' ? 0.22 : 0.18}>
          {[60, 120, 180, 240].map((r) => (
            <circle key={r} cx={cx} cy={cy} r={r} fill="none" stroke={theme.palette.info.main} strokeWidth={0.6} />
          ))}
          {[0, 45, 90, 135].map((a) => {
            const rad = (a * Math.PI) / 180
            return (
              <line
                key={a}
                x1={cx - 250 * Math.cos(rad)}
                y1={cy - 250 * Math.sin(rad)}
                x2={cx + 250 * Math.cos(rad)}
                y2={cy + 250 * Math.sin(rad)}
                stroke={theme.palette.info.main}
                strokeWidth={0.5}
              />
            )
          })}
        </g>

        {/* Radar sweep */}
        {!reduceMotion && visible && (
          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            animate={{ rotate: 360 }}
            transition={{ duration: isRunning ? 4.5 : 10, repeat: Infinity, ease: 'linear' }}
          >
            <path
              d={`M ${cx} ${cy} L ${cx} ${cy - 240} A 240 240 0 0 1 ${cx + 120} ${cy - 208} Z`}
              fill={theme.palette.mode === 'dark' ? 'rgba(100,180,255,0.12)' : 'rgba(25,118,210,0.1)'}
            />
          </motion.g>
        )}

        {/* Runway */}
        <g opacity={0.7}>
          <rect
            x={cx - 180}
            y={H - 70}
            width={360}
            height={18}
            rx={3}
            fill={theme.palette.mode === 'dark' ? '#2a3348' : '#6b7280'}
          />
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
            <motion.rect
              key={i}
              x={cx - 170 + i * 44}
              y={H - 64}
              width={22}
              height={4}
              fill="#f8fafc"
              animate={
                reduceMotion || !visible
                  ? undefined
                  : { opacity: isDone ? [1, 0.3, 1] : [0.4, 1, 0.4] }
              }
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.12 }}
            />
          ))}
        </g>

        {/* Tool airports */}
        {pads.map((pad) => {
          const active = activeTool === pad.tool
          const used = steps.some((s) => s.action === pad.tool)
          const fill = active
            ? theme.palette.warning.main
            : used
              ? theme.palette.success.main
              : theme.palette.mode === 'dark'
                ? '#1e293b'
                : '#cbd5e1'
          const meta = TOOL_HELP[pad.tool]
          return (
            <g key={pad.tool}>
              <title>
                {meta ? `${meta.short}: ${meta.help}` : pad.tool}
              </title>
              <motion.circle
                cx={pad.x}
                cy={pad.y}
                r={active ? 22 : 16}
                fill={fill}
                stroke={theme.palette.background.paper}
                strokeWidth={2}
                style={{ cursor: 'help' }}
                animate={
                  active && !reduceMotion
                    ? { scale: [1, 1.12, 1], opacity: [0.85, 1, 0.85] }
                    : { scale: 1, opacity: 1 }
                }
                transition={{ duration: 1.4, repeat: active ? Infinity : 0 }}
              />
              <text
                x={pad.x}
                y={pad.y + 36}
                textAnchor="middle"
                fill={theme.palette.text.primary}
                fontSize={11}
                fontWeight={700}
                style={{ letterSpacing: 0.6, cursor: 'help' }}
              >
                {meta?.short || pad.tool.slice(0, 6).toUpperCase()}
              </text>
              {active && (
                <motion.circle
                  cx={pad.x}
                  cy={pad.y}
                  r={28}
                  fill="none"
                  stroke={theme.palette.warning.main}
                  strokeWidth={1.5}
                  initial={{ opacity: 0.8, scale: 0.8 }}
                  animate={{ opacity: 0, scale: 1.6 }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              )}
            </g>
          )
        })}

        {/* Center tower hub */}
        <g style={{ cursor: 'help' }}>
          <title>{AGENT_HELP.atcHub}</title>
          <circle
            cx={cx}
            cy={cy}
            r={34}
            fill={theme.palette.mode === 'dark' ? '#0f172a' : '#ffffff'}
            stroke={isError ? theme.palette.error.main : isDone ? theme.palette.success.main : theme.palette.primary.main}
            strokeWidth={3}
          />
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            fill={theme.palette.text.primary}
            fontSize={12}
            fontWeight={800}
          >
            AGENT
          </text>
          <text x={cx} y={cy + 14} textAnchor="middle" fill={theme.palette.text.secondary} fontSize={9}>
            PLANNER
          </text>
        </g>

        {/* Aircraft per step */}
        {steps.map((step, idx) => {
          const pad = pads.find((p) => p.tool === step.action) || pads[idx % pads.length]
          const startAngle = (-90 + idx * 28) * (Math.PI / 180)
          const sx = cx + 50 * Math.cos(startAngle)
          const sy = cy + 50 * Math.sin(startAngle)
          const isLatest = idx === steps.length - 1
          return (
            <g key={`craft-${step.step}`}>
              <title>
                Step {step.step}: {TOOL_HELP[step.action]?.short || step.action}
              </title>
              <motion.path
                d={`M ${sx} ${sy} Q ${(sx + pad.x) / 2 + 40} ${(sy + pad.y) / 2 - 50} ${pad.x} ${pad.y}`}
                fill="none"
                stroke={theme.palette.info.main}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: isLatest ? 0.9 : 0.35 }}
                transition={{ duration: reduceMotion ? 0 : 1.1 }}
              />
              <motion.g
                initial={{ x: sx, y: sy, opacity: 0 }}
                animate={{ x: pad.x, y: pad.y - 8, opacity: 1 }}
                transition={{ duration: reduceMotion ? 0 : 1.15, ease: [0.22, 1, 0.36, 1] }}
              >
                <polygon
                  points="0,-10 7,8 0,4 -7,8"
                  fill={isLatest ? theme.palette.secondary.main : theme.palette.primary.light}
                  stroke={theme.palette.background.paper}
                  strokeWidth={1}
                />
              </motion.g>
            </g>
          )
        })}

        {/* Holding pattern orbit while waiting */}
        {holding && isRunning && !reduceMotion && (
          <motion.g
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            animate={{ rotate: 360 }}
            transition={{ duration: 3.2, repeat: Infinity, ease: 'linear' }}
          >
            <title>{AGENT_HELP.holding}</title>
            <polygon points={`${cx},${cy - 95} ${cx + 6},${cy - 80} ${cx - 6},${cy - 80}`} fill={theme.palette.warning.main} />
            <circle cx={cx} cy={cy - 88} r={14} fill="none" stroke={theme.palette.warning.main} strokeWidth={1} opacity={0.5} />
          </motion.g>
        )}

        {/* Particles */}
        {particles.map((p) => (
          <motion.circle
            key={p.id}
            cx={p.x}
            cy={p.y}
            r={1.2}
            fill={theme.palette.info.light}
            animate={reduceMotion || !visible ? undefined : { opacity: [0.1, 0.7, 0.1], y: [p.y, p.y - p.d * 6, p.y] }}
            transition={{ duration: 5 + p.delay, repeat: Infinity, delay: p.delay }}
          />
        ))}

        {/* Final landing sweep */}
        {isDone && (
          <motion.rect
            x={0}
            y={0}
            width={W}
            height={H}
            fill={theme.palette.success.main}
            initial={{ opacity: 0.25 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 1.4 }}
          />
        )}
      </svg>

      {/* HTML hover targets over tool pads (MUI tooltips; SVG titles as fallback) */}
      {pads.map((pad) => {
        const meta = TOOL_HELP[pad.tool]
        const active = activeTool === pad.tool
        const used = steps.some((s) => s.action === pad.tool)
        return (
          <Tooltip
            key={`tip-${pad.tool}`}
            arrow
            title={
              <Box sx={{ maxWidth: 260 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {meta?.short || pad.tool} · {pad.tool}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5, lineHeight: 1.4 }}>
                  {meta?.help || pad.tool}
                </Typography>
                <Typography variant="caption" sx={{ display: 'block', mt: 0.75, opacity: 0.85 }}>
                  {active ? 'In use now' : used ? 'Used earlier this run' : 'Not used yet'}
                </Typography>
              </Box>
            }
          >
            <Box
              sx={{
                position: 'absolute',
                left: `${(pad.x / W) * 100}%`,
                top: `${(pad.y / H) * 100}%`,
                width: 44,
                height: 52,
                transform: 'translate(-50%, -40%)',
                cursor: 'help',
                zIndex: 3,
              }}
              aria-label={meta?.help || pad.tool}
            />
          </Tooltip>
        )
      })}

      <Tooltip title={AGENT_HELP.atcHub} arrow>
        <Box
          sx={{
            position: 'absolute',
            left: `${(cx / W) * 100}%`,
            top: `${(cy / H) * 100}%`,
            width: 68,
            height: 68,
            transform: 'translate(-50%, -50%)',
            cursor: 'help',
            zIndex: 3,
            borderRadius: '50%',
          }}
          aria-label="Agent planner"
        />
      </Tooltip>

      {/* Tool legend */}
      <Stack
        direction="row"
        spacing={0.75}
        useFlexGap
        flexWrap="wrap"
        sx={{
          position: 'absolute',
          top: 40,
          right: 16,
          maxWidth: 280,
          zIndex: 2,
          justifyContent: 'flex-end',
        }}
      >
        {activeTools.map((t) => {
          const meta = TOOL_HELP[t]
          const active = activeTool === t
          const used = steps.some((s) => s.action === t)
          return (
            <Tooltip key={`leg-${t}`} title={meta?.help || t} arrow>
              <Chip
                size="small"
                label={meta?.short || t}
                color={active ? 'warning' : used ? 'success' : 'default'}
                variant={active || used ? 'filled' : 'outlined'}
                sx={{ cursor: 'help', height: 22, fontSize: 11, fontWeight: 700 }}
              />
            </Tooltip>
          )
        })}
      </Stack>

      {/* Thought radio glass panel */}
      <Box
        sx={{
          position: 'absolute',
          left: 16,
          bottom: 16,
          right: 16,
          maxWidth: 420,
          p: 1.5,
          borderRadius: 2,
          bgcolor: theme.palette.mode === 'dark' ? 'rgba(8,12,22,0.72)' : 'rgba(255,255,255,0.78)',
          backdropFilter: 'blur(10px)',
          border: `1px solid ${theme.palette.divider}`,
          zIndex: 2,
        }}
      >
        <Typography
          variant="caption"
          sx={{ color: 'text.secondary', fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase' }}
        >
          <HelpTip title={AGENT_HELP.towerRadio}>Agent thinking</HelpTip>
        </Typography>
        <AnimatePresence mode="wait">
          <Typography
            component={motion.div}
            key={latest?.thought || status}
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            sx={{ mt: 0.5, fontSize: 13, lineHeight: 1.45, color: 'text.primary', minHeight: 40 }}
          >
            {radioText}
          </Typography>
        </AnimatePresence>
        {latest?.observation && (
          <Tooltip title={AGENT_HELP.cargo} arrow>
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                mt: 1,
                color: 'text.secondary',
                maxHeight: 48,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                cursor: 'help',
              }}
            >
              Last tool result: {latest.observation.slice(0, 160)}
              {latest.observation.length > 160 ? '…' : ''}
            </Typography>
          </Tooltip>
        )}
      </Box>

      {/* Final answer card */}
      {finalAnswer && (
        <Box
          component={motion.div}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          sx={{
            position: 'absolute',
            right: 16,
            top: 72,
            maxWidth: 320,
            p: 1.5,
            borderRadius: 2,
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(12,28,18,0.85)' : 'rgba(232,245,233,0.92)',
            border: `1px solid ${theme.palette.success.main}`,
            backdropFilter: 'blur(8px)',
            zIndex: 2,
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 800, color: 'success.main', letterSpacing: 1 }}>
            <HelpTip title={AGENT_HELP.arrival} underline={false}>
              FINAL ANSWER
            </HelpTip>
          </Typography>
          <Typography sx={{ mt: 0.5, fontSize: 13, lineHeight: 1.4, maxHeight: 120, overflow: 'auto' }}>
            {finalAnswer.slice(0, 420)}
            {finalAnswer.length > 420 ? '…' : ''}
          </Typography>
        </Box>
      )}
    </Box>
  )
}

export default AgentTheaterScene
