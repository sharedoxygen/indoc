import React, { useState } from 'react';
import {
    Paper,
    Box,
    Typography,
    LinearProgress,
    Chip,
    IconButton,
    Collapse,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Avatar,
    Fade,
    Alert,
} from '@mui/material';
import {
    CloudUpload as UploadIcon,
    CheckCircle as CompleteIcon,
    Error as ErrorIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    Close as CloseIcon,
} from '@mui/icons-material';

interface ProcessingStage {
    id: string;
    name: string;
    icon: React.ReactNode;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    message?: string;
    progress?: number;
}

interface DocumentProcessingItem {
    id: string;
    filename: string;
    fileSize: number;
    uploadedAt: Date;
    currentStage: string;
    stages: ProcessingStage[];
    overallStatus: 'processing' | 'completed' | 'failed';
}

interface DocumentProcessingStatusProps {
    documents: DocumentProcessingItem[];
    onClose?: (documentId: string) => void;
    className?: string;
}

const getStageColor = (status: ProcessingStage['status']) => {
    switch (status) {
        case 'completed': return 'success';
        case 'processing': return 'primary';
        case 'failed': return 'error';
        default: return 'default';
    }
};

const getStageIcon = (stage: ProcessingStage) => {
    if (stage.status === 'failed') return <ErrorIcon color="error" />;
    if (stage.status === 'completed') return <CompleteIcon color="success" />;
    return stage.icon;
};

const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const DocumentProcessingItem: React.FC<{
    document: DocumentProcessingItem;
    onClose?: (documentId: string) => void;
}> = ({ document, onClose }) => {
    const [expanded, setExpanded] = useState(true);

    const currentStageIndex = document.stages.findIndex(s => s.id === document.currentStage);
    const progress = ((currentStageIndex + 1) / document.stages.length) * 100;

    const currentStage = document.stages.find(s => s.id === document.currentStage);

    return (
        <Fade in timeout={500}>
            <Paper
                elevation={2}
                sx={{
                    mb: 2,
                    border: document.overallStatus === 'failed' ? '1px solid #f44336' : '1px solid #e0e0e0',
                    borderRadius: 2,
                    overflow: 'hidden',
                }}
            >
                {/* Header */}
                <Box
                    sx={{
                        p: 2,
                        bgcolor: document.overallStatus === 'completed'
                            ? 'success.light'
                            : document.overallStatus === 'failed'
                                ? 'error.light'
                                : 'primary.light',
                        color: document.overallStatus === 'completed'
                            ? 'success.contrastText'
                            : document.overallStatus === 'failed'
                                ? 'error.contrastText'
                                : 'primary.contrastText',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                    }}
                >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ bgcolor: 'rgba(255,255,255,0.2)' }}>
                            {document.overallStatus === 'completed' ? (
                                <CompleteIcon />
                            ) : document.overallStatus === 'failed' ? (
                                <ErrorIcon />
                            ) : (
                                <UploadIcon />
                            )}
                        </Avatar>

                        <Box>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {document.filename}
                            </Typography>
                            <Typography variant="body2" sx={{ opacity: 0.8 }}>
                                {formatFileSize(document.fileSize)} • {document.uploadedAt.toLocaleTimeString()}
                            </Typography>
                        </Box>
                    </Box>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {document.overallStatus === 'processing' && (
                            <Chip
                                label={currentStage?.name || 'Processing...'}
                                size="small"
                                color="secondary"
                                sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'inherit' }}
                            />
                        )}

                        <IconButton
                            size="small"
                            onClick={() => setExpanded(!expanded)}
                            sx={{ color: 'inherit' }}
                        >
                            {expanded ? <CollapseIcon /> : <ExpandIcon />}
                        </IconButton>

                        {onClose && document.overallStatus !== 'processing' && (
                            <IconButton
                                size="small"
                                onClick={() => onClose(document.id)}
                                sx={{ color: 'inherit' }}
                            >
                                <CloseIcon />
                            </IconButton>
                        )}
                    </Box>
                </Box>

                {/* Progress Bar */}
                {document.overallStatus === 'processing' && (
                    <LinearProgress
                        variant={currentStage?.progress ? 'determinate' : 'indeterminate'}
                        value={currentStage?.progress || progress}
                        sx={{
                            height: 4,
                            bgcolor: 'rgba(0,0,0,0.1)',
                            '& .MuiLinearProgress-bar': { bgcolor: 'success.main' }
                        }}
                    />
                )}

                {/* Detailed Status */}
                <Collapse in={expanded}>
                    <Box sx={{ p: 2 }}>
                        {document.overallStatus === 'completed' && (
                            <Alert severity="success" sx={{ mb: 2 }}>
                                Document processed successfully! Ready for search and chat.
                            </Alert>
                        )}

                        {document.overallStatus === 'failed' && (
                            <Alert severity="error" sx={{ mb: 2 }}>
                                Document processing failed. Please try uploading again.
                            </Alert>
                        )}

                        <List dense>
                            {document.stages.map((stage) => (
                                <ListItem
                                    key={stage.id}
                                    sx={{
                                        opacity: stage.status === 'pending' ? 0.5 : 1,
                                        transition: 'opacity 0.3s',
                                    }}
                                >
                                    <ListItemIcon>
                                        {getStageIcon(stage)}
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={stage.name}
                                        secondary={stage.message}
                                    />
                                    <Chip
                                        label={stage.status}
                                        size="small"
                                        color={getStageColor(stage.status)}
                                        variant={stage.status === 'processing' ? 'filled' : 'outlined'}
                                    />
                                </ListItem>
                            ))}
                        </List>
                    </Box>
                </Collapse>
            </Paper>
        </Fade>
    );
};

export const DocumentProcessingStatus: React.FC<DocumentProcessingStatusProps> = ({
    documents,
    onClose,
    className,
}) => {
    if (documents.length === 0) return null;

    return (
        <Box className={className} sx={{ maxHeight: '400px', overflow: 'auto' }}>
            <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <UploadIcon color="primary" />
                Document Processing ({documents.length})
            </Typography>

            {documents.map((doc) => (
                <DocumentProcessingItem
                    key={doc.id}
                    document={doc}
                    onClose={onClose}
                />
            ))}
        </Box>
    );
};

export default DocumentProcessingStatus;
