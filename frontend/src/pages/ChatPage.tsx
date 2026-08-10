import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Paper,
  Chip,
  Card,
  CardContent,
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
} from '@mui/material'
import { DocumentChat } from '../components/DocumentChat'
import ChatHistory from '../components/ChatHistory'
import DocumentDetailsDrawer from '../components/DocumentDetailsDrawer'
import AgentModePanel from '../components/agent/AgentModePanel'
import { ArcMeter } from '../components/instruments'
import { useGetDocumentsQuery } from '../store/api'
import { format } from 'date-fns'
import {
  Chat as ChatIcon,
  History as HistoryIcon,
  Close as CloseIcon,
  FlightTakeoff as AgentIcon,
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

  // Auto-select all indexed docs once when they first load
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
    if (selectedDocuments.length === availableDocuments.length) {
      setSelectedDocuments([])
    } else {
      setSelectedDocuments(availableDocuments.map((doc: any) => doc.uuid))
    }
  }

  const selectionPct =
    availableDocuments.length > 0 ? (selectedDocuments.length / availableDocuments.length) * 100 : 0

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            {mode === 'agent' ? 'Agent Tower' : 'Document Chat'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {mode === 'agent' ? 'Watch the ReAct agent fly missions over your docs' : 'Conversational Q&A over indexed documents'}
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
            <ToggleButton value="agent">
              <AgentIcon sx={{ mr: 0.75, fontSize: 18 }} /> Agent
            </ToggleButton>
            <ToggleButton value="chat">
              <ChatIcon sx={{ mr: 0.75, fontSize: 18 }} /> Chat
            </ToggleButton>
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
          <Button variant="outlined" startIcon={<HistoryIcon />} onClick={() => setHistoryOpen(true)}>
            History
          </Button>
        </Box>
      </Box>

      <Grid container spacing={2} sx={{ flexGrow: 1, height: 'calc(100% - 72px)', minHeight: 0 }}>
        <Grid item xs={12} md={mode === 'agent' ? 3 : 4} sx={{ height: '100%', minHeight: 0 }}>
          <Paper
            sx={{
              p: 2,
              borderRadius: 3,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ mb: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
                Scope
              </Typography>
              <Button size="small" onClick={handleSelectAll} disabled={availableDocuments.length === 0}>
                {selectedDocuments.length === availableDocuments.length ? 'Clear' : 'All'}
              </Button>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
              <ArcMeter
                value={selectionPct}
                label="Selected"
                subtitle={`${selectedDocuments.length}/${availableDocuments.length}`}
                unit="%"
                precision={0}
                size={100}
                status={selectedDocuments.length > 0 ? 'ok' : 'idle'}
              />
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
              <Chip label={`${data?.total ?? availableDocuments.length}`} size="small" />
            </Box>

            <Box sx={{ flexGrow: 1, overflow: 'auto', pr: 0.5 }}>
              {isLoading ? (
                <Typography color="text.secondary">Loading…</Typography>
              ) : availableDocuments.length === 0 ? (
                <Typography color="text.secondary">No indexed documents.</Typography>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {availableDocuments.map((doc: any) => {
                    const isSelected = selectedDocuments.includes(doc.uuid)
                    return (
                      <Card
                        component={motion.div}
                        key={doc.uuid}
                        layout
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0, scale: isSelected ? 1 : 0.99 }}
                        whileHover={{ y: -2 }}
                        sx={{
                          cursor: 'pointer',
                          border: isSelected ? 2 : 1,
                          borderColor: isSelected ? 'primary.main' : 'divider',
                          bgcolor: isSelected ? 'action.selected' : 'background.paper',
                        }}
                        onClick={(e: React.MouseEvent) => handleDocumentClick(doc, e)}
                      >
                        <CardContent sx={{ p: 1.25, '&:last-child': { pb: 1.25 } }}>
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                            <Checkbox
                              checked={isSelected}
                              size="small"
                              sx={{ p: 0, mt: 0.25 }}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDocumentToggle(doc.uuid)
                              }}
                            />
                            <Avatar
                              sx={{
                                width: 28,
                                height: 28,
                                bgcolor: getFileColor(doc.file_type),
                                fontSize: '0.7rem',
                              }}
                            >
                              <FileTypeIcon fileType={doc.file_type} iconProps={{ fontSize: 'small' }} />
                            </Avatar>
                            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                              <Typography
                                variant="subtitle2"
                                sx={{
                                  fontWeight: 600,
                                  fontSize: '0.8rem',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {doc.title || doc.filename}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {format(new Date(doc.created_at), 'MMM dd')}
                              </Typography>
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    )
                  })}
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={mode === 'agent' ? 9 : 8} sx={{ height: '100%', minHeight: 0, display: 'flex' }}>
          <Box sx={{ flex: 1, minHeight: 0, width: '100%' }}>
            {mode === 'agent' ? (
              <AgentModePanel
                documentIds={selectedDocuments}
                onFinalAnswer={(goal, answer) => {
                  setLastAgentAnswer({ goal, answer })
                  enqueueSnackbar('Mission complete — answer landed on the arrival board', {
                    variant: 'success',
                  })
                }}
              />
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1 }}>
                {lastAgentAnswer && (
                  <Paper sx={{ p: 1.5, borderRadius: 2, border: '1px solid', borderColor: 'success.main' }}>
                    <Typography variant="caption" sx={{ fontWeight: 700, color: 'success.main' }}>
                      LAST AGENT ARRIVAL
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
            )}
          </Box>
        </Grid>
      </Grid>

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
