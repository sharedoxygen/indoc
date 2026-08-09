import React, { useState } from 'react'
import {
    Drawer,
    Box,
    Typography,
    IconButton,
    Chip,
    List,
    ListItem,
    ListItemText,
    Divider,
    Button,
    Avatar,
    Grid,
    Card,
    CardContent,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    CircularProgress
} from '@mui/material'
import {
    Close as CloseIcon,
    Download as DownloadIcon,
    Share as ShareIcon,
    Edit as EditIcon,
    InsertDriveFile as FileIcon,
    Folder as FolderIcon,
    Schedule as ScheduleIcon,
    Person as PersonIcon,
    Security as SecurityIcon,
    Delete as DeleteIcon
} from '@mui/icons-material'
import { formatDistanceToNow, format } from 'date-fns'
import DocumentEditModal from './DocumentEditModal'

interface Document {
    id?: number
    uuid: string
    filename: string
    file_type: string
    file_size: number
    folder_path?: string
    title?: string
    description?: string
    tags?: string[]
    document_set_id?: string
    status?: string
    virus_scan_status?: string
    created_at: string
    updated_at?: string
    uploaded_by?: string
    custom_metadata?: any
}

interface DocumentDetailsDrawerProps {
    open: boolean
    document: Document | null
    onClose: () => void
    onEdit?: (document: Document) => void
    onDownload?: (document: Document) => void
    onShare?: (document: Document) => void
    onDelete?: (document: Document) => void
}

