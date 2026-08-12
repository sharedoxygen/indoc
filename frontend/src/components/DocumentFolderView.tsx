import React, { useMemo, useState } from 'react'
import {
    Box,
    Breadcrumbs,
    Typography,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    ListItemSecondaryAction,
    IconButton,
    Tooltip,
    Chip,
    Stack,
    Paper,
    Grid,
    Card,
    CardActionArea,
    CardContent,
    alpha,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Button,
    CircularProgress,
} from '@mui/material'
import {
    Folder as FolderIcon,
    FolderOpen as FolderOpenIcon,
    InsertDriveFile as FileIcon,
    NavigateNext as NavigateNextIcon,
    Home as HomeIcon,
    PictureAsPdf as PdfIcon,
    Image as ImageIcon,
    Description as DocIcon,
    TableChart as ExcelIcon,
    Code as CodeIcon,
    VideoLibrary as VideoIcon,
    AudioFile as AudioIcon,
    Download as DownloadIcon,
    Visibility as ViewIcon,
    Delete as DeleteIcon,
    DeleteSweep as DeleteFolderIcon,
} from '@mui/icons-material'
import { format } from 'date-fns'
import { useSnackbar } from 'notistack'
import DocumentDetailsDrawer from './DocumentDetailsDrawer'

interface Document {
    id: number
    uuid: string
    filename: string
    file_type: string
    file_size: number
    folder_path?: string
    status: string
    created_at: string
}

interface FolderNode {
    name: string
    path: string
    files: Document[]
    subfolders: Map<string, FolderNode>
    totalSize: number
    fileCount: number
}

interface DocumentFolderViewProps {
    documents: Document[]
    onDocumentSelect?: (doc: Document) => void
    onDocumentView?: (docId: string) => void
    selectedDocuments?: string[]
    onCorpusChanged?: () => void
}

