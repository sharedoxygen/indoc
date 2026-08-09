import React, { useMemo, useState } from 'react';
import {
    Box,
    Typography,
    TextField,
    InputAdornment,
    Paper,
    Chip,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Button,
    Checkbox,
    Stack,
    Fab,
    Badge,
    alpha,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TableSortLabel,
    IconButton,
    Tooltip
} from '@mui/material';
import {
    Search as SearchIcon,
    Share as ShareIcon,
    SelectAll as SelectAllIcon,
    Description as FileIcon,
    GetApp as DownloadIcon,
    Visibility as PreviewIcon
} from '@mui/icons-material';
import { useGetDocumentsQuery } from '../store/api';
import { DocumentsList } from '../components/DocumentsList';
import { useDebounce } from '../hooks/useDebounce';
import DocumentAccessManager from './DocumentAccessManager';
import { useSnackbar } from 'notistack';

interface Document {
    id: number;
    uuid: string;
    filename: string;
    title: string;
    file_type: string;
    file_size: number;
    status: string;
    created_at: string;
    uploaded_by: number;
}

const DocumentsPageEnhanced: React.FC = () => {
    const [search, setSearch] = useState('');
    const [fileType, setFileType] = useState<'all' | string>('all');
    const [sortBy, setSortBy] = useState<'created_at' | 'filename'>('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [selectedDocs, setSelectedDocs] = useState<Set<number>>(new Set());
    const [shareDialogOpen, setShareDialogOpen] = useState(false);
    const { enqueueSnackbar } = useSnackbar();

    const debouncedSearch = useDebounce(search, 300);

    const { data, isLoading, refetch } = useGetDocumentsQuery({
        skip: 0,
        limit: 1000,
        search: debouncedSearch || undefined,
        status: 'indexed',
        file_type: fileType === 'all' ? undefined : fileType,
        sort_by: sortBy,
        sort_order: sortOrder
    });

    const indexedDocuments = useMemo(() => {
        return (data?.documents || []).filter((d: any) => d.status === 'indexed');
    }, [data]);

    const selectedDocuments = useMemo(() => {
        return indexedDocuments.filter((doc: any) => selectedDocs.has(doc.id));
    }, [indexedDocuments, selectedDocs]);

    const handleToggleSelect = (docId: number) => {
        setSelectedDocs(prev => {
            const newSet = new Set(prev);
            if (newSet.has(docId)) {
                newSet.delete(docId);
            } else {
                newSet.add(docId);
            }
            return newSet;
        });
    };

    const handleSelectAll = () => {
        if (selectedDocs.size === indexedDocuments.length) {
            setSelectedDocs(new Set());
        } else {
            setSelectedDocs(new Set(indexedDocuments.map((d: any) => d.id)));
        }
    };

    const handleShareClick = () => {
        setShareDialogOpen(true);
    };

    const handlePreviewDocument = async (doc: any) => {
        try {
            // Detect theme
            const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

            // Theme colors
            const theme = {
                backdrop: isDark ? 'rgba(0,0,0,0.9)' : 'rgba(0,0,0,0.7)',
                background: isDark ? '#2b2b2b' : '#ffffff',
                headerBg: isDark ? '#1e1e1e' : '#f5f5f5',
                border: isDark ? '#3a3a3a' : '#e0e0e0',
                textPrimary: isDark ? '#e0e0e0' : '#2c3e50',
                textSecondary: isDark ? '#999' : '#666',
                buttonBg: isDark ? '#3a3a3a' : '#f0f0f0',
                buttonHoverBg: isDark ? '#4a4a4a' : '#e0e0e0',
                loadingBg: isDark ? '#1a1a1a' : '#f8f8f8',
                spinnerBorder: isDark ? '#3a3a3a' : '#e0e0e0',
                spinnerTop: '#2196f3'
            };

            // Create preview modal
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: ${theme.backdrop};
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                box-sizing: border-box;
                animation: fadeIn 0.2s ease-in;
            `;

            const content = document.createElement('div');
            content.style.cssText = `
                background: ${theme.background};
                border-radius: 12px;
                width: 95%;
                max-width: 1400px;
                height: 90vh;
                overflow: hidden;
                position: relative;
                box-shadow: 0 20px 60px rgba(0,0,0,${isDark ? '0.5' : '0.3'});
                display: flex;
                flex-direction: column;
            `;

            // Header
            const header = document.createElement('div');
            header.style.cssText = `
                padding: 16px 24px;
                background: ${theme.headerBg};
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid ${theme.border};
            `;

            const titleSection = document.createElement('div');
            titleSection.style.cssText = `
                display: flex;
                align-items: center;
                gap: 12px;
                flex: 1;
            `;

            const fileIcon = document.createElement('span');
            fileIcon.textContent = '📄';
            fileIcon.style.fontSize = '24px';

            const title = document.createElement('h3');
            title.textContent = doc.filename || doc.title;
            title.style.cssText = `
                margin: 0;
                font-size: 16px;
                font-weight: 500;
                color: ${theme.textPrimary};
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            `;

            const buttonGroup = document.createElement('div');
            buttonGroup.style.cssText = `
                display: flex;
                gap: 8px;
                align-items: center;
            `;

            const downloadBtn = document.createElement('button');
            downloadBtn.innerHTML = '⬇ Download';
            downloadBtn.style.cssText = `
                background: #2196f3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: background 0.2s;
            `;
            downloadBtn.onmouseover = () => downloadBtn.style.background = '#1976d2';
            downloadBtn.onmouseout = () => downloadBtn.style.background = '#2196f3';
            downloadBtn.onclick = () => handleDownloadDocument(doc);

            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '✕';
            closeBtn.style.cssText = `
                background: none;
                border: none;
                color: ${theme.textSecondary};
                font-size: 24px;
                cursor: pointer;
                padding: 4px 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 6px;
                transition: all 0.2s;
            `;
            closeBtn.onmouseover = () => {
                closeBtn.style.background = theme.buttonHoverBg;
                closeBtn.style.color = theme.textPrimary;
            };
            closeBtn.onmouseout = () => {
                closeBtn.style.background = 'none';
                closeBtn.style.color = theme.textSecondary;
            };

            titleSection.appendChild(fileIcon);
            titleSection.appendChild(title);
            buttonGroup.appendChild(downloadBtn);
            buttonGroup.appendChild(closeBtn);
            header.appendChild(titleSection);
            header.appendChild(buttonGroup);

            // Loading spinner
            const loadingDiv = document.createElement('div');
            loadingDiv.style.cssText = `
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: ${theme.textPrimary};
                font-size: 16px;
                gap: 16px;
                background: ${theme.loadingBg};
            `;

            const spinner = document.createElement('div');
            spinner.style.cssText = `
                width: 48px;
                height: 48px;
                border: 4px solid ${theme.spinnerBorder};
                border-top-color: ${theme.spinnerTop};
                border-radius: 50%;
                animation: spin 1s linear infinite;
            `;

            const loadingText = document.createElement('div');
            loadingText.textContent = 'Loading document...';
            loadingText.style.cssText = `
                font-size: 14px;
                color: ${theme.textSecondary};
            `;

            loadingDiv.appendChild(spinner);
            loadingDiv.appendChild(loadingText);

            content.appendChild(header);
            content.appendChild(loadingDiv);
            modal.appendChild(content);

            // Add CSS animation
            const style = document.createElement('style');
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);

            // Close handlers
            const cleanup = () => {
                if (modal.parentNode) {
                    modal.style.animation = 'fadeOut 0.2s ease-out';
                    setTimeout(() => {
                        if (modal.parentNode) {
                            document.body.removeChild(modal);
                        }
                        document.head.removeChild(style);
                    }, 200);
                }
            };

            closeBtn.onclick = cleanup;
            modal.onclick = (e) => {
                if (e.target === modal) {
                    cleanup();
                }
            };

            // ESC key to close
            const escHandler = (e: KeyboardEvent) => {
                if (e.key === 'Escape') {
                    cleanup();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);

            document.body.appendChild(modal);

            // Fetch and display document
            const token = localStorage.getItem('token');
            const response = await fetch(`http://localhost:8001/api/v1/files/preview/${doc.uuid}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': '*/*'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const blob = await response.blob();

            // Convert blob to base64 data URL (works in all browsers)
            const arrayBuffer = await blob.arrayBuffer();
            const bytes = new Uint8Array(arrayBuffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            const base64 = btoa(binary);
            const dataUrl = `data:application/pdf;base64,${base64}`;

            // Create embedded PDF viewer
            const viewerContainer = document.createElement('div');
            viewerContainer.style.cssText = `
                flex: 1;
                background: ${theme.loadingBg};
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                position: relative;
            `;

            // Create object element with data URL (more compatible than iframe)
            const pdfObject = document.createElement('object');
            pdfObject.data = dataUrl;
            pdfObject.type = 'application/pdf';
            pdfObject.style.cssText = `
                width: 100%;
                height: 100%;
                border: none;
            `;

            // Fallback content if PDF can't be displayed
            const fallback = document.createElement('div');
            fallback.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
                padding: 40px;
                max-width: 500px;
            `;

            const fallbackIcon = document.createElement('div');
            fallbackIcon.textContent = '📄';
            fallbackIcon.style.cssText = `
                font-size: 64px;
                margin-bottom: 20px;
                opacity: 0.6;
            `;

            const fallbackTitle = document.createElement('div');
            fallbackTitle.textContent = 'PDF Viewer Not Available';
            fallbackTitle.style.cssText = `
                font-size: 18px;
                font-weight: 500;
                color: ${theme.textPrimary};
                margin-bottom: 12px;
            `;

            const fallbackDesc = document.createElement('div');
            fallbackDesc.textContent = 'Your browser cannot display PDFs inline. Download the file to view it.';
            fallbackDesc.style.cssText = `
                font-size: 14px;
                color: ${theme.textSecondary};
                margin-bottom: 24px;
                line-height: 1.5;
            `;

            const fallbackBtn = document.createElement('button');
            fallbackBtn.innerHTML = '⬇ Download Document';
            fallbackBtn.style.cssText = `
                background: #2196f3;
                color: white;
                border: none;
                padding: 12px 32px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                font-weight: 500;
                transition: all 0.2s;
                box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
            `;
            fallbackBtn.onmouseover = () => {
                fallbackBtn.style.background = '#1976d2';
                fallbackBtn.style.transform = 'translateY(-1px)';
            };
            fallbackBtn.onmouseout = () => {
                fallbackBtn.style.background = '#2196f3';
                fallbackBtn.style.transform = 'translateY(0)';
            };
            fallbackBtn.onclick = () => {
                const link = document.createElement('a');
                link.href = dataUrl;
                link.download = doc.filename || doc.title;
                link.click();
                enqueueSnackbar('Download started', { variant: 'success' });
            };

            fallback.appendChild(fallbackIcon);
            fallback.appendChild(fallbackTitle);
            fallback.appendChild(fallbackDesc);
            fallback.appendChild(fallbackBtn);

            pdfObject.appendChild(fallback);
            viewerContainer.appendChild(pdfObject);

            // Replace loading with PDF viewer
            content.replaceChild(viewerContainer, loadingDiv);

        } catch (error) {
            console.error('Preview failed:', error);
            enqueueSnackbar('Failed to load document preview', { variant: 'error' });
        }
    };

    const handleDownloadDocument = async (doc: any) => {
        try {
            // Fetch document with authentication
            const token = localStorage.getItem('token');
            const response = await fetch(`http://localhost:8001/api/v1/files/download/${doc.uuid}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': '*/*'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);

            // Create a temporary link for download
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = doc.filename || doc.title;
            link.style.display = 'none';

            // Add to DOM, click, then remove
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Cleanup blob URL
            URL.revokeObjectURL(blobUrl);

            // Show success message
            enqueueSnackbar(`Downloading ${doc.filename || doc.title}`, {
                variant: 'success',
                autoHideDuration: 2000
            });

        } catch (error) {
            console.error('Download failed:', error);
            enqueueSnackbar('Download failed. Please try again.', {
                variant: 'error'
            });
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const getFileIcon = (fileType: string) => {
        switch (fileType.toLowerCase()) {
            case 'pdf': return '📄';
            case 'docx': return '📝';
            case 'xlsx': return '📊';
            case 'pptx': return '📋';
            case 'txt': return '📃';
            default: return '📄';
        }
    };

    return (
        <Box sx={{ position: 'relative' }}>
            {/* Header */}
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    Documents
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                    {selectedDocs.size > 0 && (
                        <Button
                            variant="outlined"
                            onClick={() => setSelectedDocs(new Set())}
                            size="small"
                        >
                            Clear Selection ({selectedDocs.size})
                        </Button>
                    )}
                </Stack>
            </Stack>

            {/* Controls */}
            <Paper sx={{ p: 2, borderRadius: 2, mb: 2 }}>
                <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                    <TextField
                        placeholder="Search documents..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        size="small"
                        sx={{ minWidth: 250 }}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon />
                                </InputAdornment>
                            )
                        }}
                    />
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Type</InputLabel>
                        <Select
                            label="Type"
                            value={fileType}
                            onChange={(e) => setFileType(e.target.value as any)}
                        >
                            <MenuItem value="all">All Types</MenuItem>
                            <MenuItem value="pdf">PDF</MenuItem>
                            <MenuItem value="txt">TXT</MenuItem>
                            <MenuItem value="docx">DOCX</MenuItem>
                            <MenuItem value="pptx">PPTX</MenuItem>
                            <MenuItem value="xlsx">XLSX</MenuItem>
                        </Select>
                    </FormControl>
                    <Button
                        variant="outlined"
                        size="small"
                        startIcon={<SelectAllIcon />}
                        onClick={handleSelectAll}
                    >
                        {selectedDocs.size === indexedDocuments.length ? 'Deselect All' : 'Select All'}
                    </Button>
                    {selectedDocs.size > 0 && (
                        <Chip
                            label={`${selectedDocs.size} selected`}
                            color="primary"
                            size="small"
                        />
                    )}
                </Stack>
            </Paper>

            {/* Documents Table */}
            <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
                <Table size="small" sx={{ minWidth: 650 }}>
                    <TableHead>
                        <TableRow sx={{ bgcolor: 'grey.50' }}>
                            <TableCell padding="checkbox">
                                <Checkbox
                                    indeterminate={selectedDocs.size > 0 && selectedDocs.size < indexedDocuments.length}
                                    checked={indexedDocuments.length > 0 && selectedDocs.size === indexedDocuments.length}
                                    onChange={handleSelectAll}
                                    size="small"
                                />
                            </TableCell>
                            <TableCell>
                                <TableSortLabel
                                    active={sortBy === 'filename'}
                                    direction={sortBy === 'filename' ? sortOrder : 'asc'}
                                    onClick={() => {
                                        setSortBy('filename');
                                        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                                    }}
                                >
                                    Name
                                </TableSortLabel>
                            </TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell align="right">Size</TableCell>
                            <TableCell align="right">
                                <TableSortLabel
                                    active={sortBy === 'created_at'}
                                    direction={sortBy === 'created_at' ? sortOrder : 'asc'}
                                    onClick={() => {
                                        setSortBy('created_at');
                                        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                                    }}
                                >
                                    Date
                                </TableSortLabel>
                            </TableCell>
                            <TableCell align="center">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {indexedDocuments.map((doc: any) => (
                            <TableRow
                                key={doc.id}
                                hover
                                selected={selectedDocs.has(doc.id)}
                                sx={{
                                    '&:last-child td, &:last-child th': { border: 0 },
                                    cursor: 'pointer',
                                    '&.Mui-selected': {
                                        bgcolor: alpha('#2196f3', 0.08)
                                    }
                                }}
                            >
                                <TableCell padding="checkbox">
                                    <Checkbox
                                        checked={selectedDocs.has(doc.id)}
                                        onChange={() => handleToggleSelect(doc.id)}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>
                                    <Stack direction="row" spacing={1} alignItems="center">
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                            {getFileIcon(doc.file_type)}
                                        </Typography>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                            {doc.title || doc.filename}
                                        </Typography>
                                    </Stack>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={doc.file_type.toUpperCase()}
                                        size="small"
                                        variant="outlined"
                                        sx={{
                                            fontSize: '0.75rem',
                                            height: 20,
                                            minWidth: 50,
                                            textAlign: 'center'
                                        }}
                                    />
                                </TableCell>
                                <TableCell align="right">
                                    <Typography variant="body2" color="text.secondary">
                                        {formatFileSize(doc.file_size)}
                                    </Typography>
                                </TableCell>
                                <TableCell align="right">
                                    <Typography variant="body2" color="text.secondary">
                                        {new Date(doc.created_at).toLocaleDateString('en-US', {
                                            month: 'short',
                                            day: 'numeric',
                                            year: 'numeric'
                                        })}
                                    </Typography>
                                </TableCell>
                                <TableCell align="center">
                                    <Stack direction="row" spacing={0.5} justifyContent="center">
                                        <Tooltip title="Preview">
                                            <IconButton
                                                size="small"
                                                color="primary"
                                                onClick={() => handlePreviewDocument(doc)}
                                            >
                                                <PreviewIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title="Download">
                                            <IconButton
                                                size="small"
                                                color="primary"
                                                onClick={() => handleDownloadDocument(doc)}
                                            >
                                                <DownloadIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </Stack>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Empty State */}
            {indexedDocuments.length === 0 && !isLoading && (
                <Box textAlign="center" py={8}>
                    <FileIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                        No documents found
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {search || fileType !== 'all'
                            ? 'Try adjusting your search or filter criteria.'
                            : 'Upload some documents to get started.'
                        }
                    </Typography>
                </Box>
            )}

            {/* Floating Share Button */}
            {selectedDocs.size > 0 && (
                <Fab
                    color="primary"
                    sx={{
                        position: 'fixed',
                        bottom: 24,
                        right: 24,
                        width: 64,
                        height: 64,
                        boxShadow: '0 6px 20px rgba(33, 150, 243, 0.3)'
                    }}
                    onClick={handleShareClick}
                >
                    <Badge badgeContent={selectedDocs.size} color="error" max={99}>
                        <ShareIcon />
                    </Badge>
                </Fab>
            )}

            {/* Access Manager Dialog */}
            <DocumentAccessManager
                open={shareDialogOpen}
                onClose={() => setShareDialogOpen(false)}
                selectedDocuments={selectedDocuments}
                onSuccess={() => {
                    setSelectedDocs(new Set());
                    refetch();
                }}
            />
        </Box>
    );
};

export default DocumentsPageEnhanced;

