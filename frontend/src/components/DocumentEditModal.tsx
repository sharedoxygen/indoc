import React, { useState, useEffect } from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Box,
    CircularProgress,
    IconButton,
    Typography
} from '@mui/material'
import { Close as CloseIcon } from '@mui/icons-material'
import { useUpdateDocumentMutation } from '../store/api'
import { useSnackbar } from 'notistack'

interface Document {
    uuid: string
    filename: string
    title?: string
    description?: string
    tags?: string[]
}

interface DocumentEditModalProps {
    open: boolean
    document: Document | null
    onClose: () => void
    onSaved?: () => void
}

const DocumentEditModal: React.FC<DocumentEditModalProps> = ({
    open,
    document,
    onClose,
    onSaved
}) => {
    const { enqueueSnackbar } = useSnackbar()
    const [updateDocument, { isLoading }] = useUpdateDocumentMutation()

    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [tags, setTags] = useState('')

    useEffect(() => {
        if (document) {
            setTitle(document.title || '')
            setDescription(document.description || '')
            setTags((document.tags || []).join(', '))
        }
    }, [document])

    const handleSave = async () => {
        if (!document) return

        try {
            await updateDocument({
                id: document.uuid,
                title,
                description,
                tags: tags.split(',').map((t) => t.trim()).filter(Boolean)
            }).unwrap()

            enqueueSnackbar('Document updated successfully', { variant: 'success' })
            onSaved?.()
            onClose()
        } catch (error: any) {
            console.error('Save failed:', error)
            enqueueSnackbar(error?.data?.detail || 'Failed to save document', { variant: 'error' })
        }
    }

    const handleClose = () => {
        if (!isLoading) {
            onClose()
        }
    }

    if (!document) return null

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="sm"
            fullWidth
        >
            <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Edit Document
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        {document.filename}
                    </Typography>
                </Box>
                <IconButton onClick={handleClose} size="small" disabled={isLoading}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>

            <DialogContent dividers>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <TextField
                        label="Title"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        fullWidth
                        placeholder="Enter document title"
                        disabled={isLoading}
                    />
                    
                    <TextField
                        label="Description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        fullWidth
                        multiline
                        minRows={3}
                        maxRows={6}
                        placeholder="Enter document description"
                        disabled={isLoading}
                    />
                    
                    <TextField
                        label="Tags"
                        value={tags}
                        onChange={(e) => setTags(e.target.value)}
                        fullWidth
                        placeholder="tag1, tag2, tag3"
                        helperText="Comma-separated tags"
                        disabled={isLoading}
                    />
                </Box>
            </DialogContent>

            <DialogActions sx={{ px: 3, pb: 2 }}>
                <Button onClick={handleClose} disabled={isLoading}>
                    Cancel
                </Button>
                <Button
                    onClick={handleSave}
                    variant="contained"
                    disabled={isLoading}
                    startIcon={isLoading ? <CircularProgress size={16} /> : null}
                >
                    {isLoading ? 'Saving...' : 'Save Changes'}
                </Button>
            </DialogActions>
        </Dialog>
    )
}

export default DocumentEditModal

