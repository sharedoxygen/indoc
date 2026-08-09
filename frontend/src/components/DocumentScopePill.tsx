import React, { useState } from 'react'
import {
    Box,
    Chip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Checkbox,
    TextField,
    Typography,
    Stack,
    Divider,
} from '@mui/material'
import {
    FilterList as FilterIcon,
    Description as DocumentIcon,
    Search as SearchIcon,
} from '@mui/icons-material'

interface Document {
    id: string
    uuid: string
    filename: string
    file_type: string
    created_at: string
}

interface DocumentScopePillProps {
    selectedDocuments: Document[]
    onSelectionChange: (documents: Document[]) => void
    allDocuments: Document[]
}

const DocumentScopePill: React.FC<DocumentScopePillProps> = ({
    selectedDocuments,
    onSelectionChange,
    allDocuments,
}) => {
    const [open, setOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')

    const handleOpen = () => setOpen(true)
    const handleClose = () => setOpen(false)

    const handleToggleDocument = (doc: Document) => {
        const isSelected = selectedDocuments.some(d => d.uuid === doc.uuid)
        if (isSelected) {
            onSelectionChange(selectedDocuments.filter(d => d.uuid !== doc.uuid))
        } else {
            onSelectionChange([...selectedDocuments, doc])
        }
    }

    const handleSelectAll = () => {
        onSelectionChange(filteredDocuments)
    }

    const handleClearSelection = () => {
        onSelectionChange([])
    }

    const filteredDocuments = allDocuments.filter(doc =>
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
    )

    const scopeLabel = selectedDocuments.length === 0
        ? 'All Accessible Documents'
        : `${selectedDocuments.length} Selected`

    return (
        <>
            <Box sx={{ mb: 2 }}>
                <Chip
                    icon={<FilterIcon />}
                    label={scopeLabel}
                    onClick={handleOpen}
                    color={selectedDocuments.length > 0 ? 'primary' : 'default'}
                    variant={selectedDocuments.length > 0 ? 'filled' : 'outlined'}
                    sx={{
                        fontWeight: 500,
                        cursor: 'pointer',
                        '&:hover': {
                            backgroundColor: selectedDocuments.length > 0 ? 'primary.dark' : 'action.hover',
                        },
                    }}
                />
                {selectedDocuments.length > 0 && (
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                        Query will be limited to selected documents
                    </Typography>
                )}
            </Box>

            <Dialog
                open={open}
                onClose={handleClose}
                maxWidth="sm"
                fullWidth
                PaperProps={{
                    sx: { height: '70vh' }
                }}
            >
                <DialogTitle>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="h6">Select Document Scope</Typography>
                        <Stack direction="row" spacing={1}>
                            <Button size="small" onClick={handleSelectAll}>
                                Select All
                            </Button>
                            <Button size="small" onClick={handleClearSelection} disabled={selectedDocuments.length === 0}>
                                Clear
                            </Button>
                        </Stack>
                    </Stack>
                </DialogTitle>
                <Divider />
                <DialogContent>
                    <TextField
                        fullWidth
                        placeholder="Search documents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        InputProps={{
                            startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                        }}
                        sx={{ mb: 2 }}
                    />

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {filteredDocuments.length} documents available
                    </Typography>

                    <List sx={{ maxHeight: 400, overflow: 'auto' }}>
                        {filteredDocuments.map((doc) => {
                            const isSelected = selectedDocuments.some(d => d.uuid === doc.uuid)
                            return (
                                <ListItem key={doc.uuid} disablePadding>
                                    <ListItemButton
                                        onClick={() => handleToggleDocument(doc)}
                                        dense
                                    >
                                        <ListItemIcon>
                                            <Checkbox
                                                edge="start"
                                                checked={isSelected}
                                                tabIndex={-1}
                                                disableRipple
                                            />
                                        </ListItemIcon>
                                        <ListItemIcon sx={{ minWidth: 40 }}>
                                            <DocumentIcon />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={doc.filename}
                                            secondary={`Type: ${doc.file_type} • ${new Date(doc.created_at).toLocaleDateString()}`}
                                            primaryTypographyProps={{ noWrap: true }}
                                        />
                                    </ListItemButton>
                                </ListItem>
                            )
                        })}
                    </List>
                </DialogContent>
                <Divider />
                <DialogActions>
                    <Button onClick={handleClose}>Close</Button>
                    <Button onClick={handleClose} variant="contained">
                        Apply ({selectedDocuments.length})
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    )
}

export default DocumentScopePill




