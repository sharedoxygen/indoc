import React, { useMemo, useState } from 'react'
import { Box, Typography, TextField, InputAdornment, Paper, Chip, CircularProgress, FormControl, InputLabel, Select, MenuItem, ToggleButtonGroup, ToggleButton } from '@mui/material'
import { Search as SearchIcon, ViewModule as GridViewIcon, ViewList as ListViewIcon } from '@mui/icons-material'
import { useGetDocumentsQuery } from '../store/api'
import { DocumentsList } from '../components/DocumentsList'
import DocumentFolderView from '../components/DocumentFolderView'
import { useDebounce } from '../hooks/useDebounce'
import { useNavigate } from 'react-router-dom'

const STATUS_SLIDES = [
    { value: 'indexed', label: 'Ready' },
    { value: 'processing', label: 'Processing' },
    { value: 'uploaded', label: 'Queued' },
    { value: 'failed', label: 'Failed' },
    { value: 'all', label: 'All' },
] as const

const DocumentsPage: React.FC = () => {
    const navigate = useNavigate()
    const [search, setSearch] = useState('')
    const [fileType, setFileType] = useState<'all' | string>('all')
    const [statusFilter, setStatusFilter] = useState<string>('indexed')
    const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'filename' | 'file_type' | 'file_size'>('created_at')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
    const [viewMode, setViewMode] = useState<'folder' | 'list'>('folder')

    const debouncedSearch = useDebounce(search, 300)

    const { data, isLoading } = useGetDocumentsQuery({
        skip: 0,
        limit: 100,
        search: debouncedSearch || undefined,
        status: statusFilter === 'all' ? undefined : statusFilter,
        file_type: fileType === 'all' ? undefined : fileType,
        sort_by: sortBy,
        sort_order: sortOrder
    }, {
        refetchOnMountOrArgChange: true,
        refetchOnFocus: false
    })
    const indexedDocuments = useMemo(() => {
        const docs = data?.documents || []
        return docs
    }, [data])

    return (
        <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, mb: 2 }}>Documents</Typography>
            <Paper sx={{ p: 2, borderRadius: 3, mb: 3 }}>
                <TextField
                    fullWidth
                    placeholder="Search documents..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    InputProps={{ startAdornment: (<InputAdornment position="start"><SearchIcon /></InputAdornment>) }}
                />
                <Box sx={{ mt: 1.5, mb: 1 }}>
                    <ToggleButtonGroup
                        exclusive
                        size="small"
                        value={statusFilter}
                        onChange={(_, v) => v && setStatusFilter(v)}
                        sx={{ flexWrap: 'wrap' }}
                    >
                        {STATUS_SLIDES.map((s) => (
                            <ToggleButton key={s.value} value={s.value}>
                                {s.label}
                            </ToggleButton>
                        ))}
                    </ToggleButtonGroup>
                </Box>
                <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
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
                </Box>
                <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        <Chip label={`${data?.total ?? indexedDocuments.length} results`} size="small" />
                        {data?.total && data?.total > indexedDocuments.length && (
                            <Chip label={`showing ${indexedDocuments.length}`} color="default" size="small" />
                        )}
                    </Box>
                    <ToggleButtonGroup
                        value={viewMode}
                        exclusive
                        onChange={(_e, newMode) => newMode && setViewMode(newMode)}
                        size="small"
                    >
                        <ToggleButton value="folder">
                            <GridViewIcon fontSize="small" sx={{ mr: 0.5 }} />
                            Folders
                        </ToggleButton>
                        <ToggleButton value="list">
                            <ListViewIcon fontSize="small" sx={{ mr: 0.5 }} />
                            List
                        </ToggleButton>
                    </ToggleButtonGroup>
                </Box>
            </Paper>

            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                    <CircularProgress />
                </Box>
            ) : viewMode === 'folder' ? (
                <DocumentFolderView
                    documents={indexedDocuments}
                    onDocumentView={(docId) => navigate(`/document/${docId}`)}
                    selectedDocuments={[]}
                />
            ) : (
                <DocumentsList
                    documents={indexedDocuments}
                    isLoading={isLoading}
                    selectedDocuments={[]}
                    onDocumentSelect={() => { }}
                    searchTerm={search}
                />
            )}
        </Box>
    )
}

export default DocumentsPage


