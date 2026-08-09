import React from 'react';
import { Box, Typography, LinearProgress, Chip, Paper, useTheme } from '@mui/material';
import {
    CloudUpload as UploadIcon,
    Storage as PostgresIcon,
    Search as ElasticsearchIcon,
    AccountTree as QdrantIcon,
    CheckCircle as SuccessIcon,
    Error as ErrorIcon,
    HourglassEmpty as ProcessingIcon,
} from '@mui/icons-material';

interface ProcessingStep {
    name: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    message?: string;
    details?: string[];
    errorMessage?: string;
    icon: React.ReactNode;
    color: string;
}

interface DocumentProcessingProgressProps {
    filename: string;
    steps: {
        upload?: { status: string; progress?: number; message?: string };
        virus_scan?: { status: string; progress?: number; message?: string };
        text_extraction?: { status: string; progress?: number; message?: string };
        elasticsearch_indexing?: { status: string; progress?: number; message?: string };
        qdrant_vector_index?: { status: string; progress?: number; message?: string };
    };
    overallProgress: number;
}

export const DocumentProcessingProgress: React.FC<DocumentProcessingProgressProps> = ({
    filename,
    steps,
    overallProgress,
}) => {
    const theme = useTheme();

    const getStepIcon = (stepName: string, status: string) => {
        if (status === 'completed') return <SuccessIcon sx={{ fontSize: 28, color: theme.palette.success.main }} />;
        if (status === 'failed') return <ErrorIcon sx={{ fontSize: 28, color: theme.palette.error.main }} />;
        if (status === 'processing') return <ProcessingIcon sx={{ fontSize: 28, color: theme.palette.primary.main, animation: 'spin 2s linear infinite', '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } } }} />;

        const icons: Record<string, React.ReactNode> = {
            upload: <UploadIcon sx={{ fontSize: 28, color: theme.palette.text.disabled }} />,
            postgres: <PostgresIcon sx={{ fontSize: 28, color: theme.palette.text.disabled }} />,
            elasticsearch: <ElasticsearchIcon sx={{ fontSize: 28, color: theme.palette.text.disabled }} />,
            qdrant: <QdrantIcon sx={{ fontSize: 28, color: theme.palette.text.disabled }} />,
        };
        return icons[stepName] || <ProcessingIcon sx={{ fontSize: 28, color: theme.palette.text.disabled }} />;
    };

    const getStepColor = (status: string) => {
        if (status === 'completed') return theme.palette.success.main;
        if (status === 'failed') return theme.palette.error.main;
        if (status === 'processing') return theme.palette.primary.main;
        return theme.palette.divider;
    };

    const getStatusChip = (status: string) => {
        if (status === 'completed') return <Chip label="✓ Done" color="success" size="small" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />;
        if (status === 'failed') return <Chip label="✗ Failed" color="error" size="small" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />;
        if (status === 'processing') return <Chip label="Processing..." color="primary" size="small" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />;
        return <Chip label="Pending" variant="outlined" size="small" sx={{ fontSize: '0.7rem' }} />;
    };

    const pipelineSteps: { key: string; label: string; stepKey: keyof typeof steps; icon: string }[] = [
        { key: 'upload', label: 'Upload', stepKey: 'upload', icon: 'upload' },
        { key: 'postgres', label: 'PostgreSQL', stepKey: 'text_extraction', icon: 'postgres' },
        { key: 'elasticsearch', label: 'Elasticsearch', stepKey: 'elasticsearch_indexing', icon: 'elasticsearch' },
        { key: 'qdrant', label: 'Qdrant', stepKey: 'qdrant_vector_index', icon: 'qdrant' },
    ];

    return (
        <Paper
            sx={{
                p: 3,
                mb: 2,
                borderRadius: 3,
                background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.mode === 'dark' ? 'rgba(25, 118, 210, 0.05)' : 'rgba(25, 118, 210, 0.02)'} 100%)`,
                border: `2px solid ${overallProgress === 100 ? theme.palette.success.main : theme.palette.primary.main}`,
            }}
        >
            {/* Header */}
            <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 1, color: 'text.primary' }}>
                    {filename}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress
                        variant="determinate"
                        value={overallProgress}
                        sx={{
                            flex: 1,
                            height: 8,
                            borderRadius: 4,
                            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                            '& .MuiLinearProgress-bar': {
                                borderRadius: 4,
                                background: `linear-gradient(90deg, ${theme.palette.success.main} 0%, ${theme.palette.primary.main} 100%)`,
                            },
                        }}
                    />
                    <Typography variant="body2" sx={{ fontWeight: 700, minWidth: 45, color: 'text.primary' }}>
                        {Math.round(overallProgress)}%
                    </Typography>
                </Box>
            </Box>

            {/* Pipeline Steps */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
                {pipelineSteps.map((step, index) => {
                    const stepData = steps[step.stepKey];
                    const status = stepData?.status || 'pending';
                    const message = stepData?.message || '';
                    const stepColor = getStepColor(status);

                    return (
                        <React.Fragment key={step.key}>
                            {/* Step Card */}
                            <Box
                                sx={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    gap: 0.5,
                                    px: 2,
                                    py: 1.5,
                                    borderRadius: 2,
                                    border: `2px solid ${stepColor}`,
                                    bgcolor: status === 'completed' ? `${theme.palette.success.main}15` :
                                        status === 'processing' ? `${theme.palette.primary.main}15` :
                                            status === 'failed' ? `${theme.palette.error.main}15` :
                                                theme.palette.background.paper,
                                    minWidth: 120,
                                    position: 'relative',
                                    transition: 'all 0.3s ease',
                                    animation: status === 'processing' ? 'pulse 2s ease-in-out infinite' : 'none',
                                    '@keyframes pulse': {
                                        '0%, 100%': { transform: 'scale(1)' },
                                        '50%': { transform: 'scale(1.02)' },
                                    },
                                }}
                            >
                                {/* Icon */}
                                <Box sx={{ mb: 0.5 }}>
                                    {getStepIcon(step.icon, status)}
                                </Box>

                                {/* Label */}
                                <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem', color: 'text.secondary', textAlign: 'center' }}>
                                    {step.label.toUpperCase()}
                                </Typography>

                                {/* Status Badge */}
                                {getStatusChip(status)}

                                {/* Message */}
                                {message && (
                                    <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', textAlign: 'center', mt: 0.5, maxWidth: 100 }}>
                                        {message}
                                    </Typography>
                                )}
                            </Box>

                            {/* Arrow between steps */}
                            {index < pipelineSteps.length - 1 && (
                                <Typography sx={{ color: stepColor, fontWeight: 700, fontSize: '1.5rem', opacity: 0.6 }}>
                                    →
                                </Typography>
                            )}
                        </React.Fragment>
                    );
                })}

                {/* Final Check Mark - Only show when ALL steps are actually completed */}
                {steps.upload?.status === 'completed' &&
                    steps.text_extraction?.status === 'completed' &&
                    steps.elasticsearch_indexing?.status === 'completed' &&
                    steps.qdrant_vector_index?.status === 'completed' && (
                    <>
                        <Typography sx={{ color: theme.palette.success.main, fontWeight: 700, fontSize: '1.5rem' }}>
                            ✓
                        </Typography>
                        <Chip label="INDEXED" color="success" sx={{ fontWeight: 700 }} />
                    </>
                )}
            </Box>

            {/* Error Details */}
            {Object.values(steps).some((s: any) => s?.status === 'failed') && (
                <Box sx={{ mt: 2, p: 2, bgcolor: theme.palette.error.light, borderRadius: 2, border: `1px solid ${theme.palette.error.main}` }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.error.dark }}>
                        ⚠️ Processing failed. Review error details in System Logs or retry upload.
                    </Typography>
                    {Object.entries(steps).map(([key, value]: [string, any]) =>
                        value?.status === 'failed' && value?.errorMessage ? (
                            <Typography key={key} variant="caption" sx={{ display: 'block', mt: 0.5, color: theme.palette.error.dark }}>
                                {key}: {value.errorMessage}
                            </Typography>
                        ) : null
                    )}
                </Box>
            )}
        </Paper>
    );
};

export default DocumentProcessingProgress;

