import React from 'react'
import {
    Card,
    CardContent,
    Typography,
    Chip,
    Box,
    IconButton,
    Avatar,
} from '@mui/material'
import { MoreVert as MoreIcon } from '@mui/icons-material'
import { format } from 'date-fns'

interface CompactDocumentCardProps {
    document: any
    onView: (doc: any) => void
    onMenuOpen: (event: React.MouseEvent<HTMLElement>, doc: any) => void
}

const getFileTypeColor = (fileType: string) => {
    const colors: Record<string, string> = {
        pdf: '#dc2626',
        docx: '#2563eb',
        xlsx: '#059669',
        pptx: '#ea580c',
        txt: '#6b7280',
        html: '#7c3aed',
        json: '#0891b2',
        xml: '#a16207',
    }
    return colors[fileType] || '#6b7280'
}

const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 B'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
}

export const CompactDocumentCard: React.FC<CompactDocumentCardProps> = ({
    document,
    onView,
    onMenuOpen,
}) => {
    return (
        <Card
            sx={{
                height: 140,
                cursor: 'pointer',
                borderRadius: 3,
                border: '1px solid',
                borderColor: 'divider',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                    borderColor: 'primary.main',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                },
            }}
            onClick={() => onView(document)}
        >
            <CardContent sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                {/* Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                    <Avatar
                        sx={{
                            width: 32,
                            height: 32,
                            bgcolor: getFileTypeColor(document.file_type),
                            fontSize: '0.75rem',
                            fontWeight: 700,
                        }}
                    >
                        {document.file_type.toUpperCase().slice(0, 3)}
                    </Avatar>
                    <IconButton
                        size="small"
                        onClick={(e) => {
                            e.stopPropagation()
                            onMenuOpen(e, document)
                        }}
                        sx={{ p: 0.5, color: 'text.secondary' }}
                    >
                        <MoreIcon fontSize="small" />
                    </IconButton>
                </Box>

                {/* Title */}
                <Typography
                    variant="subtitle2"
                    sx={{
                        fontWeight: 600,
                        fontSize: '0.875rem',
                        lineHeight: 1.2,
                        mb: 1,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                    }}
                >
                    {document.title || document.filename}
                </Typography>

                {/* Metadata */}
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5 }}>
                    {formatFileSize(document.file_size)} • {format(new Date(document.created_at), 'MMM dd')}
                </Typography>

                {/* Status badges */}
                <Box sx={{ display: 'flex', gap: 0.5, mt: 'auto' }}>
                    <Chip
                        label={document.status}
                        size="small"
                        color={document.status === 'indexed' ? 'success' : document.status === 'failed' ? 'error' : 'warning'}
                        sx={{
                            fontSize: '0.65rem',
                            height: 20,
                            '& .MuiChip-label': { px: 1 }
                        }}
                    />
                    {document.virus_scan_status && document.virus_scan_status !== 'clean' && (
                        <Chip
                            label={document.virus_scan_status}
                            size="small"
                            color="warning"
                            sx={{
                                fontSize: '0.65rem',
                                height: 20,
                                '& .MuiChip-label': { px: 1 }
                            }}
                        />
                    )}
                </Box>
            </CardContent>
        </Card>
    )
}
