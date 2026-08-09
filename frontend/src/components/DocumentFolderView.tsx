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
    MoreVert as MoreIcon,
    Download as DownloadIcon,
    Visibility as ViewIcon,
    Delete as DeleteIcon,
} from '@mui/icons-material'
import { format } from 'date-fns'
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
}

const DocumentFolderView: React.FC<DocumentFolderViewProps> = ({
    documents,
    onDocumentSelect,
    onDocumentView,
    selectedDocuments = []
}) => {
    const [currentPath, setCurrentPath] = useState<string[]>([])
    const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
    const [drawerOpen, setDrawerOpen] = useState(false)

    const handleDocumentClick = (doc: Document) => {
        console.log('Folder view - Document clicked:', doc.uuid, doc.filename)
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

            // Navigate/create folder structure
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

            // Add file to final folder
            current.files.push(doc)
            current.totalSize += doc.file_size
            current.fileCount += 1

            // Update parent folder stats
            let parent = root
            parts.forEach(part => {
                parent.totalSize += doc.file_size
                parent.fileCount += 1
                parent = parent.subfolders.get(part)!
            })
        })

        return root
    }, [documents])

    // Get current folder
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
            {/* Breadcrumb Navigation */}
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

            {/* Folders Grid */}
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
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        '&:hover': {
                                            transform: 'translateY(-4px)',
                                            boxShadow: 4
                                        }
                                    }}
                                >
                                    <CardActionArea onClick={() => handleFolderClick(folder.name)}>
                                        <CardContent>
                                            <Stack direction="row" spacing={2} alignItems="center">
                                                <FolderIcon
                                                    sx={{
                                                        fontSize: 48,
                                                        color: 'primary.main'
                                                    }}
                                                />
                                                <Box flex={1}>
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
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            )}

            {/* Files List */}
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

            {/* Empty State */}
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
                    // Refresh after edit (edit happens in modal within drawer)
                    window.location.reload()
                }}
                onDownload={(doc) => {
                    window.open(`/api/v1/files/${doc.uuid}/download`, '_blank')
                }}
                onShare={(doc) => {
                    // Copy share link to clipboard
                    const shareUrl = `${window.location.origin}/documents/${doc.uuid}`
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        console.log('✅ Share link copied:', shareUrl)
                        // Show success notification if snackbar is available
                        alert('Share link copied to clipboard!')
                    })
                }}
                onDelete={async (doc) => {
                    // Delete document via API
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
                        
                        console.log('✅ Document deleted:', doc.filename)
                        alert('Document deleted successfully!')
                        
                        // Refresh the page or remove from local state
                        window.location.reload()
                    } catch (error) {
                        console.error('❌ Delete failed:', error)
                        alert('Failed to delete document. Please try again.')
                        throw error
                    }
                }}
            />
        </Box>
    )
}

export default DocumentFolderView


