import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Chip,
  Checkbox,
  Avatar,
  Button,
  TextField,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Drawer,
  IconButton,
  Divider,
  Tooltip,
  Stack,
  useTheme,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
} from '@mui/material'
import { DocumentChat } from '../components/DocumentChat'
import ChatHistory from '../components/ChatHistory'
import DocumentDetailsDrawer from '../components/DocumentDetailsDrawer'
import AgentModePanel, { AgentRunRecord } from '../components/agent/AgentModePanel'
import { AGENT_HELP } from '../components/agent/agentHelp'
import HelpTip from '../components/HelpTip'
import { useGetDocumentsQuery } from '../store/api'
import { format } from 'date-fns'
import {
  Chat as ChatIcon,
  History as HistoryIcon,
  Close as CloseIcon,
  Tune as TuneIcon,
  DoneAll as DoneAllIcon,
  LibraryBooks as LibraryIcon,
} from '@mui/icons-material'
import FileTypeIcon, { getFileColor } from '../components/FileTypeIcon'
import { Search as SearchIcon } from '@mui/icons-material'
import { useDebounce } from '../hooks/useDebounce'
import { AnimatePresence, motion } from 'framer-motion'
import { useSnackbar } from 'notistack'

const glass = (dark: boolean) =>
  dark
    ? {
        background: 'linear-gradient(180deg, rgba(22,28,38,0.92) 0%, rgba(12,16,22,0.88) 100%)',
        border: '1px solid rgba(255,255,255,0.08)',
        boxShadow: '0 18px 50px rgba(0,0,0,0.35)',
        backdropFilter: 'blur(18px)',
      }
    : {
        background: 'linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(247,249,252,0.88) 100%)',
        border: '1px solid rgba(15,23,42,0.08)',
        boxShadow: '0 18px 40px rgba(15,23,42,0.08)',
        backdropFilter: 'blur(18px)',
      }

/**
 * Insight Bridge — research-first shell.
 * Corpus is a calm summary strip; document picking lives in Refine (dialog),
 * not a permanent checkbox wall.
 */
