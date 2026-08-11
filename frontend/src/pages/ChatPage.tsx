import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Box,
  Typography,
  Grid,
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
} from '@mui/material'
import { DocumentChat } from '../components/DocumentChat'
import ChatHistory from '../components/ChatHistory'
import DocumentDetailsDrawer from '../components/DocumentDetailsDrawer'
import AgentModePanel, { AgentRunRecord } from '../components/agent/AgentModePanel'
import { AGENT_HELP } from '../components/agent/agentHelp'
import HelpTip from '../components/HelpTip'
import { ArcMeter } from '../components/instruments'
import { useGetDocumentsQuery } from '../store/api'
import { format } from 'date-fns'
import {
  Chat as ChatIcon,
  History as HistoryIcon,
  Close as CloseIcon,
} from '@mui/icons-material'
import FileTypeIcon, { getFileColor } from '../components/FileTypeIcon'
import { Search as SearchIcon } from '@mui/icons-material'
import { useDebounce } from '../hooks/useDebounce'
import { motion } from 'framer-motion'
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
 * Insight Bridge — single research console.
 * Left: corpus scope. Right: agent. Chat is follow-up only (drawer).
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

  useEffect(() => {
    if (!autoSelectedRef.current && availableDocuments.length > 0 && selectedDocuments.length === 0) {
      setSelectedDocuments(availableDocuments.map((doc: any) => doc.uuid))
      autoSelectedRef.current = true
    }
  }, [availableDocuments, selectedDocuments.length])

  const handleDocumentToggle = (docId: string) => {
    setSelectedDocuments((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    )
  }

  const handleDocumentClick = (doc: any, e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.MuiCheckbox-root')) return
    setSelectedDocumentForDetails(doc)
    setDetailsDrawerOpen(true)
  }

  const handleSelectAll = () => {
    const visibleIds = availableDocuments.map((doc: any) => doc.uuid)
    const allShownSelected =
      visibleIds.length > 0 && visibleIds.every((id: string) => selectedDocuments.includes(id))
    if (allShownSelected) {
      const visible = new Set(visibleIds)
      setSelectedDocuments((prev) => prev.filter((id) => !visible.has(id)))
    } else {
      setSelectedDocuments((prev) => Array.from(new Set([...prev, ...visibleIds])))
    }
  }

  const openFollowUp = (run: AgentRunRecord) => {
    setFollowUpBrief(run)
    setSelectedConversationId(undefined)
    setFollowUpOpen(true)
    setHistoryOpen(false)
  }

  const selectedInView = availableDocuments.filter((d: any) => selectedDocuments.includes(d.uuid)).length
  const selectionPct =
    availableDocuments.length > 0 ? Math.min(100, (selectedInView / availableDocuments.length) * 100) : 0

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
      }}
    >
      <Box
        aria-hidden
        sx={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background: dark
            ? 'radial-gradient(800px 420px at 18% 0%, rgba(56,189,248,0.12), transparent 60%), radial-gradient(700px 380px at 88% 8%, rgba(99,102,241,0.14), transparent 55%)'
            : 'radial-gradient(800px 420px at 18% 0%, rgba(14,165,233,0.1), transparent 60%), radial-gradient(700px 380px at 88% 8%, rgba(99,102,241,0.08), transparent 55%)',
        }}
      />

      <Box
        sx={{
          position: 'relative',
          zIndex: 1,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          mb: 2,
          flexWrap: 'wrap',
          gap: 1.5,
        }}
      >
        <Box>
          <Typography
            sx={{
              fontWeight: 750,
              letterSpacing: '-0.04em',
              fontSize: { xs: '1.65rem', md: '2rem' },
              lineHeight: 1.1,
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
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 640 }}>
            {AGENT_HELP.pageSubtitle}
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} alignItems="center">
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
        </Stack>
      </Box>

      <Grid
        container
        spacing={2}
        sx={{ position: 'relative', zIndex: 1, flexGrow: 1, minHeight: 0, height: 'calc(100% - 72px)' }}
      >
        <Grid item xs={12} md={3} sx={{ height: '100%', minHeight: 0 }}>
          <Paper
            sx={{
              p: 2,
              borderRadius: 2.5,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              ...glass(dark),
            }}
          >
            <Box sx={{ mb: 1.25, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 750, letterSpacing: '-0.02em' }}>
                <HelpTip title={AGENT_HELP.scope}>Scope</HelpTip>
              </Typography>
              <Tooltip title={AGENT_HELP.scopeSelectAll}>
                <span>
                  <Button
                    size="small"
                    onClick={handleSelectAll}
                    disabled={availableDocuments.length === 0}
                    sx={{ textTransform: 'none', fontWeight: 650 }}
                  >
                    {selectedInView === availableDocuments.length && availableDocuments.length > 0
                      ? 'Clear shown'
                      : 'All shown'}
                  </Button>
                </span>
              </Tooltip>
            </Box>

            <Tooltip title={AGENT_HELP.scopeMeter} arrow>
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1, cursor: 'help' }}>
                <ArcMeter
                  value={selectionPct}
                  label="In list"
                  subtitle={`${selectedDocuments.length} selected · ${availableDocuments.length} shown`}
                  unit="%"
                  precision={0}
                  size={104}
                  status={selectedDocuments.length > 0 ? 'ok' : 'idle'}
                />
              </Box>
            </Tooltip>

            <Tooltip title={AGENT_HELP.scopeSearch}>
              <TextField
                size="small"
                fullWidth
                placeholder="Filter list…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                sx={{ mb: 1 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                }}
              />
            </Tooltip>

            <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Type</InputLabel>
                <Select label="Type" value={fileType} onChange={(e) => setFileType(e.target.value as any)}>
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="pdf">PDF</MenuItem>
                  <MenuItem value="txt">TXT</MenuItem>
                  <MenuItem value="docx">DOCX</MenuItem>
                  <MenuItem value="pptx">PPTX</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 110 }}>
                <InputLabel>Sort</InputLabel>
                <Select label="Sort" value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
                  <MenuItem value="created_at">Created</MenuItem>
                  <MenuItem value="updated_at">Updated</MenuItem>
                  <MenuItem value="filename">Filename</MenuItem>
                  <MenuItem value="file_type">Type</MenuItem>
                  <MenuItem value="file_size">Size</MenuItem>
                </Select>
              </FormControl>
              <Chip
                label={`${data?.total ?? availableDocuments.length} match`}
                size="small"
                sx={{ fontWeight: 650 }}
              />
              <Chip
                color={selectedDocuments.length > 0 ? 'success' : 'default'}
                label={`${selectedDocuments.length} in run`}
                size="small"
                sx={{ fontWeight: 700 }}
              />
            </Box>

            <Box sx={{ flexGrow: 1, overflow: 'auto', pr: 0.5, minHeight: 0 }}>
              {isLoading ? (
                <Typography color="text.secondary">Loading…</Typography>
              ) : availableDocuments.length === 0 ? (
                <Typography color="text.secondary">No indexed documents.</Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  {availableDocuments.map((doc: any) => {
                    const isSelected = selectedDocuments.includes(doc.uuid)
                    return (
                      <Box
                        key={doc.uuid}
                        component={motion.div}
                        layout
                        onClick={(e: React.MouseEvent) => handleDocumentClick(doc, e)}
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          px: 1,
                          py: 0.7,
                          borderRadius: 1.25,
                          cursor: 'pointer',
                          border: '1px solid',
                          borderColor: isSelected ? 'primary.main' : 'transparent',
                          bgcolor: isSelected
                            ? dark
                              ? 'rgba(25,118,210,0.14)'
                              : 'rgba(25,118,210,0.08)'
                            : 'transparent',
                          '&:hover': { bgcolor: 'action.hover' },
                        }}
                      >
                        <Checkbox
                          checked={isSelected}
                          size="small"
                          sx={{ p: 0.25 }}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDocumentToggle(doc.uuid)
                          }}
                        />
                        <Avatar
                          sx={{ width: 22, height: 22, bgcolor: getFileColor(doc.file_type), fontSize: 10 }}
                        >
                          <FileTypeIcon fileType={doc.file_type} iconProps={{ sx: { fontSize: 14 } }} />
                        </Avatar>
                        <Typography
                          variant="body2"
                          sx={{
                            flex: 1,
                            minWidth: 0,
                            fontWeight: 500,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {doc.title || doc.filename}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.disabled"
                          sx={{ fontVariantNumeric: 'tabular-nums' }}
                        >
                          {format(new Date(doc.created_at), 'MMM dd')}
                        </Typography>
                      </Box>
                    )
                  })}
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={9} sx={{ height: '100%', minHeight: 0 }}>
          <AgentModePanel
            documentIds={selectedDocuments}
            onFinalAnswer={(_goal, _answer, run) => {
              enqueueSnackbar('Brief complete — Ask follow-up from the Brief Board', { variant: 'success' })
              // Keep latest brief handy for one-click follow-up
              setFollowUpBrief(run)
            }}
            onAskFollowUp={openFollowUp}
          />
        </Grid>
      </Grid>

      {/* Follow-up Q&A — folded Chat, not a peer mode */}
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
              <Typography variant="subtitle1" sx={{ fontWeight: 750, display: 'flex', alignItems: 'center', gap: 0.75 }}>
                <ChatIcon fontSize="small" color="primary" />
                Ask follow-up
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {followUpBrief?.goal || 'Conversational Q&A over the same scoped corpus'}
              </Typography>
            </Box>
            <Stack direction="row" spacing={0.5}>
              <Tooltip title="Follow-up history">
                <IconButton
                  size="small"
                  onClick={() => {
                    setHistoryOpen(true)
                  }}
                >
                  <HistoryIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <IconButton size="small" onClick={() => setFollowUpOpen(false)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Stack>
          {followUpBrief && (
            <Paper
              variant="outlined"
              sx={{ mt: 1.25, p: 1.25, borderRadius: 1.5, bgcolor: 'action.hover' }}
            >
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
              followUpBrief
                ? `Regarding the research brief on “${followUpBrief.goal}”: `
                : undefined
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
