import React, { useState, useEffect } from 'react'
import {
    Box,
    Paper,
    Typography,
    List,
    ListItem,
    ListItemText,
    ListItemIcon,
    ListItemSecondaryAction,
    IconButton,
    Chip,
    LinearProgress,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Alert,
    Tooltip,
    Stack,
    Card,
    CardContent,
    Menu,
    MenuItem,
    Divider,
    Skeleton,
    TextField,
    InputAdornment,
    Checkbox,
    Toolbar,
} from '@mui/material'
import {
    Chat as ChatIcon,
    Archive as ArchiveIcon,
    Unarchive as UnarchiveIcon,
    Delete as DeleteIcon,
    PushPin as PinIcon,
    PushPinOutlined as UnpinIcon,
    MoreVert as MoreIcon,
    Search as SearchIcon,
    Storage as StorageIcon,
    TrendingUp as UpgradeIcon,
    AccessTime as TimeIcon,
    Folder as FolderIcon,
    FolderOpen as FolderOpenIcon,
    CloudUpload as CloudIcon,
    Warning as WarningIcon,
    SelectAll as SelectAllIcon,
    Deselect as DeselectIcon,
} from '@mui/icons-material'
import { formatDistanceToNow } from 'date-fns'
import { http } from '../services/http'
import { useSnackbar } from 'notistack'

interface Conversation {
    id: string
    title: string
    created_at: string
    updated_at: string
    message_count?: number
    is_archived?: boolean
    is_pinned?: boolean
    is_favorite?: boolean
}

interface StorageUsage {
    tier: string
    is_premium: boolean
    conversation_storage: {
        used: number
        limit: number
        percentage: number
        used_formatted: string
        limit_formatted: string
    }
    document_storage: {
        used: number
        limit: number
        percentage: number
        used_formatted: string
        limit_formatted: string
    }
    retention: {
        conversation_days: number
        document_days: number
    }
    counts: {
        conversations: number
        messages: number
    }
    billing?: {
        monthly_fee: number
        overage_charges: number
        last_billed: string | null
    }
}

interface ChatHistoryProps {
    onConversationSelect?: (conversationId: string) => void
    selectedConversationId?: string
}

