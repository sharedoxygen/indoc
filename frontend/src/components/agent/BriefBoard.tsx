import React, { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  IconButton,
  List,
  ListItemButton,
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

/** Session brief library — clean list + readable answer pane. */
export const BriefBoard: React.FC<BriefBoardProps> = ({
  runs,
  focusRunId,
  onAskFollowUp,
  onReuseGoal,
  onClear,
}) => {
  const theme = useTheme()
  const dark = theme.palette.mode === 'dark'
  const narrow = useMediaQuery(theme.breakpoints.down('sm'))
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
      await navigator.clipboard.writeText(`Objective: ${selected.goal}\n\n${selected.answer}`)
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
        height: '100%',
        minHeight: 0,
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        overflow: 'hidden',
        bgcolor: dark ? 'rgba(12,16,22,0.96)' : 'background.paper',
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          px: 1.5,
          py: 0.9,
          borderBottom: '1px solid',
          borderColor: 'divider',
          flexShrink: 0,
          minWidth: 0,
        }}
      >
        <Stack direction="row" spacing={0.75} alignItems="center" minWidth={0} sx={{ overflow: 'hidden' }}>
          <BriefIcon sx={{ fontSize: 16, color: 'text.secondary', flexShrink: 0 }} />
          <Typography
            variant="caption"
            sx={{ fontWeight: 750, letterSpacing: 0.6, textTransform: 'uppercase', flexShrink: 0 }}
          >
            <HelpTip title={AGENT_HELP.arrivalBoard} underline={false}>
              Briefs
            </HelpTip>
          </Typography>
          <Typography variant="caption" color="text.disabled" sx={{ fontVariantNumeric: 'tabular-nums' }}>
            {runs.length}
          </Typography>
        </Stack>
        {onClear && runs.length > 0 && (
          <Tooltip title="Clear session briefs">
            <IconButton size="small" onClick={onClear} aria-label="Clear briefs">
              <ClearIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Tooltip>
        )}
      </Stack>

      {runs.length === 0 || !selected ? (
        <Box
          sx={{
            flex: 1,
            display: 'grid',
            placeItems: 'center',
            px: 3,
            py: 3,
            textAlign: 'center',
          }}
        >
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
              No briefs yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 280, mx: 'auto' }}>
              Finished research answers appear here. Select a brief to read the full result.
            </Typography>
          </Box>
        </Box>
      ) : (
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: '200px minmax(0, 1fr)', lg: '220px minmax(0, 1fr)' },
            gridTemplateRows: { xs: '132px minmax(0, 1fr)', sm: 'minmax(0, 1fr)' },
          }}
        >
          {/* Navigator — goal + meta only; no chip pile */}
          <Box
            sx={{
              borderRight: { sm: '1px solid' },
              borderBottom: { xs: '1px solid', sm: 'none' },
              borderColor: 'divider',
              overflow: 'auto',
              minWidth: 0,
              bgcolor: dark ? 'rgba(0,0,0,0.22)' : 'rgba(0,0,0,0.02)',
            }}
          >
            <List disablePadding dense>
              {runs.map((run) => {
                const active = run.id === selected.id
                const partial = isPartial(run.answer)
                return (
                  <ListItemButton
                    key={run.id}
                    selected={active}
                    onClick={() => setSelectedId(run.id)}
                    sx={{
                      display: 'block',
                      py: 1.1,
                      px: 1.25,
                      minWidth: 0,
                      borderLeft: '3px solid',
                      borderColor: active ? (partial ? 'warning.main' : 'primary.main') : 'transparent',
                      '&.Mui-selected': {
                        bgcolor: dark ? 'rgba(56,189,248,0.07)' : 'rgba(25,118,210,0.05)',
                      },
                    }}
                  >
                    <Typography
                      variant="body2"
                      title={run.goal}
                      sx={{
                        fontWeight: active ? 700 : 600,
                        lineHeight: 1.35,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        color: 'text.primary',
                      }}
                    >
                      {run.goal}
                    </Typography>
                    <Stack
                      direction="row"
                      spacing={0.75}
                      alignItems="center"
                      sx={{ mt: 0.45, minWidth: 0 }}
                    >
                      <Box
                        sx={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          flexShrink: 0,
                          bgcolor: partial ? 'warning.main' : 'success.main',
                        }}
                      />
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {partial ? 'Partial' : 'Complete'} · {run.steps || 0} steps · {formatWhen(run.at)}
                      </Typography>
                    </Stack>
                  </ListItemButton>
                )
              })}
            </List>
          </Box>

          {/* Reader */}
          <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: 0, minWidth: 0 }}>
            <Box
              sx={{
                px: 1.75,
                py: 1.1,
                borderBottom: '1px solid',
                borderColor: 'divider',
                flexShrink: 0,
                minWidth: 0,
              }}
            >
              <Stack
                direction="row"
                spacing={1}
                alignItems="flex-start"
                justifyContent="space-between"
                sx={{ minWidth: 0 }}
              >
                <Box sx={{ minWidth: 0, flex: 1, pr: 1 }}>
                  <Typography
                    variant="subtitle2"
                    title={selected.goal}
                    sx={{
                      fontWeight: 750,
                      letterSpacing: '-0.01em',
                      lineHeight: 1.35,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {selected.goal}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 0.35, display: 'block', fontVariantNumeric: 'tabular-nums' }}
                  >
                    {isPartial(selected.answer) ? 'Partial' : 'Complete'}
                    {' · '}
                    {selected.steps || 0} steps
                    {' · '}
                    {formatWhen(selected.at)}
                  </Typography>
                </Box>

                <Stack direction="row" spacing={0.5} flexShrink={0} alignItems="center">
                  {onReuseGoal && (
                    <Tooltip title="Reuse objective">
                      {narrow ? (
                        <IconButton size="small" onClick={() => onReuseGoal(selected.goal)}>
                          <ReuseIcon fontSize="small" />
                        </IconButton>
                      ) : (
                        <Button
                          size="small"
                          startIcon={<ReuseIcon />}
                          onClick={() => onReuseGoal(selected.goal)}
                          sx={{ textTransform: 'none', fontWeight: 650, borderRadius: 1.5 }}
                        >
                          Reuse
                        </Button>
                      )}
                    </Tooltip>
                  )}
                  <Tooltip title={copied ? 'Copied' : 'Copy brief'}>
                    {narrow ? (
                      <IconButton size="small" onClick={handleCopy}>
                        <CopyIcon fontSize="small" />
                      </IconButton>
                    ) : (
                      <Button
                        size="small"
                        startIcon={<CopyIcon />}
                        onClick={handleCopy}
                        sx={{ textTransform: 'none', fontWeight: 650, borderRadius: 1.5 }}
                      >
                        {copied ? 'Copied' : 'Copy'}
                      </Button>
                    )}
                  </Tooltip>
                  {onAskFollowUp && (
                    <Tooltip title={AGENT_HELP.askFollowUp}>
                      {narrow ? (
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => onAskFollowUp(selected)}
                        >
                          <ChatIcon fontSize="small" />
                        </IconButton>
                      ) : (
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<ChatIcon />}
                          onClick={() => onAskFollowUp(selected)}
                          sx={{ textTransform: 'none', fontWeight: 700, borderRadius: 1.5, whiteSpace: 'nowrap' }}
                        >
                          Follow-up
                        </Button>
                      )}
                    </Tooltip>
                  )}
                </Stack>
              </Stack>
            </Box>

            <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', px: 1.75, py: 1.5 }}>
              <AnimatePresence mode="wait">
                <Box
                  key={selected.id}
                  component={motion.div}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.7,
                      color: 'text.primary',
                      wordBreak: 'break-word',
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {selected.answer}
                  </Typography>
                </Box>
              </AnimatePresence>
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  )
}

export default BriefBoard
