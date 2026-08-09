import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Typography,
    LinearProgress,
    Chip,
    Avatar,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    Card,
    CardContent,
    IconButton,
    Collapse,
    Badge,
    Tooltip,
    CircularProgress
} from '@mui/material';
import {
    CloudUpload as UploadIcon,
    Security as VirusIcon,
    TextSnippet as ExtractIcon,
    Search as ElasticsearchIcon,
    Psychology as QdrantIcon,
    Storage as PostgresIcon,
    CheckCircle as CompleteIcon,
    Error as ErrorIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    PlayArrow as ProcessingIcon
} from '@mui/icons-material';
import { keyframes } from '@mui/system';

// Remove pulse keyframes definition

const slideIn = keyframes`
  0% { transform: translateX(-20px); opacity: 0; }
  100% { transform: translateX(0); opacity: 1; }
`;

interface ProcessingStep {
    id: string;
    label: string;
    icon: React.ReactElement;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    message?: string;
    duration?: number;
    details?: string[];
}

interface DocumentProcessingState {
    documentId: string;
    filename: string;
    fileType: string;
    fileSize: number;
    status: 'uploaded' | 'processing' | 'indexed' | 'failed';
    currentStep: string;
    steps: ProcessingStep[];
    startTime: Date;
    estimatedCompletion?: Date;
    errorMessage?: string;
}

interface DocumentProcessingPipelineProps {
    documents: DocumentProcessingState[];
    onRetry?: (documentId: string) => void;
    onCancel?: (documentId: string) => void;
}

const DocumentProcessingPipeline: React.FC<DocumentProcessingPipelineProps> = ({
    documents,
    onRetry,
    onCancel
}) => {
    const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());

    const toggleExpanded = (docId: string) => {
        const newExpanded = new Set(expandedDocs);
        if (newExpanded.has(docId)) {
            newExpanded.delete(docId);
        } else {
            newExpanded.add(docId);
        }
        setExpandedDocs(newExpanded);
    };

    const getStepIcon = (step: ProcessingStep) => {
        if (step.status === 'completed') {
            return <CompleteIcon sx={{ color: 'success.main' }} />;
        }
        if (step.status === 'failed') {
            return <ErrorIcon sx={{ color: 'error.main' }} />;
        }
        if (step.status === 'processing') {
            return step.icon;
        }
        return step.icon;
    };

    const getOverallProgress = (doc: DocumentProcessingState) => {
        const completedSteps = doc.steps.filter(s => s.status === 'completed').length;
        return (completedSteps / doc.steps.length) * 100;
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'success';
            case 'processing': return 'primary';
            case 'failed': return 'error';
            default: return 'default';
        }
    };

    const formatDuration = (startTime: Date) => {
        const now = new Date();
        const diff = now.getTime() - startTime.getTime();
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);

        if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        }
        return `${seconds}s`;
    };

    return (
        <Box sx={{ width: '100%', maxWidth: 1200, mx: 'auto', p: 2 }}>
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
                📊 Document Processing Pipeline
            </Typography>

            {documents.map((doc) => {
                const isExpanded = expandedDocs.has(doc.documentId);
                const overallProgress = getOverallProgress(doc);
                const currentStepIndex = doc.steps.findIndex(s => s.status === 'processing');

                return (
                    <Paper
                        key={doc.documentId}
                        sx={{
                            mb: 1.5,
                            p: 2,
                            border: '1px solid',
                            borderColor: doc.status === 'processing' ? 'primary.main' : 'divider',
                            bgcolor: 'background.paper',
                            transition: 'border-color 0.2s ease'
                        }}
                    >
                        {/* Compact Document Header */}
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexGrow: 1 }}>
                                <Box
                                    sx={{
                                        width: 32,
                                        height: 32,
                                        borderRadius: 1,
                                        bgcolor: 'primary.main',
                                        color: 'white',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '0.75rem',
                                        fontWeight: 600
                                    }}
                                >
                                    {doc.fileType.toUpperCase().slice(0, 2)}
                                </Box>

                                <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                                    <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.875rem', mb: 0.25 }}>
                                        {doc.filename}
                                    </Typography>
                                    <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
                                        {(doc.fileSize / 1024 / 1024).toFixed(1)} MB • {formatDuration(doc.startTime)}
                                    </Typography>
                                </Box>
                            </Box>

                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Chip
                                    label={doc.status.replace('_', ' ').toUpperCase()}
                                    color={getStatusColor(doc.status) as any}
                                    size="small"
                                    variant="outlined"
                                    sx={{ fontSize: '0.6875rem', height: 24 }}
                                />
                                {onRetry && (doc.status === 'failed' || doc.status === 'uploaded') && (
                                    <Chip size="small" label="Retry" onClick={() => onRetry(doc.documentId)} variant="outlined" color="primary" sx={{ fontSize: '0.6875rem', height: 24 }} />
                                )}
                                {onCancel && doc.status === 'processing' && (
                                    <Chip size="small" label="Cancel" onClick={() => onCancel(doc.documentId)} variant="outlined" color="error" sx={{ fontSize: '0.6875rem', height: 24 }} />
                                )}
                                <IconButton size="small" onClick={() => toggleExpanded(doc.documentId)}>
                                    {isExpanded ? <CollapseIcon fontSize="small" /> : <ExpandIcon fontSize="small" />}
                                </IconButton>
                            </Box>
                        </Box>

                        {/* Compact Progress Bar */}
                        <Box sx={{ mb: 1.5 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary', fontWeight: 500 }}>
                                    PROGRESS
                                </Typography>
                                <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600, color: overallProgress === 100 ? 'success.main' : 'primary.main' }}>
                                    {Math.round(overallProgress)}%
                                </Typography>
                            </Box>
                            <LinearProgress
                                variant="determinate"
                                value={overallProgress}
                                sx={{
                                    height: 6,
                                    borderRadius: 3,
                                    bgcolor: 'grey.200',
                                    '& .MuiLinearProgress-bar': {
                                        borderRadius: 3,
                                        bgcolor: overallProgress === 100 ? 'success.main' : 'primary.main'
                                    }
                                }}
                            />
                        </Box>

                        {/* Current Step - Inline */}
                        {currentStepIndex >= 0 && (
                            <Box sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1.5,
                                p: 1.5,
                                bgcolor: 'action.hover',
                                borderRadius: 1,
                                border: '1px solid',
                                borderColor: 'primary.main',
                                mb: 1.5
                            }}>
                                <CircularProgress size={16} color="primary" />
                                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8125rem' }}>
                                    {doc.steps[currentStepIndex].label.replace(/[^A-Za-z\s]/g, '')}
                                </Typography>
                                <Box sx={{ flexGrow: 1 }} />
                                <Chip
                                    size="small"
                                    label="AUTO"
                                    variant="outlined"
                                    color="primary"
                                    sx={{ fontSize: '0.625rem', height: 20 }}
                                />
                            </Box>
                        )}

                        {/* Detailed Steps */}
                        <Collapse in={isExpanded}>
                            <Stepper orientation="vertical" sx={{ mt: 2 }}>
                                {doc.steps.map((step, index) => (
                                    <Step key={step.id} active={step.status !== 'pending'} completed={step.status === 'completed'}>
                                        <StepLabel
                                            icon={
                                                <Badge
                                                    badgeContent={step.status === 'processing' ? <CircularProgress size={12} /> : null}
                                                    overlap="circular"
                                                >
                                                    {getStepIcon(step)}
                                                </Badge>
                                            }
                                            error={step.status === 'failed'}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <Typography
                                                    variant="body1"
                                                    sx={{
                                                        fontWeight: step.status === 'processing' ? 600 : 400,
                                                        color: step.status === 'failed' ? 'error.main' : 'text.primary'
                                                    }}
                                                >
                                                    {step.label}
                                                </Typography>

                                                {step.status === 'processing' && step.progress !== undefined && (
                                                    <Chip
                                                        label={`${step.progress}%`}
                                                        size="small"
                                                        color="primary"
                                                        variant="outlined"
                                                    />
                                                )}
                                            </Box>
                                        </StepLabel>

                                        <StepContent>
                                            {step.message && (
                                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                                    {step.message}
                                                </Typography>
                                            )}

                                            {step.details && step.details.length > 0 && (
                                                <Box sx={{ ml: 2 }}>
                                                    {step.details.map((detail, idx) => (
                                                        <Typography
                                                            key={idx}
                                                            variant="caption"
                                                            display="block"
                                                            color="text.secondary"
                                                        >
                                                            • {detail}
                                                        </Typography>
                                                    ))}
                                                </Box>
                                            )}

                                            {step.status === 'processing' && step.progress !== undefined && (
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={step.progress}
                                                    sx={{ mt: 1, width: 200 }}
                                                />
                                            )}
                                        </StepContent>
                                    </Step>
                                ))}
                            </Stepper>
                        </Collapse>

                        {/* Error Message */}
                        {doc.status === 'failed' && doc.errorMessage && (
                            <Paper sx={{ p: 2, mt: 2, bgcolor: 'error.50', border: '1px solid', borderColor: 'error.200' }}>
                                <Typography variant="body2" color="error.main">
                                    <strong>Error:</strong> {doc.errorMessage}
                                </Typography>
                            </Paper>
                        )}
                    </Paper>
                );
            })}

            {documents.length === 0 && (
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'grey.50' }}>
                    <Typography variant="h6" color="text.secondary">
                        No documents currently processing
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Upload documents to see the real-time processing pipeline
                    </Typography>
                </Paper>
            )}
        </Box>
    );
};

