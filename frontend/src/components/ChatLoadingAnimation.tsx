/**
 * Beautiful Chat Loading Animation
 * 
 * Clever, informative progress indicator that shows what's happening
 * Per AI Guide: Uses theme tokens, engaging UX
 */
import React, { useState, useEffect } from 'react'
import { Box, Typography, LinearProgress, Paper, Stack, Fade, Grow, Chip } from '@mui/material'
import {
    Search as SearchIcon,
    Psychology as ThinkingIcon,
    AutoAwesome as SparkleIcon,
    CheckCircle as DoneIcon,
} from '@mui/icons-material'

interface ChatLoadingAnimationProps {
    stage?: 'searching' | 'analyzing' | 'generating' | 'done'
    progress?: number
}

export const ChatLoadingAnimation: React.FC<ChatLoadingAnimationProps> = ({
    stage = 'searching',
    progress = 0
}) => {
    const [currentStage, setCurrentStage] = useState(stage)
    const [animatedProgress, setAnimatedProgress] = useState(0)
    const [dots, setDots] = useState('')

    // Animated dots for "thinking" effect
    useEffect(() => {
        const interval = setInterval(() => {
            setDots(prev => prev.length >= 3 ? '' : prev + '.')
        }, 400)
        return () => clearInterval(interval)
    }, [])

    // Smooth progress animation
    useEffect(() => {
        setAnimatedProgress(progress)
    }, [progress])

    // Auto-advance stages if not controlled
    useEffect(() => {
        if (stage !== currentStage) {
            setCurrentStage(stage)
        }
    }, [stage])

    const stages = [
        {
            key: 'searching',
            icon: <SearchIcon sx={{ fontSize: 28 }} />,
            label: 'Searching documents',
            color: '#1976d2',
            description: 'Hybrid search across Elasticsearch + Qdrant'
        },
        {
            key: 'analyzing',
            icon: <ThinkingIcon sx={{ fontSize: 28 }} />,
            label: 'Analyzing context',
            color: '#7b1fa2',
            description: 'Building grounded context from retrieved sources'
        },
        {
            key: 'generating',
            icon: <SparkleIcon sx={{ fontSize: 28 }} />,
            label: 'Generating answer',
            color: '#00897b',
            description: 'Multi-provider LLM with answer grounding'
        },
        {
            key: 'done',
            icon: <DoneIcon sx={{ fontSize: 28 }} />,
            label: 'Complete',
            color: '#4caf50',
            description: 'Response ready with source citations'
        }
    ]

    const activeStage = stages.find(s => s.key === currentStage) || stages[0]
    const stageIndex = stages.findIndex(s => s.key === currentStage)

    return (
        <Fade in timeout={300}>
            <Paper
                elevation={0}
                sx={{
                    p: 3,
                    bgcolor: 'background.paper',
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'divider',
                }}
            >
                <Stack spacing={3}>
                    {/* Main status with icon */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Grow in timeout={500}>
                            <Box
                                sx={{
                                    color: activeStage.color,
                                    display: 'flex',
                                    animation: currentStage !== 'done' ? 'pulse 2s ease-in-out infinite' : 'none',
                                    '@keyframes pulse': {
                                        '0%, 100%': { opacity: 1, transform: 'scale(1)' },
                                        '50%': { opacity: 0.7, transform: 'scale(1.1)' }
                                    }
                                }}
                            >
                                {activeStage.icon}
                            </Box>
                        </Grow>

                        <Box sx={{ flex: 1 }}>
                            <Typography
                                variant="h6"
                                sx={{
                                    fontWeight: 600,
                                    color: activeStage.color
                                }}
                            >
                                {activeStage.label}{currentStage !== 'done' && dots}
                            </Typography>
                            <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{ display: 'block', mt: 0.5 }}
                            >
                                {activeStage.description}
                            </Typography>
                        </Box>
                    </Box>

                    {/* Progress bar */}
                    <Box>
                        <LinearProgress
                            variant={currentStage === 'done' ? 'determinate' : 'indeterminate'}
                            value={currentStage === 'done' ? 100 : animatedProgress}
                            sx={{
                                height: 8,
                                borderRadius: 4,
                                bgcolor: 'action.hover',
                                '& .MuiLinearProgress-bar': {
                                    borderRadius: 4,
                                    background: currentStage === 'done'
                                        ? activeStage.color
                                        : `linear-gradient(90deg, ${activeStage.color} 0%, ${activeStage.color}dd 100%)`,
                                    transition: 'transform 0.4s ease'
                                }
                            }}
                        />
                        {currentStage !== 'done' && (
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                                <Typography variant="caption" color="text.secondary">
                                    Processing...
                                </Typography>
                                <Typography variant="caption" sx={{ color: activeStage.color, fontWeight: 600 }}>
                                    {Math.round(animatedProgress)}%
                                </Typography>
                            </Box>
                        )}
                    </Box>

                    {/* Stage chips */}
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {stages.map((s, idx) => {
                            const isPast = idx < stageIndex
                            const isCurrent = idx === stageIndex
                            const isFuture = idx > stageIndex

                            return (
                                <Chip
                                    key={s.key}
                                    size="small"
                                    icon={isPast ? <DoneIcon /> : isCurrent ? s.icon : undefined}
                                    label={s.label.replace(' documents', '').replace(' context', '').replace(' answer', '')}
                                    sx={{
                                        bgcolor: isPast ? `${s.color}22` : isCurrent ? `${s.color}33` : 'action.hover',
                                        borderColor: isPast || isCurrent ? s.color : 'divider',
                                        border: '1px solid',
                                        color: isPast || isCurrent ? s.color : 'text.secondary',
                                        fontWeight: isCurrent ? 600 : 400,
                                        transition: 'all 0.3s ease',
                                        '& .MuiChip-icon': {
                                            color: isPast || isCurrent ? s.color : 'text.secondary'
                                        }
                                    }}
                                />
                            )
                        })}
                    </Box>

                    {/* Fun fact or tip (rotates) */}
                    {currentStage !== 'done' && (
                        <Fade in timeout={1000}>
                            <Box
                                sx={{
                                    p: 2,
                                    bgcolor: 'action.hover',
                                    borderRadius: 1,
                                    borderLeft: '3px solid',
                                    borderLeftColor: activeStage.color
                                }}
                            >
                                <Typography variant="caption" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                                    💡 <strong>Did you know?</strong> inDoc verifies every answer against minimum 3 source documents
                                    to prevent hallucinations. Your answer is being grounded right now...
                                </Typography>
                            </Box>
                        </Fade>
                    )}
                </Stack>
            </Paper>
        </Fade>
    )
}

export default ChatLoadingAnimation