const DocumentFolderView: React.FC<DocumentFolderViewProps> = ({
    documents,
    onDocumentSelect,
    onDocumentView,
    selectedDocuments = [],
    onCorpusChanged,
}) => {
    const { enqueueSnackbar } = useSnackbar()
    const [currentPath, setCurrentPath] = useState<string[]>([])
    const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
    const [drawerOpen, setDrawerOpen] = useState(false)
    const [folderToDelete, setFolderToDelete] = useState<FolderNode | null>(null)
    const [deletingFolder, setDeletingFolder] = useState(false)

    const handleDocumentClick = (doc: Document) => {
        setSelectedDocument(doc)
        setDrawerOpen(true)
    }

    const handleCloseDrawer = () => {
        setDrawerOpen(false)
        setSelectedDocument(null)
    }

    // Build folder tree from flat document list
    const folderTree = useMemo(() => {
        const root: FolderNode = {
            name: 'root',
            path: '',
            files: [],
            subfolders: new Map(),
            totalSize: 0,
            fileCount: 0
        }

        documents.forEach(doc => {
            const path = doc.folder_path || ''
            const parts = path ? path.split('/').filter(p => p) : []

            let current = root

            parts.forEach((part, index) => {
                if (!current.subfolders.has(part)) {
                    current.subfolders.set(part, {
                        name: part,
                        path: parts.slice(0, index + 1).join('/'),
                        files: [],
                        subfolders: new Map(),
                        totalSize: 0,
                        fileCount: 0
                    })
                }
                current = current.subfolders.get(part)!
            })

            current.files.push(doc)
            current.totalSize += doc.file_size
            current.fileCount += 1

            let parent = root
            parts.forEach(part => {
                parent.totalSize += doc.file_size
                parent.fileCount += 1
                parent = parent.subfolders.get(part)!
            })
        })

        return root
    }, [documents])

    const currentFolder = useMemo(() => {
        let folder = folderTree
        currentPath.forEach(part => {
            folder = folder.subfolders.get(part) || folder
        })
        return folder
    }, [folderTree, currentPath])

    const handleFolderClick = (folderName: string) => {
        setCurrentPath([...currentPath, folderName])
    }

    const handleBreadcrumbClick = (index: number) => {
        setCurrentPath(currentPath.slice(0, index))
    }

    const handleDeleteFolder = async () => {
        if (!folderToDelete) return
        setDeletingFolder(true)
        try {
            const form = new FormData()
            form.append('folder_path', folderToDelete.path)
            const response = await fetch('/api/v1/files/folder/delete', {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
                },
                body: form,
            })
            const body = await response.json().catch(() => ({}))
            if (!response.ok) {
                throw new Error(body.detail || 'Folder delete failed')
            }
            enqueueSnackbar(
                body.message ||
                    `Removed ${body.deleted_count ?? 0} document(s) from inDoc under “${folderToDelete.path}”.`,
                { variant: body.failed_count ? 'warning' : 'success', autoHideDuration: 7000 }
            )
            // If we deleted the current folder (or an ancestor), step up
            if (currentPath.join('/') === folderToDelete.path || currentPath.join('/').startsWith(`${folderToDelete.path}/`)) {
                const parts = folderToDelete.path.split('/').filter(Boolean)
                setCurrentPath(parts.slice(0, -1))
            }
            setFolderToDelete(null)
            onCorpusChanged?.()
        } catch (err: any) {
            enqueueSnackbar(err?.message || 'Failed to remove folder from inDoc', { variant: 'error' })
        } finally {
            setDeletingFolder(false)
        }
    }

    const getFileIcon = (fileType: string) => {
        const type = fileType.toLowerCase()
        if (type === 'pdf') return <PdfIcon color="error" />
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(type)) return <ImageIcon color="primary" />
        if (['doc', 'docx'].includes(type)) return <DocIcon color="info" />
        if (['xls', 'xlsx', 'csv'].includes(type)) return <ExcelIcon color="success" />
        if (['mp4', 'avi', 'mov'].includes(type)) return <VideoIcon color="secondary" />
        if (['mp3', 'wav'].includes(type)) return <AudioIcon color="warning" />
        if (['js', 'ts', 'py', 'java'].includes(type)) return <CodeIcon />
        return <FileIcon />
    }

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
    }

    const folders = Array.from(currentFolder.subfolders.values())
    const files = currentFolder.files

    return (
        <Box>
            <Paper sx={{ p: 2, mb: 2 }}>
                <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />}>
                    <Box
                        component="span"
                        onClick={() => setCurrentPath([])}
                        sx={{
                            display: 'flex',
                            alignItems: 'center',
                            cursor: 'pointer',
                            '&:hover': { textDecoration: 'underline' }
                        }}
                    >
                        <HomeIcon sx={{ mr: 0.5 }} fontSize="small" />
                        All Documents
                    </Box>
                    {currentPath.map((part, index) => (
                        <Box
                            key={index}
                            component="span"
                            onClick={() => handleBreadcrumbClick(index + 1)}
                            sx={{
                                cursor: 'pointer',
                                '&:hover': { textDecoration: 'underline' }
                            }}
                        >
                            {part}
                        </Box>
                    ))}
                </Breadcrumbs>
            </Paper>

            {folders.length > 0 && (
                <Box mb={3}>
                    <Typography variant="h6" gutterBottom>
                        Folders
                    </Typography>
                    <Grid container spacing={2}>
                        {folders.map(folder => (
                            <Grid item xs={12} sm={6} md={4} lg={3} key={folder.name}>
                                <Card
                                    sx={{
                                        transition: 'all 0.2s',
                                        '&:hover': {
                                            transform: 'translateY(-4px)',
                                            boxShadow: 4
                                        }
                                    }}
                                >
                                    <CardActionArea onClick={() => handleFolderClick(folder.name)}>
                                        <CardContent>
                                            <Stack direction="row" spacing={1.5} alignItems="center">
                                                <FolderIcon
                                                    sx={{
                                                        fontSize: 48,
                                                        color: 'primary.main'
                                                    }}
                                                />
                                                <Box flex={1} minWidth={0}>
                                                    <Typography variant="body1" fontWeight={500} noWrap>
                                                        {folder.name}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {folder.fileCount} items • {formatFileSize(folder.totalSize)}
                                                    </Typography>
                                                </Box>
                                            </Stack>
                                        </CardContent>
                                    </CardActionArea>
                                    <Box sx={{ px: 1.5, pb: 1.25, display: 'flex', justifyContent: 'flex-end' }}>
                                        <Tooltip title="Remove folder from inDoc (keeps files on disk)">
                                            <IconButton
                                                size="small"
                                                color="error"
                                                aria-label={`Remove ${folder.name} from inDoc`}
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    setFolderToDelete(folder)
                                                }}
                                            >
                                                <DeleteFolderIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </Box>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            )}

            {files.length > 0 && (
                <Box>
                    <Typography variant="h6" gutterBottom>
                        Files ({files.length})
                    </Typography>
                    <Paper>
                        <List>
                            {files.map((file, index) => (
                                <ListItem
                                    key={file.uuid}
                                    divider={index < files.length - 1}
                                    onClick={() => handleDocumentClick(file)}
                                    sx={{
                                        cursor: 'pointer',
                                        '&:hover': {
                                            bgcolor: alpha('#fff', 0.05)
                                        }
                                    }}
                                >
                                    <ListItemIcon>
                                        {getFileIcon(file.file_type)}
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={
                                            <Box component="span" display="inline-flex" alignItems="center" gap={1}>
                                                <Typography component="span" variant="body2">
                                                    {file.filename}
                                                </Typography>
                                                {file.status && (
                                                    <Chip
                                                        label={file.status}
                                                        size="small"
                                                        color={file.status === 'indexed' ? 'success' : 'default'}
                                                        variant="outlined"
                                                    />
                                                )}
                                            </Box>
                                        }
                                        secondary={
                                            <Typography component="span" variant="caption" color="text.secondary">
                                                {formatFileSize(file.file_size)} • {format(new Date(file.created_at), 'MMM dd, yyyy')}
                                            </Typography>
                                        }
                                    />
                                    <ListItemSecondaryAction>
                                        <Stack direction="row" spacing={1}>
                                            <Tooltip title="View Details">
                                                <IconButton
                                                    size="small"
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleDocumentClick(file)
                                                    }}
                                                >
                                                    <ViewIcon fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                            <Tooltip title="Download">
                                                <IconButton
                                                    size="small"
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        window.open(`/api/v1/files/${file.uuid}/download`, '_blank')
                                                    }}
                                                >
                                                    <DownloadIcon fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                        </Stack>
                                    </ListItemSecondaryAction>
                                </ListItem>
                            ))}
                        </List>
                    </Paper>
                </Box>
            )}

            {folders.length === 0 && files.length === 0 && (
                <Box
                    display="flex"
                    flexDirection="column"
                    alignItems="center"
                    justifyContent="center"
                    py={8}
                >
                    <FolderOpenIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                        This folder is empty
                    </Typography>
                </Box>
            )}

            <DocumentDetailsDrawer
                open={drawerOpen}
                document={selectedDocument}
                onClose={handleCloseDrawer}
                onEdit={() => {
                    onCorpusChanged?.()
                }}
                onDownload={(doc) => {
                    window.open(`/api/v1/files/${doc.uuid}/download`, '_blank')
                }}
                onShare={(doc) => {
                    const shareUrl = `${window.location.origin}/documents/${doc.uuid}`
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        enqueueSnackbar('Share link copied to clipboard', { variant: 'success' })
                    })
                }}
                onDelete={async (doc) => {
                    try {
                        const response = await fetch(`/api/v1/files/${doc.uuid}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                                'Content-Type': 'application/json',
                            },
                        })

                        if (!response.ok) {
                            throw new Error('Delete failed')
                        }

                        enqueueSnackbar(`Removed “${doc.filename}” from inDoc`, { variant: 'success' })
                        handleCloseDrawer()
                        onCorpusChanged?.()
                    } catch (error) {
                        enqueueSnackbar('Failed to delete document', { variant: 'error' })
                        throw error
                    }
                }}
            />

            <Dialog
                open={Boolean(folderToDelete)}
                onClose={() => !deletingFolder && setFolderToDelete(null)}
                maxWidth="sm"
                fullWidth
            >
                <DialogTitle sx={{ fontWeight: 700 }}>Remove folder from inDoc?</DialogTitle>
                <DialogContent>
                    <DialogContentText component="div">
                        Remove <strong>{folderToDelete?.path}</strong> and{' '}
                        <strong>{folderToDelete?.fileCount ?? 0}</strong> document
                        {(folderToDelete?.fileCount ?? 0) === 1 ? '' : 's'} from the inDoc corpus
                        (search, vectors, and stored copies).
                        <Box
                            sx={{
                                mt: 2,
                                p: 1.5,
                                borderRadius: 1.5,
                                bgcolor: (t) =>
                                    t.palette.mode === 'dark' ? 'rgba(56,189,248,0.08)' : 'rgba(2,132,199,0.08)',
                                border: '1px solid',
                                borderColor: 'divider',
                            }}
                        >
                            <Typography variant="body2" sx={{ fontWeight: 650 }}>
                                Your original files on disk are not deleted.
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                This only removes the corpus entries inside inDoc. You can re-upload the folder later.
                            </Typography>
                        </Box>
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2 }}>
                    <Button onClick={() => setFolderToDelete(null)} disabled={deletingFolder}>
                        Cancel
                    </Button>
                    <Button
                        color="error"
                        variant="contained"
                        onClick={handleDeleteFolder}
                        disabled={deletingFolder}
                        startIcon={deletingFolder ? <CircularProgress size={16} color="inherit" /> : <DeleteIcon />}
                    >
                        {deletingFolder ? 'Removing…' : 'Remove from inDoc'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default DocumentFolderView