// Default pipeline steps template
export const createDefaultPipelineSteps = (filename: string): ProcessingStep[] => [
    {
        id: 'upload',
        label: '📁 File Upload',
        icon: <UploadIcon />,
        status: 'completed',
        message: `${filename} uploaded successfully`,
        details: ['File saved to storage', 'Metadata recorded']
    },
    {
        id: 'virus_scan',
        label: '🦠 Virus Scan',
        icon: <VirusIcon />,
        status: 'processing',
        progress: 0,
        message: 'Scanning for malware and threats...',
        details: ['ClamAV engine', 'Signature database check']
    },
    {
        id: 'text_extraction',
        label: '📝 Text Extraction',
        icon: <ExtractIcon />,
        status: 'pending',
        message: 'Extract text content from document',
        details: ['OCR processing', 'Content parsing', 'Metadata extraction']
    },
    {
        id: 'elasticsearch_index',
        label: '🔍 Elasticsearch Indexing',
        icon: <ElasticsearchIcon />,
        status: 'pending',
        message: 'Creating keyword search index',
        details: ['Field boosting', 'Analyzer configuration', 'Index optimization']
    },
    {
        id: 'qdrant_index',
        label: '🧠 Qdrant Vector Index',
        icon: <QdrantIcon />,
        status: 'pending',
        message: 'Generating semantic embeddings',
        details: ['BERT transformers', 'Vector generation', 'Similarity indexing']
    },
    {
        id: 'postgresql_update',
        label: '🐘 PostgreSQL Update',
        icon: <PostgresIcon />,
        status: 'pending',
        message: 'Updating database indexes',
        details: ['GIN indexes', 'Trigram indexes', 'Full-text search']
    }
];

export default DocumentProcessingPipeline;