const ChatPage: React.FC = () => {
  const theme = useTheme()
  const dark = theme.palette.mode === 'dark'
  const { enqueueSnackbar } = useSnackbar()
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | undefined>()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [followUpOpen, setFollowUpOpen] = useState(false)
  const [followUpBrief, setFollowUpBrief] = useState<AgentRunRecord | null>(null)
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false)
  const [selectedDocumentForDetails, setSelectedDocumentForDetails] = useState<any>(null)
  const [refineOpen, setRefineOpen] = useState(false)
  const [draftSelection, setDraftSelection] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [fileType, setFileType] = useState<'all' | string>('all')
  const [sortBy, setSortBy] = useState<'created_at' | 'filename' | 'file_type' | 'file_size' | 'updated_at'>(
    'created_at'
  )
  const [sortOrder] = useState<'asc' | 'desc'>('desc')
  const autoSelectedRef = useRef(false)

  const debouncedSearch = useDebounce(search, 500)

  const { data, isLoading } = useGetDocumentsQuery({
    skip: 0,
    limit: 100,
    search: debouncedSearch || undefined,
    file_type: fileType,
    sort_by: sortBy,
    sort_order: sortOrder,
    status: 'indexed',
  })

  const availableDocuments = useMemo(
    () => (data?.documents || []).filter((d: any) => d.status === 'indexed'),
    [data]
  )

  const allIndexedIds = useMemo(
    () => availableDocuments.map((d: any) => d.uuid as string),
    [availableDocuments]
  )

  useEffect(() => {
    if (!autoSelectedRef.current && availableDocuments.length > 0 && selectedDocuments.length === 0) {
      setSelectedDocuments(availableDocuments.map((doc: any) => doc.uuid))
      autoSelectedRef.current = true
    }
  }, [availableDocuments, selectedDocuments.length])

  const usingAllIndexed =
    availableDocuments.length > 0 &&
    selectedDocuments.length >= availableDocuments.length &&
    availableDocuments.every((d: any) => selectedDocuments.includes(d.uuid))

  const selectedPreviews = useMemo(() => {
    const byId = new Map(availableDocuments.map((d: any) => [d.uuid, d]))
    return selectedDocuments
      .map((id) => byId.get(id))
      .filter(Boolean)
      .slice(0, 4) as any[]
  }, [availableDocuments, selectedDocuments])

  const openRefine = () => {
    setDraftSelection(selectedDocuments)
    setRefineOpen(true)
  }

  const applyRefine = () => {
    setSelectedDocuments(draftSelection)
    setRefineOpen(false)
    enqueueSnackbar(
      draftSelection.length === availableDocuments.length
        ? 'Scope: all indexed documents'
        : `Scope: ${draftSelection.length} document${draftSelection.length === 1 ? '' : 's'}`,
      { variant: 'info' }
    )
  }

  const useAllIndexed = () => {
    setSelectedDocuments(allIndexedIds)
  }

  const selectAllIndexedInDraft = () => {
    setDraftSelection(allIndexedIds)
  }

  const toggleDraft = (docId: string) => {
    setDraftSelection((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    )
  }

  const toggleDraftShown = () => {
    const visibleIds = availableDocuments.map((d: any) => d.uuid as string)
    const allShown = visibleIds.length > 0 && visibleIds.every((id) => draftSelection.includes(id))
    if (allShown) {
      const visible = new Set(visibleIds)
      setDraftSelection((prev) => prev.filter((id) => !visible.has(id)))
    } else {
      setDraftSelection((prev) => Array.from(new Set([...prev, ...visibleIds])))
    }
  }

  const openFollowUp = (run: AgentRunRecord) => {
    setFollowUpBrief(run)
    setSelectedConversationId(undefined)
    setFollowUpOpen(true)
    setHistoryOpen(false)
  }

  const draftShownSelected = availableDocuments.filter((d: any) => draftSelection.includes(d.uuid)).length
  const scopeProgress =
    availableDocuments.length > 0
      ? Math.round((selectedDocuments.length / Math.max(availableDocuments.length, 1)) * 100)
      : 0

  return (
    <Box
      sx={{
        height: 'calc(100vh - 64px)',
        display: 'flex',
        flexDirection: 'column',
        mx: { xs: -2, md: -3 },
        mt: { xs: -2, md: -3 },
        px: { xs: 2, md: 3 },
        pt: { xs: 2, md: 2.5 },
        pb: 2,
        position: 'relative',
        overflow: 'hidden',
        gap: 1.5,
      }}
    >
      <Box
        aria-hidden
        sx={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background: dark
            ? 'radial-gradient(900px 480px at 20% -5%, rgba(56,189,248,0.14), transparent 55%), radial-gradient(700px 400px at 90% 0%, rgba(99,102,241,0.12), transparent 50%)'
            : 'radial-gradient(900px 480px at 20% -5%, rgba(14,165,233,0.1), transparent 55%), radial-gradient(700px 400px at 90% 0%, rgba(99,102,241,0.08), transparent 50%)',
        }}
      />

      {/* Masthead */}
      <Box
        sx={{
          position: 'relative',
          zIndex: 1,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 1.5,
        }}
      >
        <Box>
          <Typography
            sx={{
              fontWeight: 750,
              letterSpacing: '-0.045em',
              fontSize: { xs: '1.7rem', md: '2.1rem' },
              lineHeight: 1.05,
              background: dark
                ? 'linear-gradient(120deg, #f8fafc 0%, #93c5fd 45%, #67e8f9 100%)'
                : 'linear-gradient(120deg, #0f172a 0%, #1d4ed8 50%, #0891b2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            <HelpTip title={AGENT_HELP.pageTitle} underline={false}>
              {AGENT_HELP.productName}
            </HelpTip>
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.6, maxWidth: 560 }}>
            {AGENT_HELP.pageSubtitle}
          </Typography>
        </Box>
        <Tooltip title={AGENT_HELP.followUpHistory}>
          <Button
            variant="outlined"
            startIcon={<HistoryIcon />}
            onClick={() => setHistoryOpen(true)}
            sx={{ borderRadius: 999, textTransform: 'none', fontWeight: 650 }}
          >
            Follow-ups
          </Button>
        </Tooltip>
      </Box>

      {/* Calm corpus strip — not a document wall */}
      <Paper
        component={motion.div}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        sx={{
          position: 'relative',
          zIndex: 1,
          px: 2,
          py: 1.5,
          borderRadius: 2.5,
          ...glass(dark),
        }}
      >
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={1.75}
          alignItems={{ md: 'center' }}
          justifyContent="space-between"
        >
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ minWidth: 0, flex: 1 }}>
            <Box
              sx={{
                width: 44,
                height: 44,
                borderRadius: 2,
                display: 'grid',
                placeItems: 'center',
                background: dark
                  ? 'linear-gradient(145deg, rgba(56,189,248,0.2), rgba(99,102,241,0.15))'
                  : 'linear-gradient(145deg, rgba(14,165,233,0.15), rgba(99,102,241,0.12))',
                color: 'primary.main',
                flexShrink: 0,
              }}
            >
              <LibraryIcon />
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 750, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
                <HelpTip title={AGENT_HELP.scope}>
                  {usingAllIndexed ? 'Entire indexed corpus' : 'Custom corpus'}
                </HelpTip>
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.15 }}>
                {isLoading
                  ? 'Loading indexed documents…'
                  : usingAllIndexed
                    ? `${selectedDocuments.length} documents ready for research`
                    : `${selectedDocuments.length} of ${availableDocuments.length || '—'} indexed documents selected`}
              </Typography>
              {!usingAllIndexed && selectedPreviews.length > 0 && (
                <Stack direction="row" spacing={0.75} sx={{ mt: 0.85, flexWrap: 'wrap' }} useFlexGap>
                  {selectedPreviews.map((doc: any) => (
                    <Chip
                      key={doc.uuid}
                      size="small"
                      avatar={
                        <Avatar sx={{ bgcolor: getFileColor(doc.file_type), width: 18, height: 18 }}>
                          <FileTypeIcon fileType={doc.file_type} iconProps={{ sx: { fontSize: 11 } }} />
                        </Avatar>
                      }
                      label={doc.title || doc.filename}
                      onClick={() => {
                        setSelectedDocumentForDetails(doc)
                        setDetailsDrawerOpen(true)
                      }}
                      sx={{
                        maxWidth: 180,
                        height: 26,
                        borderRadius: 1,
                        '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' },
                      }}
                    />
                  ))}
                  {selectedDocuments.length > selectedPreviews.length && (
                    <Chip
                      size="small"
                      label={`+${selectedDocuments.length - selectedPreviews.length} more`}
                      sx={{ height: 26, borderRadius: 1, fontWeight: 650 }}
                      onClick={openRefine}
                    />
                  )}
                </Stack>
              )}
            </Box>
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Box sx={{ width: { xs: '100%', sm: 120 }, mr: { sm: 0.5 } }}>
              <Typography
                variant="caption"
                sx={{ color: 'text.disabled', fontWeight: 650, letterSpacing: 0.6, display: 'block', mb: 0.35 }}
              >
                COVERAGE
              </Typography>
              <LinearProgress
                variant="determinate"
                value={scopeProgress}
                sx={{
                  height: 4,
                  borderRadius: 2,
                  bgcolor: dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 2,
                    background: usingAllIndexed
                      ? 'linear-gradient(90deg, #22c55e, #06b6d4)'
                      : 'linear-gradient(90deg, #3b82f6, #06b6d4)',
                  },
                }}
              />
            </Box>
            <Chip
              size="small"
              color={selectedDocuments.length > 0 ? 'success' : 'default'}
              label={`${selectedDocuments.length} in run`}
              sx={{ fontWeight: 750, borderRadius: 1 }}
            />
            {!usingAllIndexed && (
              <Button
                size="small"
                startIcon={<DoneAllIcon />}
                onClick={useAllIndexed}
                sx={{ borderRadius: 999, textTransform: 'none', fontWeight: 650 }}
              >
                Use all
              </Button>
            )}
            <Button
              size="small"
              variant="contained"
              startIcon={<TuneIcon />}
              onClick={openRefine}
              sx={{
                borderRadius: 999,
                textTransform: 'none',
                fontWeight: 700,
                boxShadow: '0 8px 22px rgba(25,118,210,0.28)',
              }}
            >
              Refine scope
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Research stage — full width */}
      <Box sx={{ position: 'relative', zIndex: 1, flex: 1, minHeight: 0 }}>
        <AgentModePanel
          documentIds={selectedDocuments}
          onFinalAnswer={(_goal, _answer, run) => {
            enqueueSnackbar('Brief complete — Ask follow-up from the Brief Board', { variant: 'success' })
            setFollowUpBrief(run)
          }}
          onAskFollowUp={openFollowUp}
        />
      </Box>

      {/* Refine dialog — pleasant picker, not a permanent sidebar */}
      <Dialog
        open={refineOpen}
        onClose={() => setRefineOpen(false)}
        fullWidth
        maxWidth="md"
        PaperProps={{
          sx: {
            borderRadius: 3,
            overflow: 'hidden',
            ...glass(dark),
            maxHeight: '82vh',
          },
        }}
      >
        <DialogTitle sx={{ pb: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 750, letterSpacing: '-0.02em' }}>
                Refine corpus
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Choose what the research agent can use. Defaults to everything indexed.
              </Typography>
            </Box>
            <IconButton onClick={() => setRefineOpen(false)} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent dividers sx={{ px: 2.5, py: 2 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }}>
            <TextField
              size="small"
              fullWidth
              placeholder="Search titles…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            <FormControl size="small" sx={{ minWidth: 110 }}>
              <InputLabel>Type</InputLabel>
              <Select label="Type" value={fileType} onChange={(e) => setFileType(e.target.value as any)}>
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="pdf">PDF</MenuItem>
                <MenuItem value="txt">TXT</MenuItem>
                <MenuItem value="docx">DOCX</MenuItem>
                <MenuItem value="pptx">PPTX</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Sort</InputLabel>
              <Select label="Sort" value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
                <MenuItem value="created_at">Created</MenuItem>
                <MenuItem value="updated_at">Updated</MenuItem>
                <MenuItem value="filename">Filename</MenuItem>
                <MenuItem value="file_type">Type</MenuItem>
                <MenuItem value="file_size">Size</MenuItem>
              </Select>
            </FormControl>
            <Button size="small" onClick={toggleDraftShown} sx={{ textTransform: 'none', whiteSpace: 'nowrap' }}>
              {draftShownSelected === availableDocuments.length && availableDocuments.length > 0
                ? 'Clear shown'
                : 'Select shown'}
            </Button>
          </Stack>

          <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} alignItems="center">
            <Chip size="small" label={`${draftSelection.length} selected`} color="primary" sx={{ fontWeight: 700 }} />
            <Chip size="small" label={`${availableDocuments.length} shown`} sx={{ fontWeight: 600 }} />
            <Box sx={{ flex: 1 }} />
            <Button
              size="small"
              startIcon={<DoneAllIcon />}
              onClick={selectAllIndexedInDraft}
              sx={{ textTransform: 'none' }}
            >
              Select all indexed
            </Button>
          </Stack>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
              gap: 1,
              maxHeight: '48vh',
              overflow: 'auto',
              pr: 0.5,
            }}
          >
            <AnimatePresence initial={false}>
              {isLoading ? (
                <Typography color="text.secondary">Loading…</Typography>
              ) : availableDocuments.length === 0 ? (
                <Typography color="text.secondary">No indexed documents match.</Typography>
              ) : (
                availableDocuments.map((doc: any) => {
                  const checked = draftSelection.includes(doc.uuid)
                  return (
                    <Box
                      key={doc.uuid}
                      component={motion.div}
                      layout
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => toggleDraft(doc.uuid)}
                      sx={{
                        display: 'flex',
                        gap: 1.25,
                        alignItems: 'flex-start',
                        p: 1.25,
                        borderRadius: 2,
                        cursor: 'pointer',
                        border: '1px solid',
                        borderColor: checked ? 'primary.main' : 'divider',
                        bgcolor: checked
                          ? dark
                            ? 'rgba(25,118,210,0.14)'
                            : 'rgba(25,118,210,0.07)'
                          : dark
                            ? 'rgba(255,255,255,0.02)'
                            : 'rgba(255,255,255,0.55)',
                        transition: 'border-color 0.15s ease, background 0.15s ease',
                        '&:hover': {
                          borderColor: checked ? 'primary.main' : 'primary.light',
                          bgcolor: dark ? 'rgba(255,255,255,0.04)' : 'rgba(25,118,210,0.04)',
                        },
                      }}
                    >
                      <Checkbox
                        checked={checked}
                        size="small"
                        sx={{ p: 0.25, mt: 0.15 }}
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleDraft(doc.uuid)
                        }}
                      />
                      <Avatar
                        sx={{
                          width: 32,
                          height: 32,
                          mt: 0.15,
                          bgcolor: getFileColor(doc.file_type),
                          fontSize: 12,
                        }}
                      >
                        <FileTypeIcon fileType={doc.file_type} iconProps={{ sx: { fontSize: 16 } }} />
                      </Avatar>
                      <Box sx={{ minWidth: 0, flex: 1 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 650,
                            lineHeight: 1.3,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {doc.title || doc.filename}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {(doc.file_type || 'file').toUpperCase()} ·{' '}
                          {format(new Date(doc.created_at), 'MMM d, yyyy')}
                        </Typography>
                        <Button
                          size="small"
                          sx={{ mt: 0.25, px: 0, minWidth: 0, textTransform: 'none', fontSize: 11 }}
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedDocumentForDetails(doc)
                            setDetailsDrawerOpen(true)
                          }}
                        >
                          Details
                        </Button>
                      </Box>
                    </Box>
                  )
                })
              )}
            </AnimatePresence>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 2.5, py: 1.5 }}>
          <Button onClick={() => setRefineOpen(false)} sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={applyRefine}
            disabled={draftSelection.length === 0}
            sx={{ borderRadius: 999, textTransform: 'none', fontWeight: 700, px: 2.5 }}
          >
            Apply scope ({draftSelection.length})
          </Button>
        </DialogActions>
      </Dialog>

      <Drawer
        anchor="right"
        open={followUpOpen}
        onClose={() => setFollowUpOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: { xs: '100%', sm: 520, md: 640 },
            p: 0,
            display: 'flex',
            flexDirection: 'column',
            ...glass(dark),
          },
        }}
      >
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
            <Box sx={{ minWidth: 0 }}>
              <Typography
                variant="subtitle1"
                sx={{ fontWeight: 750, display: 'flex', alignItems: 'center', gap: 0.75 }}
              >
                <ChatIcon fontSize="small" color="primary" />
                Ask follow-up
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {followUpBrief?.goal || 'Conversational Q&A over the same scoped corpus'}
              </Typography>
            </Box>
            <Stack direction="row" spacing={0.5}>
              <IconButton size="small" onClick={() => setHistoryOpen(true)}>
                <HistoryIcon fontSize="small" />
              </IconButton>
              <IconButton size="small" onClick={() => setFollowUpOpen(false)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Stack>
          {followUpBrief && (
            <Paper variant="outlined" sx={{ mt: 1.25, p: 1.25, borderRadius: 1.5, bgcolor: 'action.hover' }}>
              <Typography variant="caption" sx={{ fontWeight: 700, color: 'success.main', letterSpacing: 0.6 }}>
                BRIEF CONTEXT
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.35, whiteSpace: 'pre-wrap' }}>
                {followUpBrief.answer.slice(0, 420)}
                {followUpBrief.answer.length > 420 ? '…' : ''}
              </Typography>
            </Paper>
          )}
        </Box>
        <Box sx={{ flex: 1, minHeight: 0, p: 1.5 }}>
          <DocumentChat
            documentIds={selectedDocuments}
            conversationId={selectedConversationId}
            onNewConversation={(id) => setSelectedConversationId(id)}
            contextBanner={
              followUpBrief
                ? `Follow-up on Insight brief: “${followUpBrief.goal}”. Ground answers in the scoped documents.`
                : undefined
            }
            initialDraft={
              followUpBrief ? `Regarding the research brief on “${followUpBrief.goal}”: ` : undefined
            }
          />
        </Box>
      </Drawer>

      <Drawer
        anchor="right"
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        sx={{ '& .MuiDrawer-paper': { width: 400, p: 2, ...glass(dark) } }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Follow-up history
          </Typography>
          <IconButton onClick={() => setHistoryOpen(false)}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Divider sx={{ mb: 2 }} />
        <ChatHistory
          onConversationSelect={(id) => {
            setSelectedConversationId(id)
            setFollowUpOpen(true)
            setHistoryOpen(false)
          }}
          selectedConversationId={selectedConversationId}
        />
      </Drawer>

      <DocumentDetailsDrawer
        open={detailsDrawerOpen}
        document={selectedDocumentForDetails}
        onClose={() => {
          setDetailsDrawerOpen(false)
          setSelectedDocumentForDetails(null)
        }}
        onEdit={() => undefined}
        onDownload={(doc) => window.open(`/api/v1/files/${doc.uuid}/download`, '_blank')}
        onShare={() => undefined}
      />
    </Box>
  )
}

export default ChatPage
