import React, { useMemo, useState } from 'react'
import { Box, Typography, Grid, Paper, Chip, Card, CardContent, Checkbox, Avatar, Button, TextField, InputAdornment, MenuItem, Select, FormControl, InputLabel, Drawer, IconButton, Divider } from '@mui/material'
import { DocumentChat } from '../components/DocumentChat'
import ChatHistory from '../components/ChatHistory'
import DocumentDetailsDrawer from '../components/DocumentDetailsDrawer'
import { useGetDocumentsQuery } from '../store/api'
import { format } from 'date-fns'
import { Chat as ChatIcon, History as HistoryIcon, Close as CloseIcon } from '@mui/icons-material'
import FileTypeIcon, { getFileColor } from '../components/FileTypeIcon'
import { Search as SearchIcon } from '@mui/icons-material'
import { useDebounce } from '../hooks/useDebounce'

const ChatPage: React.FC = () => {
    const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
    const [selectedConversationId, setSelectedConversationId] = useState<string | undefined>()
    const [historyOpen, setHistoryOpen] = useState(false)
    const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false)
    const [selectedDocumentForDetails, setSelectedDocumentForDetails] = useState<any>(null)
    const [search, setSearch] = useState('')
    const [fileType, setFileType] = useState<'all' | string>('all')
    const [sortBy, setSortBy] = useState<'created_at' | 'filename' | 'file_type' | 'file_size' | 'updated_at'>('created_at')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

    // Debounce the search term to reduce API calls (increased for better UX)
    const debouncedSearch = useDebounce(search, 500)

    const { data, isLoading } = useGetDocumentsQuery({
        skip: 0,
        limit: 100,  // Reduced from 1000 - pagination handles more
        search: debouncedSearch || undefined,
        file_type: fileType,
        sort_by: sortBy,
        sort_order: sortOrder,
        status: 'indexed'
    })
    // Only show documents that are searchable (indexed)
    const availableDocuments = useMemo(
        () => (data?.documents || []).filter((d: any) => d.status === 'indexed'),
        [data]
    )

    const selectedDocs = useMemo(
        () => availableDocuments.filter((d: any) => selectedDocuments.includes(d.uuid)),
        [availableDocuments, selectedDocuments]
    )

    const handleDocumentToggle = (docId: string) => {
        const newSelection = selectedDocuments.includes(docId)
            ? selectedDocuments.filter(id => id !== docId)
            : [...selectedDocuments, docId]
        setSelectedDocuments(newSelection)
    }

    const handleDocumentClick = (doc: any, e: React.MouseEvent) => {
        // Only show details if clicking on the card itself, not the checkbox
        if ((e.target as HTMLElement).closest('.MuiCheckbox-root')) {
            return
        }
        setSelectedDocumentForDetails(doc)
        setDetailsDrawerOpen(true)
    }

    const handleCloseDetailsDrawer = () => {
        setDetailsDrawerOpen(false)
        setSelectedDocumentForDetails(null)
    }

    const handleSelectAll = () => {
        if (selectedDocuments.length === availableDocuments.length) {
            setSelectedDocuments([])
        } else {
            setSelectedDocuments(availableDocuments.map((doc: any) => doc.uuid))
        }
    }

    return (
        <Box sx={{ p: 3, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>Document Chat</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                        variant="contained"
                        startIcon={<ChatIcon />}
                        onClick={() => {
                            // Reset selection and start a fresh conversation
                            setSelectedConversationId(undefined)
                        }}
                    >
                        New Chat
                    </Button>
                    <Button
                        variant="outlined"
                        startIcon={<HistoryIcon />}
                        onClick={() => setHistoryOpen(true)}
                    >
                        Chat History
                    </Button>
                </Box>
            </Box>

            <Grid container spacing={3} sx={{ flexGrow: 1, height: 'calc(100% - 60px)' }}>
                {/* Document Selection Panel - Fixed Header, Scrollable List on LEFT */}
                <Grid item xs={12} md={4} sx={{ height: '100%' }}>
                    <Paper sx={{
                        p: 3,
                        borderRadius: 3,
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column'
                    }}>
                        {/* Fixed Header Section */}
                        <Box sx={{ mb: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                <Typography variant="h6" sx={{ fontWeight: 600 }}>Select Documents</Typography>
                                <Button
                                    size="small"
                                    onClick={handleSelectAll}
                                    disabled={availableDocuments.length === 0}
                                >
                                    {selectedDocuments.length === availableDocuments.length ? 'Clear All' : 'Select All'}
                                </Button>
                            </Box>

                            <Chip
                                icon={<ChatIcon />}
                                label={
                                    selectedDocuments.length > 0
                                        ? `${selectedDocuments.length} document(s) selected`
                                        : 'Using all accessible documents'
                                }
                                color={selectedDocuments.length > 0 ? 'primary' : 'success'}
                                variant={selectedDocuments.length === 0 ? 'filled' : 'outlined'}
                            />
                            <Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: '1fr', gap: 1.5 }}>
                                <TextField
                                    size="small"
                                    fullWidth
                                    placeholder="Search documents..."
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    InputProps={{ startAdornment: (<InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>) }}
                                />
                                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                                    <FormControl size="small" sx={{ minWidth: 120 }}>
                                        <InputLabel>Type</InputLabel>
                                        <Select label="Type" value={fileType} onChange={(e) => setFileType(e.target.value as any)}>
                                            <MenuItem value="all">All</MenuItem>
                                            <MenuItem value="pdf">PDF</MenuItem>
                                            <MenuItem value="txt">TXT</MenuItem>
                                            <MenuItem value="docx">DOCX</MenuItem>
                                            <MenuItem value="pptx">PPTX</MenuItem>
                                        </Select>
                                    </FormControl>
                                    <FormControl size="small" sx={{ minWidth: 140 }}>
                                        <InputLabel>Sort By</InputLabel>
                                        <Select label="Sort By" value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
                                            <MenuItem value="created_at">Created</MenuItem>
                                            <MenuItem value="updated_at">Updated</MenuItem>
                                            <MenuItem value="filename">Filename</MenuItem>
                                            <MenuItem value="file_type">File Type</MenuItem>
                                            <MenuItem value="file_size">File Size</MenuItem>
                                        </Select>
                                    </FormControl>
                                    <FormControl size="small" sx={{ minWidth: 120 }}>
                                        <InputLabel>Order</InputLabel>
                                        <Select label="Order" value={sortOrder} onChange={(e) => setSortOrder(e.target.value as any)}>
                                            <MenuItem value="desc">Desc</MenuItem>
                                            <MenuItem value="asc">Asc</MenuItem>
                                        </Select>
                                    </FormControl>
                                    <Chip label={`${data?.total ?? availableDocuments.length} results`} size="small" />
                                </Box>
                                {selectedDocs.length > 0 && (
                                    <Box sx={{ mt: 0.5, p: 1, borderRadius: 2, bgcolor: 'background.default', border: 1, borderColor: 'divider' }}>
                                        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                                            Selected ({selectedDocs.length})
                                        </Typography>
                                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, maxHeight: 120, overflow: 'auto', pr: 0.5 }}>
                                            {selectedDocs.map((doc: any) => (
                                                <Chip
                                                    key={doc.uuid}
                                                    size="small"
                                                    variant="outlined"
                                                    label={doc.title || doc.filename}
                                                    onDelete={() => handleDocumentToggle(doc.uuid)}
                                                    sx={{ maxWidth: '100%', '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' } }}
                                                />
                                            ))}
                                        </Box>
                                    </Box>
                                )}
                            </Box>
                        </Box>

                        {/* Scrollable Documents List - Only this part scrolls */}
                        <Box sx={{
                            flexGrow: 1,
                            overflow: 'auto',
                            pr: 1,
                            '&::-webkit-scrollbar': {
                                width: '8px',
                            },
                            '&::-webkit-scrollbar-track': {
                                background: 'rgba(0,0,0,0.05)',
                                borderRadius: '4px',
                            },
                            '&::-webkit-scrollbar-thumb': {
                                background: 'rgba(0,0,0,0.2)',
                                borderRadius: '4px',
                                '&:hover': {
                                    background: 'rgba(0,0,0,0.3)',
                                }
                            }
                        }}>
                            {isLoading ? (
                                <Typography color="text.secondary">Loading documents...</Typography>
                            ) : availableDocuments.length === 0 ? (
                                <Typography color="text.secondary">No documents available for chat.</Typography>
                            ) : (
                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    {availableDocuments.map((doc: any) => {
                                        const isSelected = selectedDocuments.includes(doc.uuid)
                                        return (
                                            <Card
                                                key={doc.uuid}
                                                sx={{
                                                    cursor: 'pointer',
                                                    border: isSelected ? 2 : 1,
                                                    borderColor: isSelected ? 'primary.main' : 'divider',
                                                    bgcolor: isSelected ? 'primary.lighter' : 'background.paper',
                                                    transition: 'all 0.2s ease',
                                                    '&:hover': {
                                                        borderColor: 'primary.main',
                                                        transform: 'translateY(-1px)',
                                                        boxShadow: 2
                                                    }
                                                }}
                                                onClick={(e) => handleDocumentClick(doc, e)}
                                            >
                                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                                                        <Checkbox
                                                            checked={isSelected}
                                                            size="small"
                                                            sx={{ p: 0, mt: 0.5 }}
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                handleDocumentToggle(doc.uuid)
                                                            }}
                                                        />
                                                        <Avatar
                                                            sx={{
                                                                width: 32,
                                                                height: 32,
                                                                bgcolor: getFileColor(doc.file_type),
                                                                fontSize: '0.75rem'
                                                            }}
                                                        >
                                                            <FileTypeIcon fileType={doc.file_type} iconProps={{ fontSize: 'small' }} />
                                                        </Avatar>
                                                        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                                                            <Typography
                                                                variant="subtitle2"
                                                                sx={{
                                                                    fontWeight: 600,
                                                                    overflow: 'hidden',
                                                                    textOverflow: 'ellipsis',
                                                                    whiteSpace: 'nowrap'
                                                                }}
                                                            >
                                                                {doc.title || doc.filename}
                                                            </Typography>
                                                            <Typography
                                                                variant="caption"
                                                                color="text.secondary"
                                                                sx={{
                                                                    display: 'block',
                                                                    overflow: 'hidden',
                                                                    textOverflow: 'ellipsis',
                                                                    whiteSpace: 'nowrap'
                                                                }}
                                                            >
                                                                {doc.description || 'No description'}
                                                            </Typography>
                                                            <Box sx={{ display: 'flex', gap: 1, mt: 1, alignItems: 'center' }}>
                                                                <Chip
                                                                    label={doc.status}
                                                                    size="small"
                                                                    color={doc.status === 'indexed' ? 'success' : 'warning'}
                                                                    variant="outlined"
                                                                />
                                                                <Typography variant="caption" color="text.secondary">
                                                                    {format(new Date(doc.created_at), 'MMM dd')}
                                                                </Typography>
                                                            </Box>
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

                {/* Chat Panel - on RIGHT */}
                <Grid item xs={12} md={8} sx={{ height: '100%', minHeight: 0, display: 'flex' }}>
                    <Box sx={{ flex: 1, minHeight: 0 }}>
                        <DocumentChat
                            documentIds={selectedDocuments}
                            conversationId={selectedConversationId}
                            onNewConversation={(id) => {
                                console.log('🆕 ChatPage: New conversation created:', id);
                                setSelectedConversationId(id);
                            }}
                        />
                    </Box>
                </Grid>
            </Grid>

            {/* Chat History Drawer */}
            <Drawer
                anchor="right"
                open={historyOpen}
                onClose={() => setHistoryOpen(false)}
                sx={{
                    '& .MuiDrawer-paper': {
                        width: 400,
                        p: 2
                    }
                }}
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
                        console.log('🎯 ChatPage: Conversation selected:', id);
                        setSelectedConversationId(id);
                        console.log('✅ ChatPage: State updated to:', id);
                        setHistoryOpen(false);
                    }}
                    selectedConversationId={selectedConversationId}
                />
            </Drawer>

            {/* Document Details Drawer */}
            <DocumentDetailsDrawer
                open={detailsDrawerOpen}
                document={selectedDocumentForDetails}
                onClose={handleCloseDetailsDrawer}
                onEdit={(doc) => {
                    console.log('Edit document:', doc.uuid)
                }}
                onDownload={(doc) => {
                    window.open(`/api/v1/files/${doc.uuid}/download`, '_blank')
                }}
                onShare={(doc) => {
                    console.log('Share document:', doc.uuid)
                }}
            />
        </Box>
    )
}

export default ChatPage


