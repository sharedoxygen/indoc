import React, { useState } from 'react';
import {
    Box,
    Grid,
    Card,
    CardContent,
    Typography,
    Chip,
    Checkbox,
    CardActions,
} from '@mui/material';

import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import DocumentDetailsDrawer from './DocumentDetailsDrawer';

interface Document {
    uuid: string;
    filename: string;
    title?: string;
    description?: string;
    file_type: string;
    file_size: number;
    created_at: string;
    updated_at?: string;
    folder_path?: string;
    document_set_id?: string;
    status?: string;
    virus_scan_status?: string;
    uploaded_by?: string;
    tags?: string[];
    custom_metadata?: any;
}

interface DocumentsListProps {
    documents: Document[];
    isLoading: boolean;
    selectedDocuments: string[];
    onDocumentSelect: (selected: string[]) => void;
    searchTerm?: string;
}

export const DocumentsList: React.FC<DocumentsListProps> = ({ documents, isLoading, selectedDocuments, onDocumentSelect, searchTerm }) => {
    const navigate = useNavigate();
    const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    // Debug: Log drawer state changes
    React.useEffect(() => {
        console.log('Drawer open state:', drawerOpen, 'Selected document:', selectedDocument?.filename);
    }, [drawerOpen, selectedDocument]);

    const handleDocumentToggle = (docId: string) => {
        const newSelection = selectedDocuments.includes(docId)
            ? selectedDocuments.filter(id => id !== docId)
            : [...selectedDocuments, docId];
        onDocumentSelect(newSelection);
    };

    const handleViewDocument = (docId: string) => {
        navigate(`/document/${docId}`);
    };

    const handleDocumentClick = (document: Document) => {
        console.log('Document clicked:', document.uuid, document.filename);
        setSelectedDocument(document);
        setDrawerOpen(true);
        console.log('Drawer state set to:', true);
    };

    const handleCloseDrawer = () => {
        setDrawerOpen(false);
        setSelectedDocument(null);
    };

    // Server-side search already applied; show the provided documents
    const filteredDocuments = documents;

    return (
        <Box>
            <Grid container spacing={2}>
                {isLoading ? (
                    <Typography>Loading...</Typography>
                ) : (
                    filteredDocuments.map(doc => {
                        const isSelected = selectedDocuments.includes(doc.uuid);
                        return (
                            <Grid item xs={12} sm={6} key={doc.uuid}>
                                <Card
                                    onClick={() => handleDocumentClick(doc)}
                                    sx={{
                                        cursor: 'pointer',
                                        border: isSelected ? 2 : 1,
                                        borderColor: isSelected ? 'primary.main' : 'divider',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        justifyContent: 'space-between',
                                        height: '100%',
                                        transition: 'all 0.2s ease',
                                        '&:hover': {
                                            transform: 'translateY(-2px)',
                                            boxShadow: 4,
                                            borderColor: 'primary.main'
                                        }
                                    }}
                                >
                                    <CardContent sx={{ p: 2 }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                                            <Checkbox
                                                checked={isSelected}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDocumentToggle(doc.uuid);
                                                }}
                                                size="small"
                                                sx={{ p: 0, mr: 1 }}
                                            />
                                            <Typography variant="subtitle1" sx={{ flexGrow: 1, fontSize: '0.875rem', fontWeight: 600 }}>{doc.title || doc.filename}</Typography>
                                            <Chip label={doc.file_type} size="small" variant="outlined" sx={{ fontSize: '0.6875rem' }} />
                                        </Box>
                                        <Typography variant="body2" color="text.secondary" sx={{
                                            mb: 1.5,
                                            fontSize: '0.75rem',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            display: '-webkit-box',
                                            lineHeight: 1.4,
                                            maxHeight: '2.8em'
                                        }}>
                                            {doc.description || 'No description available.'}
                                        </Typography>
                                    </CardContent>
                                    <CardActions sx={{ display: 'flex', justifyContent: 'space-between', px: 2, pb: 1.5 }}>
                                        <Typography variant="caption" sx={{ fontSize: '0.6875rem' }}>
                                            {format(new Date(doc.created_at), 'MMM dd, yyyy')}
                                        </Typography>
                                    </CardActions>
                                </Card>
                            </Grid>
                        );
                    })
                )}
            </Grid>

            <DocumentDetailsDrawer
                open={drawerOpen}
                document={selectedDocument}
                onClose={handleCloseDrawer}
                onEdit={() => {
                    // Refresh after edit (edit happens in modal within drawer)
                    window.location.reload();
                }}
                onDownload={(doc) => {
                    window.open(`/api/v1/files/${doc.uuid}/download`, '_blank');
                }}
                onShare={(doc) => {
                    // Copy share link to clipboard
                    const shareUrl = `${window.location.origin}/documents/${doc.uuid}`;
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        console.log('✅ Share link copied:', shareUrl);
                        alert('Share link copied to clipboard!');
                    });
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
                        });
                        
                        if (!response.ok) {
                            throw new Error('Delete failed');
                        }
                        
                        console.log('✅ Document deleted:', doc.filename);
                        alert('Document deleted successfully!');
                        
                        // Refresh the page or remove from local state
                        window.location.reload();
                    } catch (error) {
                        console.error('❌ Delete failed:', error);
                        alert('Failed to delete document. Please try again.');
                        throw error;
                    }
                }}
            />
        </Box>
    );
};
