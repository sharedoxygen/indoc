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

function parseDependencyStatus(status: unknown): {
  score: number
  short: string
  detail: string | null
  tone: 'ok' | 'warn' | 'error'
} {
  const raw = String(status ?? 'unknown').trim()
  const lower = raw.toLowerCase()
  const [head, ...rest] = raw.split(':')
  const kind = (head || 'unknown').trim().toLowerCase()
  const detail = rest.join(':').trim() || null

  if (kind === 'healthy' || kind === 'ok' || kind === 'up' || lower === 'healthy') {
    return { score: 100, short: 'OK', detail: null, tone: 'ok' }
  }
  if (kind === 'degraded' || kind === 'warning' || kind === 'warn') {
    return { score: 50, short: 'WARN', detail, tone: 'warn' }
  }
  if (kind === 'unhealthy' || kind === 'down' || kind === 'error' || kind === 'failed') {
    return { score: 0, short: 'DOWN', detail: detail || raw, tone: 'error' }
  }
  if (lower.includes('degraded') || lower.includes('warning')) {
    return { score: 50, short: 'WARN', detail: raw, tone: 'warn' }
  }
  return { score: 0, short: 'DOWN', detail: raw, tone: 'error' }
}

function healthToScore(status: unknown): number {
  return parseDependencyStatus(status).score
}

function healthStatus(score: number): 'ok' | 'warn' | 'error' {
  if (score >= 90) return 'ok'
  if (score >= 40) return 'warn'
  return 'error'
}

