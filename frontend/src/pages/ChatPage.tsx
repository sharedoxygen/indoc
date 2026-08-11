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
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Collapse,
  Stack,
} from '@mui/material'
import { DocumentChat } from '../components/DocumentChat'
import ChatHistory from '../components/ChatHistory'
import DocumentDetailsDrawer from '../components/DocumentDetailsDrawer'
import AgentModePanel from '../components/agent/AgentModePanel'
import { AGENT_HELP } from '../components/agent/agentHelp'
import HelpTip from '../components/HelpTip'
import { useGetDocumentsQuery } from '../store/api'
import { format } from 'date-fns'
import {
  Chat as ChatIcon,
  History as HistoryIcon,
  Close as CloseIcon,
  AutoAwesome as InsightIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  FolderSpecial as CorpusIcon,
} from '@mui/icons-material'
import FileTypeIcon, { getFileColor } from '../components/FileTypeIcon'
import { Search as SearchIcon } from '@mui/icons-material'
import { useDebounce } from '../hooks/useDebounce'
import { motion } from 'framer-motion'
import { useSnackbar } from 'notistack'

type InteractionMode = 'chat' | 'agent'

const MODE_KEY = 'indoc.chat.mode'

const ChatPage: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar()
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | undefined>()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false)
  const [selectedDocumentForDetails, setSelectedDocumentForDetails] = useState<any>(null)
  const [search, setSearch] = useState('')
  const [fileType, setFileType] = useState<'all' | string>('all')
  const [sortBy, setSortBy] = useState<'created_at' | 'filename' | 'file_type' | 'file_size' | 'updated_at'>('created_at')
  const [sortOrder] = useState<'asc' | 'desc'>('desc')
  const [lastAgentAnswer, setLastAgentAnswer] = useState<{ goal: string; answer: string } | null>(null)
  const [refineOpen, setRefineOpen] = useState(false)
  const [mode, setMode] = useState<InteractionMode>(() => {
    const saved = localStorage.getItem(MODE_KEY)
    return saved === 'chat' || saved === 'agent' ? saved : 'agent'
  })
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

  useEffect(() => {
    localStorage.setItem(MODE_KEY, mode)
  }, [mode])

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

  const useAllIndexed = () => {
    setSelectedDocuments(availableDocuments.map((d: any) => d.uuid))
    setRefineOpen(false)
  }

  const selectedInView = availableDocuments.filter((d: any) => selectedDocuments.includes(d.uuid)).length
  const allIndexedSelected =
    availableDocuments.length > 0 && selectedDocuments.length >= availableDocuments.length

  const docList = (
    <Box sx={{ flexGrow: 1, overflow: 'auto', pr: 0.5, minHeight: 0 }}>
      {isLoading ? (
        <Typography color="text.secondary">Loading…</Typography>
      ) : availableDocuments.length === 0 ? (
        <Typography color="text.secondary">No indexed documents.</Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
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
                  py: 0.75,
                  borderRadius: 1.5,
                  cursor: 'pointer',
                  bgcolor: isSelected ? 'action.selected' : 'transparent',
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
                <Avatar sx={{ width: 22, height: 22, bgcolor: getFileColor(doc.file_type), fontSize: 10 }}>
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
                <Typography variant="caption" color="text.disabled">
                  {format(new Date(doc.created_at), 'MMM dd')}
                </Typography>
              </Box>
            )
          })}
        </Box>
      )}
    </Box>
  )

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            {mode === 'agent' ? (
              <HelpTip title={AGENT_HELP.pageTitle} underline={false}>
                {AGENT_HELP.productName}
              </HelpTip>
            ) : (
              'Document Chat'
            )}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {mode === 'agent' ? AGENT_HELP.pageSubtitle : 'Conversational Q&A over indexed documents'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={mode}
            onChange={(_, v) => v && setMode(v)}
            sx={{ bgcolor: 'background.paper' }}
          >
            <Tooltip title={AGENT_HELP.modeAgent}>
              <ToggleButton value="agent">
                <InsightIcon sx={{ mr: 0.75, fontSize: 18 }} /> Insight
              </ToggleButton>
            </Tooltip>
            <Tooltip title={AGENT_HELP.modeChat}>
              <ToggleButton value="chat">
                <ChatIcon sx={{ mr: 0.75, fontSize: 18 }} /> Chat
              </ToggleButton>
            </Tooltip>
          </ToggleButtonGroup>
          {mode === 'chat' && (
            <Button
              variant="contained"
              startIcon={<ChatIcon />}
              onClick={() => setSelectedConversationId(undefined)}
            >
              New Chat
            </Button>
          )}
          <Tooltip title={AGENT_HELP.history}>
            <Button variant="outlined" startIcon={<HistoryIcon />} onClick={() => setHistoryOpen(true)}>
              History
            </Button>
          </Tooltip>
        </Box>
      </Box>

      {mode === 'agent' ? (
        <Box sx={{ flexGrow: 1, minHeight: 0, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {/* Compact corpus bar — replaces the busy checkbox wall */}
          <Paper sx={{ px: 2, py: 1.25, borderRadius: 3 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ flex: 1, minWidth: 0 }}>
                <CorpusIcon color="primary" fontSize="small" />
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    <HelpTip title={AGENT_HELP.scope}>Corpus scope</HelpTip>
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {allIndexedSelected
                      ? `All indexed documents · ${selectedDocuments.length}`
                      : `${selectedDocuments.length} of ${availableDocuments.length || '—'} indexed selected`}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  color={selectedDocuments.length > 0 ? 'success' : 'default'}
                  label={`${selectedDocuments.length} in run`}
                  sx={{ fontWeight: 700 }}
                />
              </Stack>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Button size="small" variant={allIndexedSelected ? 'contained' : 'outlined'} onClick={useAllIndexed}>
                  Use all indexed
                </Button>
                <Button
                  size="small"
                  variant={refineOpen ? 'contained' : 'outlined'}
                  color="inherit"
                  endIcon={refineOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  onClick={() => setRefineOpen((v) => !v)}
                >
                  Refine
                </Button>
              </Stack>
            </Stack>

            <Collapse in={refineOpen}>
              <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="Find documents…"
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
                  <Button size="small" onClick={handleSelectAll} disabled={availableDocuments.length === 0}>
                    {selectedInView === availableDocuments.length && availableDocuments.length > 0
                      ? 'Clear shown'
                      : 'All shown'}
                  </Button>
                </Stack>
                <Box sx={{ maxHeight: 220, overflow: 'auto' }}>{docList}</Box>
              </Box>
            </Collapse>
          </Paper>

          <Box sx={{ flex: 1, minHeight: 0 }}>
            <AgentModePanel
              documentIds={selectedDocuments}
              onFinalAnswer={(goal, answer) => {
                setLastAgentAnswer({ goal, answer })
                enqueueSnackbar('Brief complete — saved on the Brief Board', { variant: 'success' })
              }}
            />
          </Box>
        </Box>
      ) : (
        <Grid container spacing={2} sx={{ flexGrow: 1, height: 'calc(100% - 72px)', minHeight: 0 }}>
          <Grid item xs={12} md={4} sx={{ height: '100%', minHeight: 0 }}>
            <Paper sx={{ p: 2, borderRadius: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ mb: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
                  Documents
                </Typography>
                <Button size="small" onClick={handleSelectAll} disabled={availableDocuments.length === 0}>
                  {selectedInView === availableDocuments.length && availableDocuments.length > 0
                    ? 'Clear shown'
                    : 'All shown'}
                </Button>
              </Box>
              <TextField
                size="small"
                fullWidth
                placeholder="Search…"
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
                <Chip label={`${selectedDocuments.length} selected`} size="small" />
              </Box>
              {docList}
            </Paper>
          </Grid>

          <Grid item xs={12} md={8} sx={{ height: '100%', minHeight: 0, display: 'flex' }}>
            <Box sx={{ flex: 1, minHeight: 0, width: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
              {lastAgentAnswer && (
                <Paper sx={{ p: 1.5, borderRadius: 2, border: '1px solid', borderColor: 'success.main' }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: 'success.main' }}>
                    LAST INSIGHT BRIEF
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                    {lastAgentAnswer.goal}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {lastAgentAnswer.answer.slice(0, 280)}
                    {lastAgentAnswer.answer.length > 280 ? '…' : ''}
                  </Typography>
                </Paper>
              )}
              <Box sx={{ flex: 1, minHeight: 0 }}>
                <DocumentChat
                  documentIds={selectedDocuments}
                  conversationId={selectedConversationId}
                  onNewConversation={(id) => setSelectedConversationId(id)}
                />
              </Box>
            </Box>
          </Grid>
        </Grid>
      )}

      <Drawer
        anchor="right"
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        sx={{ '& .MuiDrawer-paper': { width: 400, p: 2 } }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Chat History</Typography>
          <IconButton onClick={() => setHistoryOpen(false)}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Divider sx={{ mb: 2 }} />
        <ChatHistory
          onConversationSelect={(id) => {
            setSelectedConversationId(id)
            setMode('chat')
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