const ChatHistory: React.FC<ChatHistoryProps> = ({
    onConversationSelect,
    selectedConversationId,
}) => {
    const { enqueueSnackbar } = useSnackbar()
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [storageUsage, setStorageUsage] = useState<StorageUsage | null>(null)
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [includeArchived, setIncludeArchived] = useState(false)
    const [selectedConv, setSelectedConv] = useState<Conversation | null>(null)
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
    const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false)
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
    const [selectedConversations, setSelectedConversations] = useState<Set<string>>(new Set())
    const [selectionMode, setSelectionMode] = useState(false)

    useEffect(() => {
        fetchChatHistory()
        fetchStorageUsage()
    }, [includeArchived])

    const fetchChatHistory = async () => {
        try {
            setLoading(true)
            const response = await http.get('/chat/history', {
                params: {
                    limit: 100,
                    include_archived: includeArchived,
                }
            })
            setConversations(response.data.conversations)
        } catch (error) {
            enqueueSnackbar('Failed to load chat history', { variant: 'error' })
        } finally {
            setLoading(false)
        }
    }

    const fetchStorageUsage = async () => {
        try {
            const response = await http.get('/chat/storage-usage')
            setStorageUsage(response.data)
        } catch (error) {
            console.error('Failed to load storage usage:', error)
        }
    }

    const handleArchive = async (conversation: Conversation) => {
        try {
            await http.post(`/chat/conversations/${conversation.id}/archive`)
            enqueueSnackbar('Conversation archived successfully', { variant: 'success' })
            fetchChatHistory()
            fetchStorageUsage()
        } catch (error) {
            enqueueSnackbar('Failed to archive conversation', { variant: 'error' })
        }
    }

    const handleRestore = async (conversation: Conversation) => {
        try {
            await http.post(`/chat/conversations/${conversation.id}/restore`)
            enqueueSnackbar('Conversation restored successfully', { variant: 'success' })
            fetchChatHistory()
            fetchStorageUsage()
        } catch (error: any) {
            if (error.response?.status === 402) {
                enqueueSnackbar('Insufficient storage. Please upgrade your plan.', { variant: 'warning' })
                setUpgradeDialogOpen(true)
            } else {
                enqueueSnackbar('Failed to restore conversation', { variant: 'error' })
            }
        }
    }

    const handlePin = async (conversation: Conversation) => {
        try {
            await http.post(`/chat/conversations/${conversation.id}/pin`, {
                pinned: !conversation.is_pinned
            })
            enqueueSnackbar(
                conversation.is_pinned ? 'Conversation unpinned' : 'Conversation pinned',
                { variant: 'success' }
            )
            fetchChatHistory()
        } catch (error) {
            enqueueSnackbar('Failed to update pin status', { variant: 'error' })
        }
    }

    const handleDelete = async () => {
        if (!selectedConv) return

        try {
            await http.delete(`/chat/conversations/${selectedConv.id}`)
            enqueueSnackbar('Conversation deleted', { variant: 'success' })
            setDeleteDialogOpen(false)
            setSelectedConv(null)
            fetchChatHistory()
            fetchStorageUsage()
        } catch (error) {
            enqueueSnackbar('Failed to delete conversation', { variant: 'error' })
        }
    }

    const handleBulkDelete = async () => {
        if (selectedConversations.size === 0) return

        try {
            await http.post('/chat/conversations/bulk-delete',
                Array.from(selectedConversations)
            )
            enqueueSnackbar(`Deleted ${selectedConversations.size} conversation(s)`, { variant: 'success' })
            setSelectedConversations(new Set())
            setSelectionMode(false)
            setDeleteDialogOpen(false)
            fetchChatHistory()
            fetchStorageUsage()
        } catch (error) {
            enqueueSnackbar('Failed to delete conversations', { variant: 'error' })
        }
    }

    const toggleConversationSelection = (conversationId: string) => {
        const newSelected = new Set(selectedConversations)
        if (newSelected.has(conversationId)) {
            newSelected.delete(conversationId)
        } else {
            newSelected.add(conversationId)
        }
        setSelectedConversations(newSelected)
    }

    const selectAll = () => {
        const allIds = new Set(filteredConversations.map(c => c.id))
        setSelectedConversations(allIds)
    }

    const deselectAll = () => {
        setSelectedConversations(new Set())
    }

    const handleCleanup = async () => {
        try {
            const response = await http.delete('/chat/cleanup')
            enqueueSnackbar(response.data.message, { variant: 'success' })
            fetchChatHistory()
            fetchStorageUsage()
        } catch (error) {
            enqueueSnackbar('Failed to cleanup old conversations', { variant: 'error' })
        }
    }

    const handleUpgradeTier = async (tier: string) => {
        try {
            await http.post(`/chat/upgrade-tier?tier=${tier}`)
            enqueueSnackbar(`Upgraded to ${tier} tier`, { variant: 'success' })
            setUpgradeDialogOpen(false)
            fetchStorageUsage()
        } catch (error) {
            enqueueSnackbar('Failed to upgrade tier', { variant: 'error' })
        }
    }

    const filteredConversations = conversations.filter(conv =>
        conv.title.toLowerCase().includes(searchTerm.toLowerCase())
    )

    const getStorageColor = (percentage: number) => {
        if (percentage >= 90) return 'error'
        if (percentage >= 70) return 'warning'
        return 'primary'
    }

    const getTierColor = (tier: string) => {
        switch (tier) {
            case 'enterprise': return 'error'
            case 'pro': return 'warning'
            case 'basic': return 'info'
            default: return 'default'
        }
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Storage Usage Card */}
            {storageUsage && (
                <Card sx={{ mb: 2 }}>
                    <CardContent>
                        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
                            <Box>
                                <Typography variant="h6" gutterBottom>
                                    Storage Usage
                                </Typography>
                                <Stack direction="row" spacing={1} alignItems="center">
                                    <Chip
                                        label={storageUsage.tier.toUpperCase()}
                                        color={getTierColor(storageUsage.tier)}
                                        size="small"
                                    />
                                    {storageUsage.retention.conversation_days > 0 && (
                                        <Chip
                                            icon={<TimeIcon />}
                                            label={`${storageUsage.retention.conversation_days} days retention`}
                                            variant="outlined"
                                            size="small"
                                        />
                                    )}
                                </Stack>
                            </Box>
                            {storageUsage.tier !== 'enterprise' && (
                                <Button
                                    variant="outlined"
                                    startIcon={<UpgradeIcon />}
                                    onClick={() => setUpgradeDialogOpen(true)}
                                    size="small"
                                >
                                    Upgrade
                                </Button>
                            )}
                        </Stack>

                        {/* Conversation Storage */}
                        <Box mb={2}>
                            <Stack direction="row" justifyContent="space-between" mb={1}>
                                <Typography variant="body2" color="text.secondary">
                                    Conversations
                                </Typography>
                                <Typography variant="body2">
                                    {storageUsage.conversation_storage.used_formatted} / {storageUsage.conversation_storage.limit_formatted}
                                </Typography>
                            </Stack>
                            <LinearProgress
                                variant="determinate"
                                value={storageUsage.conversation_storage.percentage}
                                color={getStorageColor(storageUsage.conversation_storage.percentage)}
                                sx={{ height: 8, borderRadius: 1 }}
                            />
                        </Box>

                        {/* Stats */}
                        <Stack direction="row" spacing={3}>
                            <Box>
                                <Typography variant="h6">
                                    {storageUsage.counts.conversations}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                    Conversations
                                </Typography>
                            </Box>
                            <Box>
                                <Typography variant="h6">
                                    {storageUsage.counts.messages}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                    Messages
                                </Typography>
                            </Box>
                            {storageUsage.billing && (
                                <Box>
                                    <Typography variant="h6">
                                        ${storageUsage.billing.monthly_fee}/mo
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        Monthly Fee
                                    </Typography>
                                </Box>
                            )}
                        </Stack>

                        {/* Warning if near limit */}
                        {storageUsage.conversation_storage.percentage >= 80 && (
                            <Alert severity="warning" sx={{ mt: 2 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                    <WarningIcon fontSize="small" />
                                    <Typography variant="body2">
                                        You're using {storageUsage.conversation_storage.percentage}% of your storage.
                                        Consider archiving old conversations or upgrading your plan.
                                    </Typography>
                                </Stack>
                            </Alert>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Search and Actions */}
            <Paper sx={{ p: 2, mb: 2 }}>
                <Stack spacing={2}>
                    <Stack direction="row" spacing={2} alignItems="center">
                        <TextField
                            placeholder="Search conversations..."
                            variant="outlined"
                            size="small"
                            fullWidth
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            InputProps={{
                                startAdornment: (
                                    <InputAdornment position="start">
                                        <SearchIcon />
                                    </InputAdornment>
                                ),
                            }}
                        />
                        <Button
                            variant={selectionMode ? "contained" : "outlined"}
                            onClick={() => {
                                setSelectionMode(!selectionMode)
                                if (selectionMode) {
                                    setSelectedConversations(new Set())
                                }
                            }}
                            color={selectionMode ? "primary" : "inherit"}
                        >
                            {selectionMode ? 'Cancel Select' : 'Select'}
                        </Button>
                    </Stack>

                    {selectionMode && (
                        <Toolbar
                            variant="dense"
                            sx={{
                                bgcolor: 'primary.main',
                                color: 'primary.contrastText',
                                borderRadius: 1,
                                px: 2,
                                minHeight: 48
                            }}
                        >
                            <Typography variant="body2" sx={{ flex: 1 }}>
                                {selectedConversations.size} selected
                            </Typography>
                            <Stack direction="row" spacing={1}>
                                <Button
                                    size="small"
                                    startIcon={<SelectAllIcon />}
                                    onClick={selectAll}
                                    sx={{ color: 'white' }}
                                >
                                    Select All
                                </Button>
                                <Button
                                    size="small"
                                    startIcon={<DeselectIcon />}
                                    onClick={deselectAll}
                                    sx={{ color: 'white' }}
                                >
                                    Clear
                                </Button>
                                <Button
                                    size="small"
                                    startIcon={<DeleteIcon />}
                                    onClick={() => setDeleteDialogOpen(true)}
                                    disabled={selectedConversations.size === 0}
                                    sx={{ color: 'white' }}
                                    color="error"
                                >
                                    Delete ({selectedConversations.size})
                                </Button>
                            </Stack>
                        </Toolbar>
                    )}

                    <Stack direction="row" spacing={2} alignItems="center">
                        <Button
                            variant="outlined"
                            onClick={() => setIncludeArchived(!includeArchived)}
                            startIcon={includeArchived ? <FolderOpenIcon /> : <FolderIcon />}
                            size="small"
                        >
                            {includeArchived ? 'Hide' : 'Show'} Archived
                        </Button>
                        <Button
                            variant="outlined"
                            onClick={handleCleanup}
                            color="warning"
                            size="small"
                        >
                            Cleanup Old
                        </Button>
                    </Stack>
                </Stack>
            </Paper>

            {/* Conversations List */}
            <Paper sx={{ flex: 1, overflow: 'auto' }}>
                {loading ? (
                    <Box p={2}>
                        {[1, 2, 3].map(i => (
                            <Skeleton key={i} height={60} sx={{ mb: 1 }} />
                        ))}
                    </Box>
                ) : (
                    <List>
                        {filteredConversations.length === 0 ? (
                            <ListItem>
                                <ListItemText
                                    primary="No conversations yet"
                                    secondary="Start a new chat to begin"
                                />
                            </ListItem>
                        ) : (
                            filteredConversations.map((conversation) => (
                                <ListItem
                                    key={conversation.id}
                                    button={!selectionMode}
                                    selected={conversation.id === selectedConversationId}
                                    onClick={() => {
                                        if (selectionMode) {
                                            toggleConversationSelection(conversation.id)
                                        } else {
                                            onConversationSelect?.(conversation.id)
                                        }
                                    }}
                                >
                                    {selectionMode && (
                                        <ListItemIcon>
                                            <Checkbox
                                                edge="start"
                                                checked={selectedConversations.has(conversation.id)}
                                                tabIndex={-1}
                                                disableRipple
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    toggleConversationSelection(conversation.id)
                                                }}
                                            />
                                        </ListItemIcon>
                                    )}
                                    {!selectionMode && (
                                        <ListItemIcon>
                                            <Stack>
                                                <ChatIcon />
                                                {conversation.is_pinned && (
                                                    <PinIcon
                                                        sx={{
                                                            fontSize: 12,
                                                            position: 'absolute',
                                                            top: -4,
                                                            right: -4,
                                                            color: 'primary.main'
                                                        }}
                                                    />
                                                )}
                                            </Stack>
                                        </ListItemIcon>
                                    )}
                                    <ListItemText
                                        primary={
                                            <Stack direction="row" spacing={1} alignItems="center">
                                                <Typography variant="body2">
                                                    {conversation.title}
                                                </Typography>
                                                {conversation.is_archived && (
                                                    <Chip
                                                        label="Archived"
                                                        size="small"
                                                        variant="outlined"
                                                    />
                                                )}
                                            </Stack>
                                        }
                                        secondary={
                                            <Stack direction="row" spacing={1} alignItems="center">
                                                <Typography variant="caption">
                                                    {formatDistanceToNow(new Date(conversation.updated_at), { addSuffix: true })}
                                                </Typography>
                                                {conversation.message_count && (
                                                    <Typography variant="caption" color="text.secondary">
                                                        • {conversation.message_count} messages
                                                    </Typography>
                                                )}
                                            </Stack>
                                        }
                                    />
                                    {!selectionMode && (
                                        <ListItemSecondaryAction>
                                            <IconButton
                                                edge="end"
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    setAnchorEl(e.currentTarget)
                                                    setSelectedConv(conversation)
                                                }}
                                            >
                                                <MoreIcon />
                                            </IconButton>
                                        </ListItemSecondaryAction>
                                    )}
                                </ListItem>
                            ))
                        )}
                    </List>
                )}
            </Paper>

            {/* Context Menu */}
            <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={() => setAnchorEl(null)}
            >
                {selectedConv && (
                    <>
                        <MenuItem onClick={() => {
                            handlePin(selectedConv)
                            setAnchorEl(null)
                        }}>
                            {selectedConv.is_pinned ? <UnpinIcon sx={{ mr: 1 }} /> : <PinIcon sx={{ mr: 1 }} />}
                            {selectedConv.is_pinned ? 'Unpin' : 'Pin'} Conversation
                        </MenuItem>
                        {selectedConv.is_archived ? (
                            <MenuItem onClick={() => {
                                handleRestore(selectedConv)
                                setAnchorEl(null)
                            }}>
                                <UnarchiveIcon sx={{ mr: 1 }} />
                                Restore
                            </MenuItem>
                        ) : (
                            <MenuItem onClick={() => {
                                handleArchive(selectedConv)
                                setAnchorEl(null)
                            }}>
                                <ArchiveIcon sx={{ mr: 1 }} />
                                Archive
                            </MenuItem>
                        )}
                        <Divider />
                        <MenuItem
                            onClick={() => {
                                setDeleteDialogOpen(true)
                                setAnchorEl(null)
                            }}
                            sx={{ color: 'error.main' }}
                        >
                            <DeleteIcon sx={{ mr: 1 }} />
                            Delete
                        </MenuItem>
                    </>
                )}
            </Menu>

            {/* Upgrade Dialog */}
            <Dialog open={upgradeDialogOpen} onClose={() => setUpgradeDialogOpen(false)}>
                <DialogTitle>Upgrade Storage Plan</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 2 }}>
                        <Card>
                            <CardContent>
                                <Typography variant="h6">Basic</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    100MB conversations • 1GB documents • 90 days retention
                                </Typography>
                                <Typography variant="h5" sx={{ mt: 1 }}>
                                    $9.99/mo
                                </Typography>
                                <Button
                                    variant="contained"
                                    fullWidth
                                    sx={{ mt: 2 }}
                                    onClick={() => handleUpgradeTier('basic')}
                                >
                                    Upgrade to Basic
                                </Button>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent>
                                <Typography variant="h6">Pro</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    1GB conversations • 10GB documents • 1 year retention
                                </Typography>
                                <Typography variant="h5" sx={{ mt: 1 }}>
                                    $29.99/mo
                                </Typography>
                                <Button
                                    variant="contained"
                                    fullWidth
                                    sx={{ mt: 2 }}
                                    onClick={() => handleUpgradeTier('pro')}
                                >
                                    Upgrade to Pro
                                </Button>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent>
                                <Typography variant="h6">Enterprise</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    10GB conversations • 100GB documents • Unlimited retention
                                </Typography>
                                <Typography variant="h5" sx={{ mt: 1 }}>
                                    $99.99/mo
                                </Typography>
                                <Button
                                    variant="contained"
                                    fullWidth
                                    sx={{ mt: 2 }}
                                    onClick={() => handleUpgradeTier('enterprise')}
                                >
                                    Upgrade to Enterprise
                                </Button>
                            </CardContent>
                        </Card>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setUpgradeDialogOpen(false)}>Cancel</Button>
                </DialogActions>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
                <DialogTitle>
                    {selectionMode && selectedConversations.size > 0
                        ? `Delete ${selectedConversations.size} Conversation${selectedConversations.size > 1 ? 's' : ''}`
                        : 'Delete Conversation'
                    }
                </DialogTitle>
                <DialogContent>
                    <Typography>
                        {selectionMode && selectedConversations.size > 0
                            ? `Are you sure you want to delete ${selectedConversations.size} conversation(s)? This action cannot be undone.`
                            : `Are you sure you want to delete "${selectedConv?.title}"? This action cannot be undone.`
                        }
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
                    <Button
                        onClick={selectionMode && selectedConversations.size > 0 ? handleBulkDelete : handleDelete}
                        color="error"
                        variant="contained"
                    >
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default ChatHistory

