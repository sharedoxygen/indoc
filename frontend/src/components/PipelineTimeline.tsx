import React from 'react';
import { Box, Typography } from '@mui/material';
import { keyframes } from '@mui/system';

// Pulse animation for the active step
const pulse = keyframes`
  0% { transform: scale(1); box-shadow: 0 0 5px rgba(25,118,210,0.5); }
  50% { transform: scale(1.15); box-shadow: 0 0 15px rgba(25,118,210,0.7); }
  100% { transform: scale(1); box-shadow: 0 0 5px rgba(25,118,210,0.5); }
`;

interface ProcessingStep {
    id: string;
    label: string;
    status: 'completed' | 'processing' | 'pending';
}

interface PipelineTimelineProps {
    steps: ProcessingStep[];
}

const PipelineTimeline: React.FC<PipelineTimelineProps> = ({ steps }) => {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', px: 2, py: 1 }}>
            {steps.map((step, idx) => (
                <React.Fragment key={step.id}>
                    {/* Step Icon & Label */}
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, position: 'relative' }}>
                        <Box
                            sx={{
                                width: 40,
                                height: 40,
                                borderRadius: '50%',
                                bgcolor:
                                    step.status === 'completed'
                                        ? 'success.main'
                                        : step.status === 'processing'
                                            ? 'primary.main'
                                            : 'grey.400',
                                color: 'white',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                animation: step.status === 'processing' ? `${pulse} 2s infinite` : 'none',
                                zIndex: 1
                            }}
                        />
                        <Typography variant="caption" sx={{ mt: 1, color: step.status === 'pending' ? 'grey.500' : 'text.primary' }}>
                            {step.label}
                        </Typography>
                    </Box>

                    {/* Connector */}
                    {idx < steps.length - 1 && (
                        <Box
                            sx={{
                                flex: 1,
                                height: 4,
                                bgcolor: steps[idx].status === 'completed' && steps[idx + 1].status !== 'pending'
                                    ? 'primary.main'
                                    : 'grey.300'
                            }}
                        />
                    )}
                </React.Fragment>
            ))}
        </Box>
    );
};

export default PipelineTimeline;