function SettingRow({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ fontWeight: 700, letterSpacing: 0.3, display: 'block', mb: 0.25 }}
      >
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontSize: '0.95rem',
          lineHeight: 1.45,
          wordBreak: 'break-word',
          color: value == null || value === '' ? 'text.disabled' : 'text.primary',
        }}
      >
        {value == null || value === '' ? '—' : value}
      </Typography>
    </Box>
  )
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
  const overallParsed = parseDependencyStatus(health?.overall)

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 750, letterSpacing: '-0.02em' }}>
        Settings
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
              Application
            </Typography>
            <Stack spacing={1.5}>
              <SettingRow label="Name" value={settings?.app_name} />
              <SettingRow label="Version" value={settings?.app_version} />
              <SettingRow label="Max upload size" value={settings?.max_upload_size} />
              <SettingRow
                label="Allowed extensions"
                value={(settings?.allowed_extensions || []).join(', ')}
              />
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
              Feature Flags
            </Typography>
            <Stack spacing={0.75}>
              {features &&
                Object.entries(features).map(([k, v]) => (
                  <FormControlLabel
                    key={k}
                    control={<Switch checked={Boolean(v)} disabled size="small" color="success" />}
                    label={<Typography variant="body2" sx={{ fontSize: '0.9rem' }}>{k}</Typography>}
                    sx={{ m: 0, alignItems: 'center' }}
                  />
                ))}
              {!features && <Chip label="No flags loaded" size="small" />}
            </Stack>
          </Paper>
        </Grid>

        {isAdmin && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
                Admin Settings
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} lg={3}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 750, mb: 1.25 }}>
                    Database
                  </Typography>
                  <Stack spacing={1.25}>
                    <SettingRow label="Host" value={admin?.database?.host} />
                    <SettingRow label="Port" value={admin?.database?.port} />
                    <SettingRow label="DB" value={admin?.database?.database} />
                    <SettingRow label="User" value={admin?.database?.user} />
                  </Stack>
                </Grid>
                <Grid item xs={12} sm={6} lg={3}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 750, mb: 1.25 }}>
                    Elasticsearch
                  </Typography>
                  <Stack spacing={1.25}>
                    <SettingRow label="URL" value={admin?.elasticsearch?.url} />
                    <SettingRow label="Index" value={admin?.elasticsearch?.index} />
                  </Stack>
                </Grid>
                <Grid item xs={12} sm={6} lg={3}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 750, mb: 1.25 }}>
                    Qdrant
                  </Typography>
                  <Stack spacing={1.25}>
                    <SettingRow label="URL" value={admin?.qdrant?.url} />
                    <SettingRow label="Class" value={admin?.qdrant?.class} />
                  </Stack>
                </Grid>
                <Grid item xs={12} sm={6} lg={3}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 750, mb: 1.25 }}>
                    Storage
                  </Typography>
                  <SettingRow label="Path" value={admin?.storage?.storage_path} />
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
            sx={{ p: { xs: 2.5, md: 3 }, borderRadius: 3 }}
          >
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
              Dependencies Health
            </Typography>

            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2.5}
              alignItems={{ xs: 'flex-start', sm: 'center' }}
              sx={{ mb: 2.5 }}
            >
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
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 750, mb: 0.5 }}>
                  {overallParsed.short === 'OK'
                    ? 'All critical checks passing'
                    : overallParsed.short === 'WARN'
                      ? 'Some dependencies degraded'
                      : 'Dependency failures detected'}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.5 }}>
                  Live dependency telemetry · {String(health?.overall || 'unknown')}
                </Typography>
                {overallParsed.detail && (
                  <Typography
                    variant="body2"
                    color="warning.main"
                    sx={{ mt: 1, lineHeight: 1.45, wordBreak: 'break-word' }}
                  >
                    {overallParsed.detail}
                  </Typography>
                )}
              </Box>
            </Stack>

            <Divider sx={{ mb: 2.5 }} />

            <Grid container spacing={2}>
              {deps.map(([name, status]) => {
                const parsed = parseDependencyStatus(status)
                return (
                  <Grid key={name} item xs={12} sm={6} md={4} lg={3}>
                    <Box
                      sx={{
                        height: '100%',
                        minHeight: 0,
                        p: 1.75,
                        borderRadius: 2,
                        border: '1px solid',
                        borderColor: 'divider',
                        bgcolor: (t) =>
                          t.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.015)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: 1,
                      }}
                    >
                      <NeedleGauge
                        value={parsed.score}
                        label={name}
                        displayValue={parsed.short}
                        size={118}
                        status={parsed.tone}
                        help={{
                          title: `${name} health`,
                          body: `Live status for the “${name}” dependency. Needle maps healthy (100) → degraded (50) → down (0).`,
                          reading: String(status),
                          details: [
                            { label: 'Score', value: String(parsed.score) },
                            { label: 'Status', value: String(status) },
                          ],
                        }}
                      />
                      <Chip
                        size="small"
                        label={parsed.short === 'OK' ? 'Healthy' : parsed.short === 'WARN' ? 'Degraded' : 'Unhealthy'}
                        color={parsed.tone === 'ok' ? 'success' : parsed.tone === 'warn' ? 'warning' : 'error'}
                        variant="outlined"
                        sx={{ height: 22, fontWeight: 700, fontSize: '0.7rem' }}
                      />
                      {parsed.detail && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          title={parsed.detail}
                          sx={{
                            textAlign: 'center',
                            lineHeight: 1.4,
                            wordBreak: 'break-word',
                            display: '-webkit-box',
                            WebkitLineClamp: 3,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            width: '100%',
                            px: 0.25,
                          }}
                        >
                          {parsed.detail}
                        </Typography>
                      )}
                    </Box>
                  </Grid>
                )
              })}
              {deps.length === 0 && (
                <Grid item xs={12}>
                  <Chip label="No dependency data" size="small" />
                </Grid>
              )}
            </Grid>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
              MCP
            </Typography>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={4}>
                <SettingRow label="Status" value={mcp?.status} />
              </Grid>
              <Grid item xs={12} sm={4}>
                <SettingRow label="Version" value={mcp?.version} />
              </Grid>
              <Grid item xs={12} sm={4}>
                <SettingRow label="Capabilities" value={(mcp?.capabilities || []).join(', ')} />
              </Grid>
            </Grid>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1.5}
              alignItems={{ xs: 'stretch', sm: 'flex-start' }}
            >
              <TextField
                label="Execute Command (JSON)"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                minRows={2}
                maxRows={8}
                multiline
                fullWidth
                sx={{ '& .MuiInputBase-root': { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.9rem' } }}
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
                sx={{ flexShrink: 0, alignSelf: { sm: 'flex-start' }, mt: { sm: 1 } }}
              >
                Execute
              </Button>
            </Stack>
            {execResult && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 0.75, fontWeight: 700 }}>
                  Result
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    fontSize: '0.85rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    maxHeight: 280,
                    overflow: 'auto',
                  }}
                >
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
