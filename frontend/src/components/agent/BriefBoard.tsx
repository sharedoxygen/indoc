import React, { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Chip,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  Chat as ChatIcon,
  ContentCopy as CopyIcon,
  DeleteOutline as ClearIcon,
  DescriptionOutlined as BriefIcon,
  Replay as ReuseIcon,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import HelpTip from '../HelpTip'
import { AGENT_HELP } from './agentHelp'

export interface AgentRunRecord {
  id: string
  goal: string
  answer: string
  at: string
  steps: number
}

interface BriefBoardProps {
  runs: AgentRunRecord[]
  /** Prefer selecting this run id when it changes (e.g. newest completion). */
  focusRunId?: string | null
  onAskFollowUp?: (run: AgentRunRecord) => void
  onReuseGoal?: (goal: string) => void
  onClear?: () => void
}

function isPartial(answer: string) {
  return /could not complete|planning_failed|failed|error|unavailable/i.test(answer)
}

function formatWhen(iso: string) {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

function preview(text: string, n = 90) {
  const t = text.replace(/\s+/g, ' ').trim()
  return t.length > n ? `${t.slice(0, n)}…` : t
}

/** Session brief navigator — pick a run, read the full answer, act on it. */
export const BriefBoard: React.FC<BriefBoardProps> = ({
  runs,
  focusRunId,
  onAskFollowUp,
  onReuseGoal,
  onClear,
}) => {
  const theme = useTheme()
  const dark = theme.palette.mode === 'dark'
  const compact = useMediaQuery(theme.breakpoints.down('md'))
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (focusRunId && runs.some((r) => r.id === focusRunId)) {
      setSelectedId(focusRunId)
      return
    }
    if (!selectedId && runs[0]) setSelectedId(runs[0].id)
    if (selectedId && !runs.some((r) => r.id === selectedId)) {
      setSelectedId(runs[0]?.id ?? null)
    }
  }, [focusRunId, runs, selectedId])

  const selected = useMemo(
    () => runs.find((r) => r.id === selectedId) ?? runs[0] ?? null,
    [runs, selectedId]
  )

  const handleCopy = async () => {
    if (!selected) return
    try {
      await navigator.clipboard.writeText(
        `Objective: ${selected.goal}\n\n${selected.answer}`
      )
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      /* ignore */
    }
  }

  return (
    <Paper
      sx={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: { xs: 320, md: 360 },
        height: '100%',
        borderRadius: 2.5,
        border: '1px solid',
        borderColor: 'divider',
        overflow: 'hidden',
        background: dark
          ? 'linear-gradient(180deg, rgba(18,24,34,0.98) 0%, rgba(10,13,18,0.96) 100%)'
          : 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(246,248,251,0.96) 100%)',
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          px: 1.75,
          py: 1.1,
          borderBottom: '1px solid',
          borderColor: 'divider',
          gap: 1,
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" minWidth={0}>
          <BriefIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
          <Typography
            variant="subtitle2"
            sx={{ fontWeight: 750, letterSpacing: 0.4, whiteSpace: 'nowrap' }}
          >
            <HelpTip title={AGENT_HELP.arrivalBoard} underline={false}>
              Brief Board
            </HelpTip>
          </Typography>
          <Chip
            size="small"
            label={runs.length === 0 ? 'Empty' : `${runs.length} brief${runs.length === 1 ? '' : 's'}`}
            sx={{ height: 22, fontWeight: 700, borderRadius: 1 }}
          />
        </Stack>
        <Stack direction="row" spacing={0.5} alignItems="center">
          {onClear && runs.length > 0 && (
            <Tooltip title="Clear session briefs">
              <IconButton size="small" onClick={onClear} aria-label="Clear briefs">
                <ClearIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </Stack>

      {runs.length === 0 || !selected ? (
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            px: 3,
            py: 4,
            textAlign: 'center',
            gap: 1,
          }}
        >
          <BriefIcon sx={{ fontSize: 36, color: 'text.disabled', mb: 0.5 }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            No briefs yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 360 }}>
            Run a research objective above. When the agent finishes, the full answer appears here —
            pick any prior brief from the list to revisit it.
          </Typography>
        </Box>
      ) : (
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: 'grid',
            gridTemplateColumns: compact ? '1fr' : '240px 1fr',
            gridTemplateRows: compact ? 'auto 1fr' : '1fr',
          }}
        >
          {/* Run navigator */}
          <Box
            sx={{
              borderRight: compact ? 'none' : '1px solid',
              borderBottom: compact ? '1px solid' : 'none',
              borderColor: 'divider',
              maxHeight: compact ? 148 : 'none',
              overflow: 'auto',
              bgcolor: dark ? 'rgba(0,0,0,0.18)' : 'rgba(0,0,0,0.02)',
            }}
          >
            <List dense disablePadding>
              {runs.map((run, idx) => {
                const active = run.id === selected.id
                const partial = isPartial(run.answer)
                return (
                  <ListItemButton
                    key={run.id}
                    selected={active}
                    onClick={() => setSelectedId(run.id)}
                    sx={{
                      alignItems: 'flex-start',
                      py: 1.1,
                      px: 1.5,
                      borderLeft: '3px solid',
                      borderColor: active
                        ? partial
                          ? 'warning.main'
                          : 'primary.main'
                        : 'transparent',
                      '&.Mui-selected': {
                        bgcolor: dark ? 'rgba(56,189,248,0.08)' : 'rgba(25,118,210,0.06)',
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 0.35 }}>
                          <Typography
                            variant="caption"
                            sx={{
                              fontWeight: 800,
                              color: 'text.disabled',
                              fontVariantNumeric: 'tabular-nums',
                            }}
                          >
                            #{runs.length - idx}
                          </Typography>
                          <Chip
                            size="small"
                            color={partial ? 'warning' : 'success'}
                            variant={active ? 'filled' : 'outlined'}
                            label={partial ? 'Partial' : 'Brief'}
                            sx={{ height: 18, fontSize: 10, fontWeight: 750 }}
                          />
                          <Typography variant="caption" color="text.disabled" noWrap>
                            {formatWhen(run.at)}
                          </Typography>
                        </Stack>
                      }
                      secondary={
                        <>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: active ? 700 : 600,
                              color: 'text.primary',
                              lineHeight: 1.35,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {run.goal}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                              mt: 0.35,
                              display: '-webkit-box',
                              WebkitLineClamp: 1,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }}
                          >
                            {preview(run.answer)}
                          </Typography>
                        </>
                      }
                      secondaryTypographyProps={{ component: 'div' }}
                    />
                  </ListItemButton>
                )
              })}
            </List>
          </Box>

          {/* Reading pane */}
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              minWidth: 0,
            }}
          >
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1}
              alignItems={{ sm: 'center' }}
              justifyContent="space-between"
              sx={{ px: 2, py: 1.25, borderBottom: '1px solid', borderColor: 'divider' }}
            >
              <Box minWidth={0}>
                <Typography
                  variant="subtitle1"
                  sx={{
                    fontWeight: 750,
                    letterSpacing: '-0.015em',
                    lineHeight: 1.3,
                  }}
                >
                  {selected.goal}
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.4 }} flexWrap="wrap">
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`${selected.steps || 0} steps`}
                    sx={{ height: 22, fontWeight: 650 }}
                  />
                  <Chip
                    size="small"
                    color={isPartial(selected.answer) ? 'warning' : 'success'}
                    label={isPartial(selected.answer) ? 'Partial' : 'Complete'}
                    sx={{ height: 22, fontWeight: 700 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {formatWhen(selected.at)}
                  </Typography>
                </Stack>
              </Box>
              <Stack direction="row" spacing={0.75} flexShrink={0} flexWrap="wrap">
                {onReuseGoal && (
                  <Tooltip title="Put this objective back in the research field">
                    <Button
                      size="small"
                      startIcon={<ReuseIcon />}
                      onClick={() => onReuseGoal(selected.goal)}
                      sx={{ textTransform: 'none', fontWeight: 650, borderRadius: 999 }}
                    >
                      Reuse
                    </Button>
                  </Tooltip>
                )}
                <Tooltip title={copied ? 'Copied' : 'Copy objective + brief'}>
                  <Button
                    size="small"
                    startIcon={<CopyIcon />}
                    onClick={handleCopy}
                    sx={{ textTransform: 'none', fontWeight: 650, borderRadius: 999 }}
                  >
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </Tooltip>
                {onAskFollowUp && (
                  <Tooltip title={AGENT_HELP.askFollowUp}>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<ChatIcon />}
                      onClick={() => onAskFollowUp(selected)}
                      sx={{
                        textTransform: 'none',
                        fontWeight: 700,
                        borderRadius: 999,
                        boxShadow: '0 8px 20px rgba(25,118,210,0.28)',
                      }}
                    >
                      Ask follow-up
                    </Button>
                  </Tooltip>
                )}
              </Stack>
            </Stack>

            <Box
              sx={{
                flex: 1,
                minHeight: 0,
                overflow: 'auto',
                px: 2.25,
                py: 1.75,
              }}
            >
              <AnimatePresence mode="wait">
                <Box
                  key={selected.id}
                  component={motion.div}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.2 }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      color: 'text.disabled',
                      fontWeight: 700,
                      letterSpacing: 0.8,
                      mb: 1,
                    }}
                  >
                    ANSWER
                  </Typography>
                  <Typography
                    variant="body1"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.65,
                      letterSpacing: '0.005em',
                      color: 'text.primary',
                    }}
                  >
                    {selected.answer}
                  </Typography>
                </Box>
              </AnimatePresence>
            </Box>

            <Divider />
            <Typography
              variant="caption"
              color="text.disabled"
              sx={{ px: 2, py: 0.85, letterSpacing: 0.2 }}
            >
              Session only · select a brief on the left to switch · Ask follow-up opens chat on this answer
            </Typography>
          </Box>
        </Box>
      )}
    </Paper>
  )
}

export default BriefBoard
