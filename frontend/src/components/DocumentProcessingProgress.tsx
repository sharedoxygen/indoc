import React, { useMemo } from 'react'
import { Box, Typography, Chip, Paper, useTheme } from '@mui/material'
import {
  CloudUpload as UploadIcon,
  Storage as PostgresIcon,
  Search as ElasticsearchIcon,
  AccountTree as QdrantIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  HourglassEmpty as ProcessingIcon,
} from '@mui/icons-material'
import { PrecisionDial, SegmentRing, ArcMeter } from './instruments'
import type { SegmentStatus } from './instruments'

interface DocumentProcessingProgressProps {
  filename: string
  steps: {
    upload?: { status: string; progress?: number; message?: string }
    virus_scan?: { status: string; progress?: number; message?: string }
    text_extraction?: { status: string; progress?: number; message?: string }
    elasticsearch_indexing?: { status: string; progress?: number; message?: string }
    qdrant_vector_index?: { status: string; progress?: number; message?: string }
  }
  overallProgress: number
}

const toSegmentStatus = (status?: string): SegmentStatus => {
  if (status === 'completed') return 'complete'
  if (status === 'failed') return 'failed'
  if (status === 'processing') return 'active'
  return 'pending'
}

export const DocumentProcessingProgress: React.FC<DocumentProcessingProgressProps> = ({
  filename,
  steps,
  overallProgress,
}) => {
  const theme = useTheme()

  const getStepIcon = (stepName: string, status: string) => {
    if (status === 'completed') return <SuccessIcon sx={{ fontSize: 22, color: theme.palette.success.main }} />
    if (status === 'failed') return <ErrorIcon sx={{ fontSize: 22, color: theme.palette.error.main }} />
    if (status === 'processing')
      return (
        <ProcessingIcon
          sx={{
            fontSize: 22,
            color: theme.palette.primary.main,
            animation: 'spin 2s linear infinite',
            '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } },
          }}
        />
      )

    const icons: Record<string, React.ReactNode> = {
      upload: <UploadIcon sx={{ fontSize: 22, color: theme.palette.text.disabled }} />,
      postgres: <PostgresIcon sx={{ fontSize: 22, color: theme.palette.text.disabled }} />,
      elasticsearch: <ElasticsearchIcon sx={{ fontSize: 22, color: theme.palette.text.disabled }} />,
      qdrant: <QdrantIcon sx={{ fontSize: 22, color: theme.palette.text.disabled }} />,
    }
    return icons[stepName] || <ProcessingIcon sx={{ fontSize: 22, color: theme.palette.text.disabled }} />
  }

  const pipelineSteps: { key: string; label: string; stepKey: keyof typeof steps; icon: string }[] = [
    { key: 'upload', label: 'Upload', stepKey: 'upload', icon: 'upload' },
    { key: 'postgres', label: 'PostgreSQL', stepKey: 'text_extraction', icon: 'postgres' },
    { key: 'elasticsearch', label: 'Elasticsearch', stepKey: 'elasticsearch_indexing', icon: 'elasticsearch' },
    { key: 'qdrant', label: 'Qdrant', stepKey: 'qdrant_vector_index', icon: 'qdrant' },
  ]

  const segments = useMemo(
    () =>
      pipelineSteps.map((s) => ({
        key: s.key,
        label: s.label,
        status: toSegmentStatus(steps[s.stepKey]?.status),
        value: Math.round(steps[s.stepKey]?.progress ?? 0),
      })),
    [steps]
  )

  const activeStep = pipelineSteps.find((s) => steps[s.stepKey]?.status === 'processing')
  const activeProgress = activeStep ? Number(steps[activeStep.stepKey]?.progress ?? overallProgress) : overallProgress

  return (
    <Paper
      sx={{
        p: 2.5,
        mb: 2,
        borderRadius: 3,
        background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${
          theme.palette.mode === 'dark' ? 'rgba(25, 118, 210, 0.05)' : 'rgba(25, 118, 210, 0.02)'
        } 100%)`,
        border: `2px solid ${overallProgress === 100 ? theme.palette.success.main : theme.palette.primary.main}`,
      }}
    >
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', mb: 2 }}>
        <PrecisionDial
          value={overallProgress}
          label="Overall"
          unit="%"
          precision={0}
          size={120}
          status={overallProgress >= 100 ? 'ok' : 'active'}
          help={{
            title: 'Overall progress',
            body: 'End-to-end document pipeline progress for this file (upload → parse → embed → index).',
            reading: `${Math.round(overallProgress)}%`,
            details: [
              { label: 'File', value: filename },
              {
                label: 'Active stage',
                value: activeStep?.label || (overallProgress >= 100 ? 'Complete' : 'Waiting'),
              },
            ],
          }}
        />
        <Box sx={{ flex: 1, minWidth: 180 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5, color: 'text.primary' }}>
            {filename}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {activeStep
              ? `${activeStep.label}: ${steps[activeStep.stepKey]?.message || 'Processing…'}`
              : overallProgress >= 100
                ? 'Pipeline complete'
                : 'Waiting for pipeline updates'}
          </Typography>
          {activeStep && (
            <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-start' }}>
              <ArcMeter
                value={activeProgress}
                label={activeStep.label}
                unit="%"
                precision={0}
                size={90}
                status="active"
                help={{
                  title: `${activeStep.label} stage`,
                  body: steps[activeStep.stepKey]?.message || `Progress within the ${activeStep.label} pipeline stage.`,
                  reading: `${Math.round(activeProgress)}%`,
                }}
              />
            </Box>
          )}
        </Box>
        <SegmentRing
          segments={segments.map((seg) => ({
            ...seg,
            help: {
              title: seg.label,
              body: `Pipeline stage “${seg.label}” for this document.`,
              reading: seg.status,
            },
          }))}
          size={150}
          centerLabel="Stages"
          centerValue={`${Math.round(overallProgress)}%`}
          help={{
            title: 'Pipeline stages',
            body: 'Chronograph of this document’s processing stages. Center shows overall percent complete.',
            reading: `${Math.round(overallProgress)}%`,
          }}
        />
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
        {pipelineSteps.map((step) => {
          const status = steps[step.stepKey]?.status || 'pending'
          return (
            <Chip
              key={step.key}
              icon={getStepIcon(step.icon, status) as any}
              label={step.label}
              size="small"
              color={
                status === 'completed' ? 'success' : status === 'failed' ? 'error' : status === 'processing' ? 'primary' : 'default'
              }
              variant={status === 'pending' ? 'outlined' : 'filled'}
              sx={{ fontWeight: 600 }}
            />
          )
        })}
        {steps.upload?.status === 'completed' &&
          steps.text_extraction?.status === 'completed' &&
          steps.elasticsearch_indexing?.status === 'completed' &&
          steps.qdrant_vector_index?.status === 'completed' && (
            <Chip label="INDEXED" color="success" sx={{ fontWeight: 700 }} />
          )}
      </Box>

      {Object.values(steps).some((s: any) => s?.status === 'failed') && (
        <Box
          sx={{
            mt: 2,
            p: 2,
            bgcolor: theme.palette.error.light,
            borderRadius: 2,
            border: `1px solid ${theme.palette.error.main}`,
          }}
        >
          <Typography variant="caption" sx={{ fontWeight: 600, color: theme.palette.error.dark }}>
            Processing failed. Review System Logs or retry upload.
          </Typography>
        </Box>
      )}
    </Paper>
  )
}

export default DocumentProcessingProgress
