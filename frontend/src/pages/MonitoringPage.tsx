import React, { useMemo, useState } from 'react'
import { Box, Paper, Typography, Chip, Stack, Button, Alert } from '@mui/material'
import { OpenInNew as OpenInNewIcon, Refresh as RefreshIcon } from '@mui/icons-material'

const GRAFANA_ORIGIN = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3030'

/**
 * In-app Monitoring surface.
 * Grafana is embedded here so Admin/Manager stay inside inDoc after one login.
 * Local stack enables Grafana anonymous Viewer + allow_embedding.
 */
const MonitoringPage: React.FC = () => {
  const [frameKey, setFrameKey] = useState(0)
  const src = useMemo(() => `${GRAFANA_ORIGIN}/?kiosk`, [])

  return (
    <Box sx={{ height: 'calc(100vh - 112px)', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Monitoring
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Live ops inside inDoc — one login, no separate Grafana session for viewing.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip size="small" color="success" label="Embedded" />
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={() => setFrameKey((k) => k + 1)}
          >
            Reload
          </Button>
          <Button
            size="small"
            variant="outlined"
            endIcon={<OpenInNewIcon />}
            href={GRAFANA_ORIGIN}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open full Grafana
          </Button>
        </Stack>
      </Stack>

      <Alert severity="info" sx={{ py: 0.5 }}>
        Viewing uses Grafana anonymous Viewer. Admin edits still use Grafana’s own admin account if needed.
      </Alert>

      <Paper
        sx={{
          flex: 1,
          minHeight: 0,
          borderRadius: 3,
          overflow: 'hidden',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box
          component="iframe"
          key={frameKey}
          title="inDoc Monitoring"
          src={src}
          sx={{
            width: '100%',
            height: '100%',
            border: 0,
            display: 'block',
            bgcolor: 'background.default',
          }}
          allow="fullscreen"
        />
      </Paper>
    </Box>
  )
}

export default MonitoringPage
