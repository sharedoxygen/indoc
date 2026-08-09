import React, { useState, useMemo } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Box,
    Typography,
    TextField,
    InputAdornment,
    Chip,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Checkbox,
    IconButton,
    Tooltip,
    CircularProgress,
    Alert,
    Pagination,
    ToggleButtonGroup,
    ToggleButton
} from '@mui/material';
import {
    Search as SearchIcon,
    Close as CloseIcon,
    Delete as DeleteIcon,
    Download as DownloadIcon,
    Visibility as ViewIcon,
    Refresh as RefreshIcon,
    ViewModule as GridViewIcon,
    ViewList as ListViewIcon
} from '@mui/icons-material';
import { useGetDocumentsQuery, useDeleteDocumentMutation } from '../store/api';
import { useDebounce } from '../hooks/useDebounce';

interface BulkDocumentModalProps {
    open: boolean;
    onClose: () => void;
    title?: string;
    maxHeight?: string;
}

const BulkDocumentModal: React.FC<BulkDocumentModalProps> = ({
    open,
    onClose,
    title = "Manage Documents",
    maxHeight = "80vh"
}) => {
    const [search, setSearch] = useState('');
    const [fileType, setFileType] = useState<'all' | string>('all');
    const [documentSet, setDocumentSet] = useState('');
    const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'filename' | 'file_type' | 'file_size'>('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);
    const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);

    const debouncedSearch = useDebounce(search, 300);

    const { data, isLoading, refetch } = useGetDocumentsQuery({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        search: debouncedSearch || undefined,
        status: 'indexed',
        file_type: fileType === 'all' ? undefined : fileType,
        document_set: documentSet || undefined,
        sort_by: sortBy,
        sort_order: sortOrder
    });

    const [deleteDocument] = useDeleteDocumentMutation();

    const documents = data?.documents || [];
    const totalPages = Math.ceil((data?.total || 0) / pageSize);

    // Reset page when filters change
    React.useEffect(() => {
        setPage(1);
    }, [debouncedSearch, fileType, documentSet, sortBy, sortOrder]);

    const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
        setPage(value);
    };

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedDocuments(documents.map((doc: any) => doc.uuid || doc.id));
        } else {
            setSelectedDocuments([]);
        }
    };

    const handleSelectDocument = (docId: string, checked: boolean) => {
        if (checked) {
            setSelectedDocuments(prev => [...prev, docId]);
        } else {
            setSelectedDocuments(prev => prev.filter(id => id !== docId));
        }
    };

    const handleBulkDelete = async () => {
        if (selectedDocuments.length === 0) return;

        try {
            for (const docId of selectedDocuments) {
                await deleteDocument(docId).unwrap();
            }
            setSelectedDocuments([]);
            refetch();
        } catch (error) {
            console.error('Bulk delete failed:', error);
        }
    };

    const isAllSelected = documents.length > 0 && selectedDocuments.length === documents.length;
    const isIndeterminate = selectedDocuments.length > 0 && selectedDocuments.length < documents.length;

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: { maxHeight }
            }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="h6" component="div">
                    {title}
                </Typography>
                <IconButton onClick={onClose} size="small">
                    <CloseIcon />
                </IconButton>
            </DialogTitle>

            <DialogContent dividers>
                {/* Filters */}
                <Box sx={{ mb: 3 }}>
                    <TextField
                        fullWidth
                        placeholder="Search documents..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        size="small"
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon />
                                </InputAdornment>
                            )
                        }}
                        sx={{ mb: 2 }}
                    />

                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
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
                            <InputLabel>Document Set</InputLabel>
                            <Select label="Document Set" value={documentSet} onChange={(e) => setDocumentSet(e.target.value)}>
                                <MenuItem value="">All Sets</MenuItem>
                                <MenuItem value="ZX10R-2024">ZX10R-2024</MenuItem>
                                <MenuItem value="project-alpha">project-alpha</MenuItem>
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

                        <FormControl size="small" sx={{ minWidth: 80 }}>
                            <InputLabel>Per Page</InputLabel>
                            <Select
                                label="Per Page"
                                value={pageSize}
                                onChange={(e) => {
                                    setPageSize(Number(e.target.value));
                                    setPage(1);
                                }}
                            >
                                <MenuItem value={10}>10</MenuItem>
                                <MenuItem value={25}>25</MenuItem>
                                <MenuItem value={50}>50</MenuItem>
                                <MenuItem value={100}>100</MenuItem>
                            </Select>
                        </FormControl>

                        <Button
                            variant="outlined"
                            size="small"
                            startIcon={<RefreshIcon />}
                            onClick={() => refetch()}
                            sx={{ textTransform: 'none' }}
                        >
                            Refresh
                        </Button>
                    </Box>
                </Box>

                {/* Status Bar */}
                <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Chip label={`${data?.total ?? 0} total documents`} size="small" />
                    <Chip label={`Page ${page} of ${totalPages}`} color="primary" size="small" />
                    {selectedDocuments.length > 0 && (
                        <Chip
                            label={`${selectedDocuments.length} selected`}
                            color="secondary"
                            size="small"
                            onDelete={() => setSelectedDocuments([])}
                        />
                    )}
                </Box>

                {/* Document List */}
                {isLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                        <CircularProgress />
                    </Box>
                ) : documents.length === 0 ? (
                    <Alert severity="info">
                        No documents found matching your criteria.
                    </Alert>
                ) : (
                    <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell padding="checkbox">
                                        <Checkbox
                                            checked={isAllSelected}
                                            indeterminate={isIndeterminate}
                                            onChange={(e) => handleSelectAll(e.target.checked)}
                                        />
                                    </TableCell>
                                    <TableCell>Filename</TableCell>
                                    <TableCell>Type</TableCell>
                                    <TableCell>Size</TableCell>
                                    <TableCell>Created</TableCell>
                                    <TableCell>Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {documents.map((doc: any) => (
                                    <TableRow key={doc.uuid || doc.id} hover>
                                        <TableCell padding="checkbox">
                                            <Checkbox
                                                checked={selectedDocuments.includes(doc.uuid || doc.id)}
                                                onChange={(e) => handleSelectDocument(doc.uuid || doc.id, e.target.checked)}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                                {doc.filename}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={doc.file_type?.toUpperCase() || 'UNKNOWN'}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" color="text.secondary">
                                                {((doc.file_size || 0) / 1024 / 1024).toFixed(2)} MB
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" color="text.secondary">
                                                {new Date(doc.created_at).toLocaleDateString()}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                                                <Tooltip title="View Document">
                                                    <IconButton size="small">
                                                        <ViewIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Delete Document">
                                                    <IconButton
                                                        size="small"
                                                        onClick={() => {
                                                            if (window.confirm(`Delete ${doc.filename}?`)) {
                                                                deleteDocument(doc.uuid || doc.id);
                                                            }
                                                        }}
                                                    >
                                                        <DeleteIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                        <Pagination
                            count={totalPages}
                            page={page}
                            onChange={handlePageChange}
                            color="primary"
                            size="small"
                            showFirstButton
                            showLastButton
                        />
                    </Box>
                )}
            </DialogContent>

            <DialogActions>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flex: 1 }}>
                    {selectedDocuments.length > 0 && (
                        <Button
                            variant="contained"
                            color="error"
                            startIcon={<DeleteIcon />}
                            onClick={handleBulkDelete}
                            disabled={isLoading}
                        >
                            Delete Selected ({selectedDocuments.length})
                        </Button>
                    )}
                </Box>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
};

export default BulkDocumentModal;
