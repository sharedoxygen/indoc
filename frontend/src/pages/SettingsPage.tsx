import React from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Stack,
  Divider,
  Button,
  TextField,
  Switch,
  FormControlLabel,
} from '@mui/material'
import { motion } from 'framer-motion'
import {
  useGetSettingsQuery,
  useGetAdminSettingsQuery,
  useGetFeatureFlagsQuery,
  useGetDependenciesHealthQuery,
  useGetMcpStatusQuery,
  useExecuteToolMutation,
} from '../store/api'
import { useAppSelector } from '../hooks/redux'
import { PrecisionDial, NeedleGauge } from '../components/instruments'

function healthToScore(status: unknown): number {
  const s = String(status || '').toLowerCase()
  if (s === 'healthy' || s === 'ok' || s === 'up') return 100
  if (s === 'degraded' || s === 'warning') return 50
  return 0
}

function healthStatus(score: number): 'ok' | 'warn' | 'error' {
  if (score >= 90) return 'ok'
  if (score >= 40) return 'warn'
  return 'error'
}

const SettingsPage: React.FC = () => {
  const { data: settings } = useGetSettingsQuery(undefined)
  const { data: admin } = useGetAdminSettingsQuery(undefined)
  const { data: features } = useGetFeatureFlagsQuery(undefined)
  const { data: health } = useGetDependenciesHealthQuery(undefined)
  const { data: mcp } = useGetMcpStatusQuery(undefined)
  const [executeTool, { data: execResult, isLoading: isExecLoading }] = useExecuteToolMutation()
  const [command, setCommand] = React.useState('{}')
  const user = useAppSelector((s) => s.auth.user)
  const isAdmin = user?.role === 'Admin'

  const overallScore = healthToScore(health?.overall)
  const deps = health?.dependencies ? Object.entries(health.dependencies) : []

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Application
            </Typography>
            <Stack spacing={1}>
              <Typography variant="body2">Name: {settings?.app_name}</Typography>
              <Typography variant="body2">Version: {settings?.app_version}</Typography>
              <Typography variant="body2">Max upload size: {settings?.max_upload_size}</Typography>
              <Typography variant="body2">
                Allowed extensions: {(settings?.allowed_extensions || []).join(', ')}
              </Typography>
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Feature Flags
            </Typography>
            <Stack spacing={0.5}>
              {features &&
                Object.entries(features).map(([k, v]) => (
                  <FormControlLabel
                    key={k}
                    control={<Switch checked={Boolean(v)} disabled size="small" color="success" />}
                    label={<Typography variant="body2">{k}</Typography>}
                  />
                ))}
              {!features && <Chip label="No flags loaded" size="small" />}
            </Stack>
          </Paper>
        </Grid>

        {isAdmin && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Admin Settings
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Database</Typography>
                  <Stack spacing={0.5}>
                    <Typography variant="body2">Host: {admin?.database?.host}</Typography>
                    <Typography variant="body2">Port: {admin?.database?.port}</Typography>
                    <Typography variant="body2">DB: {admin?.database?.database}</Typography>
                    <Typography variant="body2">User: {admin?.database?.user}</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Elasticsearch</Typography>
                  <Stack spacing={0.5}>
                    <Typography variant="body2">URL: {admin?.elasticsearch?.url}</Typography>
                    <Typography variant="body2">Index: {admin?.elasticsearch?.index}</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Qdrant</Typography>
                  <Stack spacing={0.5}>
                    <Typography variant="body2">URL: {admin?.qdrant?.url}</Typography>
                    <Typography variant="body2">Class: {admin?.qdrant?.class}</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Storage</Typography>
                  <Typography variant="body2">Path: {admin?.storage?.storage_path}</Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        )}

        <Grid item xs={12}>
          <Paper
            component={motion.div}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            sx={{ p: 3, borderRadius: 3 }}
          >
            <Typography variant="h6" gutterBottom>
              Dependencies Health
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, alignItems: 'center', mb: 2 }}>
              <PrecisionDial
                value={overallScore}
                label="Overall"
                unit="%"
                precision={0}
                size={150}
                status={healthStatus(overallScore)}
                help={{
                  title: 'Overall dependency health',
                  body: 'Composite score across backend dependencies (database, search, object storage, workers, LLM). 100 = all healthy.',
                  reading: `${Math.round(overallScore)}% · ${String(health?.overall || 'unknown')}`,
                  details: deps.slice(0, 6).map(([name, st]) => ({
                    label: name,
                    value: String(st),
                  })),
                }}
              />
              <Typography variant="body2" color="text.secondary">
                Live dependency telemetry · {String(health?.overall || 'unknown')}
              </Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            <Grid container spacing={2}>
              {deps.map(([name, status]) => {
                const score = healthToScore(status)
                return (
                  <Grid key={name} item xs={6} sm={4} md={3} lg={2}>
                    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                      <NeedleGauge
                        value={score}
                        label={name}
                        displayValue={String(status)}
                        size={110}
                        status={healthStatus(score)}
                        help={{
                          title: `${name} health`,
                          body: `Live status for the “${name}” dependency. Needle maps healthy (100) → degraded (50) → down (0).`,
                          reading: String(status),
                          details: [
                            { label: 'Score', value: String(score) },
                            { label: 'Status', value: String(status) },
                          ],
                        }}
                      />
                    </Box>
                  </Grid>
                )
              })}
              {deps.length === 0 && <Chip label="No dependency data" size="small" />}
            </Grid>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              MCP
            </Typography>
            <Stack spacing={1} sx={{ mb: 2 }}>
              <Typography variant="body2">Status: {mcp?.status}</Typography>
              <Typography variant="body2">Version: {mcp?.version}</Typography>
              <Typography variant="body2">Capabilities: {(mcp?.capabilities || []).join(', ')}</Typography>
            </Stack>
            <Stack direction="row" spacing={2} alignItems="flex-start">
              <TextField
                label="Execute Command (JSON)"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                minRows={3}
                multiline
                fullWidth
              />
              <Button
                variant="contained"
                onClick={() => {
                  try {
                    const payload = JSON.parse(command)
                    executeTool(payload)
                  } catch {
                    // ignore parse errors in this minimal UI
                  }
                }}
                disabled={isExecLoading}
              >
                Execute
              </Button>
            </Stack>
            {execResult && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Result</Typography>
                <Paper variant="outlined" sx={{ p: 2, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(execResult, null, 2)}
                </Paper>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default SettingsPage
