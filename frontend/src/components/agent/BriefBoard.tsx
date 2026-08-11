import React, { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Chip,
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
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import HelpTip from '../HelpTip'
import { AGENT_HELP } from './agentHelp'
import { extractDocumentIds, formatBriefAnswer } from './briefAnswer'

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

function shortId(id: string) {
  return id.slice(0, 8)
}

const markdownSx = {
  color: 'text.primary',
  fontSize: '0.875rem',
  lineHeight: 1.7,
  wordBreak: 'break-word',
  overflowWrap: 'anywhere',
  '& > :first-of-type': { mt: 0 },
  '& > :last-child': { mb: 0 },
  '& p': { my: 1 },
  '& strong': { fontWeight: 750, color: 'text.primary' },
  '& h1, & h2, & h3, & h4': {
    fontWeight: 750,
    letterSpacing: '-0.01em',
    lineHeight: 1.3,
    mt: 1.75,
    mb: 0.75,
  },
  '& h1': { fontSize: '1.1rem' },
  '& h2': { fontSize: '1rem' },
  '& h3': { fontSize: '0.95rem' },
  '& ul, & ol': {
    my: 1,
    pl: 2.5,
    '& li': { mb: 0.85 },
    '& li::marker': { color: 'primary.main', fontWeight: 700 },
  },
  '& li > p': { my: 0.35 },
  '& blockquote': {
    m: 0,
    my: 1.25,
    pl: 1.5,
    borderLeft: '3px solid',
    borderColor: 'divider',
    color: 'text.secondary',
  },
  '& table': { width: '100%', borderCollapse: 'collapse', my: 1.25, display: 'block', overflowX: 'auto' },
  '& th, & td': { border: '1px solid', borderColor: 'divider', p: 1, verticalAlign: 'top' },
  '& th': { fontWeight: 700, bgcolor: 'action.hover' },
  '& pre': {
    p: 1.25,
    overflowX: 'auto',
    bgcolor: 'background.default',
    borderRadius: 1,
    border: '1px solid',
    borderColor: 'divider',
  },
  '& code': {
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    fontSize: '0.78em',
    px: 0.45,
    py: 0.1,
    borderRadius: 0.75,
    bgcolor: (t: { palette: { mode: string } }) =>
      t.palette.mode === 'dark' ? 'rgba(148,163,184,0.12)' : 'rgba(15,23,42,0.06)',
  },
  '& pre code': { px: 0, py: 0, bgcolor: 'transparent' },
  '& hr': { border: 0, borderTop: '1px solid', borderColor: 'divider', my: 1.5 },
} as const

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

  const formattedAnswer = useMemo(
    () => (selected ? formatBriefAnswer(selected.answer) : ''),
    [selected]
  )

  const sourceIds = useMemo(
    () => (selected ? extractDocumentIds(selected.answer) : []),
    [selected]
  )

  const handleCopy = async () => {
    if (!selected) return
    try {
      await navigator.clipboard.writeText(
        `Objective: ${selected.goal}\n\n${formatBriefAnswer(selected.answer)}`
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
            gridTemplateRows: { xs: 'minmax(120px, 28%) minmax(0, 1fr)', sm: 'minmax(0, 1fr)' },
          }}
        >
          {/* Navigator — goal + meta only */}
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

          {/* Reader / response card */}
          <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: 0, minWidth: 0 }}>
            <Box
              sx={{
                px: { xs: 1.5, sm: 2 },
                py: 1.25,
                borderBottom: '1px solid',
                borderColor: 'divider',
                flexShrink: 0,
                minWidth: 0,
                bgcolor: dark ? 'rgba(255,255,255,0.015)' : 'rgba(0,0,0,0.015)',
              }}
            >
              <Stack spacing={1} sx={{ minWidth: 0 }}>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  spacing={1}
                  alignItems={{ xs: 'stretch', sm: 'flex-start' }}
                  justifyContent="space-between"
                  sx={{ minWidth: 0 }}
                >
                  <Box sx={{ minWidth: 0, flex: 1 }}>
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

                  <Stack
                    direction="row"
                    spacing={0.5}
                    flexShrink={0}
                    alignItems="center"
                    justifyContent={{ xs: 'flex-end', sm: 'flex-start' }}
                    flexWrap="wrap"
                    useFlexGap
                  >
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
              </Stack>
            </Box>

            <Box
              sx={{
                flex: 1,
                minHeight: 0,
                overflow: 'auto',
                px: { xs: 1.25, sm: 1.75 },
                py: 1.5,
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <AnimatePresence mode="wait">
                <Box
                  key={selected.id}
                  component={motion.div}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                  sx={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    minHeight: 0,
                    gap: 1.25,
                  }}
                >
                  <Paper
                    elevation={0}
                    sx={{
                      flex: 1,
                      minHeight: 0,
                      p: { xs: 1.5, sm: 2 },
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: dark ? 'rgba(148,163,184,0.14)' : 'divider',
                      bgcolor: dark ? 'rgba(255,255,255,0.025)' : 'rgba(248,250,252,0.85)',
                      overflow: 'auto',
                    }}
                  >
                    <Box sx={markdownSx}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {formattedAnswer}
                      </ReactMarkdown>
                    </Box>
                  </Paper>

                  {sourceIds.length > 0 && (
                    <Box sx={{ flexShrink: 0 }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 700, letterSpacing: 0.4, textTransform: 'uppercase', mb: 0.75, display: 'block' }}
                      >
                        Sources · {sourceIds.length}
                      </Typography>
                      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                        {sourceIds.map((id) => (
                          <Chip
                            key={id}
                            size="small"
                            variant="outlined"
                            label={shortId(id)}
                            title={id}
                            sx={{
                              height: 24,
                              borderRadius: 1.25,
                              fontFamily:
                                'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                              fontSize: '0.7rem',
                              fontWeight: 650,
                            }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
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