const DocumentDetailsDrawer: React.FC<DocumentDetailsDrawerProps> = ({
    open,
    document,
    onClose,
    onEdit,
    onDownload,
    onShare,
    onDelete
}) => {
    const [showDeleteDialog, setShowDeleteDialog] = useState(false)
    const [showEditModal, setShowEditModal] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)

    if (!document) return null

    const handleEditClick = () => {
        setShowEditModal(true)
    }

    const handleEditSaved = () => {
        // Optionally trigger a refresh or callback
        onEdit?.(document)
    }

    const handleDeleteClick = () => {
        setShowDeleteDialog(true)
    }

    const handleDeleteConfirm = async () => {
        setIsDeleting(true)
        try {
            await onDelete?.(document)
            setShowDeleteDialog(false)
            onClose() // Close drawer after successful delete
        } catch (error) {
            console.error('Delete failed:', error)
        } finally {
            setIsDeleting(false)
        }
    }

    const handleDeleteCancel = () => {
        setShowDeleteDialog(false)
    }

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }

    const getStatusColor = (status?: string) => {
        if (!status) return 'default'
        switch (status) {
            case 'indexed': return 'success'
            case 'stored': return 'info'  // Images - stored but not semantically searchable
            case 'processing': return 'warning'
            case 'pending': return 'info'
            case 'partially_indexed': return 'warning'
            case 'failed': return 'error'
            default: return 'default'
        }
    }

    const getStatusLabel = (status?: string) => {
        if (!status) return status
        switch (status) {
            case 'indexed': return 'Fully Searchable'
            case 'stored': return 'Stored (Metadata Only)'
            case 'processing': return 'Processing'
            case 'pending': return 'Pending'
            case 'partially_indexed': return 'Partially Indexed'
            case 'failed': return 'Failed'
            default: return status
        }
    }

    const getVirusStatusColor = (status?: string) => {
        if (!status) return 'default'
        switch (status) {
            case 'clean': return 'success'
            case 'scanning': return 'warning'
            case 'infected': return 'error'
            default: return 'default'
        }
    }

    return (
        <Drawer
            anchor="right"
            open={open}
            onClose={onClose}
            sx={{
                '& .MuiDrawer-paper': {
                    width: { xs: '100%', sm: 480 },
                    borderRadius: { xs: 0, sm: '16px 0 0 16px' }
                }
            }}
        >
            <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
                {/* Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
                    <Box sx={{ flex: 1, mr: 2 }}>
                        <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                            {document.title || document.filename}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            {document.filename}
                        </Typography>
                    </Box>
                    <IconButton onClick={onClose} size="small">
                        <CloseIcon />
                    </IconButton>
                </Box>

                {/* Action Buttons */}
                <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
                    <Button
                        variant="contained"
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={() => onDownload?.(document)}
                        sx={{ flex: 1 }}
                    >
                        Download
                    </Button>
                    <Button
                        variant="outlined"
                        size="small"
                        startIcon={<ShareIcon />}
                        onClick={() => onShare?.(document)}
                        sx={{ flex: 1 }}
                    >
                        Share
                    </Button>
                    <Button
                        variant="outlined"
                        size="small"
                        startIcon={<EditIcon />}
                        onClick={handleEditClick}
                    >
                        Edit
                    </Button>
                </Box>

                {/* Delete Button (Separate Row) */}
                <Box sx={{ mb: 3 }}>
                    <Button
                        variant="outlined"
                        color="error"
                        size="small"
                        fullWidth
                        startIcon={<DeleteIcon />}
                        onClick={handleDeleteClick}
                    >
                        Delete Document
                    </Button>
                </Box>

                {/* Status Chips */}
                <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
                    {document.status && (
                        <Chip
                            label={getStatusLabel(document.status)}
                            color={getStatusColor(document.status)}
                            size="small"
                        />
                    )}
                    {document.virus_scan_status && (
                        <Chip
                            label={`Virus: ${document.virus_scan_status}`}
                            color={getVirusStatusColor(document.virus_scan_status)}
                            size="small"
                        />
                    )}
                    <Chip
                        label={document.file_type.toUpperCase()}
                        variant="outlined"
                        size="small"
                    />
                </Box>

                {/* Searchability Info for Images */}
                {document.status === 'stored' && (
                    <Box sx={{ mb: 3, p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                        <Typography variant="body2" sx={{ color: 'info.dark', fontWeight: 600 }}>
                            📷 Image Document
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'info.dark', display: 'block', mt: 0.5 }}>
                            This image is stored and viewable, but not semantically searchable.
                            You can search by filename, tags, and description only.
                        </Typography>
                    </Box>
                )}

                {/* Document Info Cards */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                        <Card variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                            <FileIcon color="primary" sx={{ fontSize: 32, mb: 1 }} />
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                {formatFileSize(document.file_size)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                File Size
                            </Typography>
                        </Card>
                    </Grid>
                    <Grid item xs={6}>
                        <Card variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                            <ScheduleIcon color="primary" sx={{ fontSize: 32, mb: 1 }} />
                            <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                {formatDistanceToNow(new Date(document.created_at), { addSuffix: true })}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Uploaded
                            </Typography>
                        </Card>
                    </Grid>
                </Grid>

                {/* Details List */}
                <List sx={{ bgcolor: 'background.paper', borderRadius: 2, mb: 2 }}>
                    {document.folder_path && (
                        <ListItem>
                            <Avatar sx={{ mr: 2, bgcolor: 'primary.light' }}>
                                <FolderIcon />
                            </Avatar>
                            <ListItemText
                                primary="Folder Path"
                                secondary={document.folder_path}
                            />
                        </ListItem>
                    )}

                    {document.document_set_id && (
                        <ListItem>
                            <Avatar sx={{ mr: 2, bgcolor: 'secondary.light' }}>
                                <SecurityIcon />
                            </Avatar>
                            <ListItemText
                                primary="Document Set"
                                secondary={document.document_set_id}
                            />
                        </ListItem>
                    )}

                    <ListItem>
                        <Avatar sx={{ mr: 2, bgcolor: 'success.light' }}>
                            <PersonIcon />
                        </Avatar>
                        <ListItemText
                            primary="Uploaded By"
                            secondary={document.uploaded_by || 'Unknown'}
                        />
                    </ListItem>
                </List>

                {/* Description */}
                {document.description && (
                    <Box sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Description
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            {document.description}
                        </Typography>
                    </Box>
                )}

                {/* Tags */}
                {document.tags && document.tags.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Tags
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {document.tags.map((tag, index) => (
                                <Chip key={index} label={tag} size="small" variant="outlined" />
                            ))}
                        </Box>
                    </Box>
                )}

                {/* Technical Details */}
                <Box sx={{ mt: 'auto', pt: 2 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                        Document ID: {document.uuid}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                        Created: {new Date(document.created_at).toLocaleString()}
                    </Typography>
                    {document.updated_at && (
                        <Typography variant="caption" color="text.secondary">
                            Modified: {new Date(document.updated_at).toLocaleString()}
                        </Typography>
                    )}
                </Box>
            </Box>

            {/* Delete Confirmation Dialog */}
            <Dialog
                open={showDeleteDialog}
                onClose={handleDeleteCancel}
                maxWidth="xs"
                fullWidth
            >
                <DialogTitle sx={{ fontWeight: 600 }}>
                    Delete Document?
                </DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to delete <strong>{document.filename}</strong>?
                        <Box sx={{ mt: 2, p: 2, bgcolor: 'error.light', borderRadius: 1 }}>
                            <Typography variant="body2" sx={{ color: 'error.dark', fontWeight: 600 }}>
                                ⚠️ This action cannot be undone
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'error.dark', display: 'block', mt: 0.5 }}>
                                The document will be permanently removed from all storage systems.
                            </Typography>
                        </Box>
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2 }}>
                    <Button
                        onClick={handleDeleteCancel}
                        disabled={isDeleting}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleDeleteConfirm}
                        color="error"
                        variant="contained"
                        disabled={isDeleting}
                        startIcon={isDeleting ? <CircularProgress size={16} /> : <DeleteIcon />}
                    >
                        {isDeleting ? 'Deleting...' : 'Delete'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Edit Modal */}
            <DocumentEditModal
                open={showEditModal}
                document={document}
                onClose={() => setShowEditModal(false)}
                onSaved={handleEditSaved}
            />
        </Drawer>
    )
}

export default DocumentDetailsDrawer

