import React from 'react'
import { Box, Paper, Typography, Grid, Chip, Stack, Divider, Button, TextField } from '@mui/material'
import { useGetSettingsQuery, useGetAdminSettingsQuery, useGetFeatureFlagsQuery, useGetDependenciesHealthQuery, useGetMcpStatusQuery, useExecuteToolMutation } from '../store/api'
import { useAppSelector } from '../hooks/redux'

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
              <Typography variant="body2">Allowed extensions: {(settings?.allowed_extensions || []).join(', ')}</Typography>
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Feature Flags
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {features && Object.entries(features).map(([k, v]) => (
                <Chip key={k} label={`${k}: ${v ? 'on' : 'off'}`} color={v ? 'success' : 'default'} size="small" />
              ))}
            </Stack>
          </Paper>
        </Grid>

        {isAdmin && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Admin Settings
              </Typography>
              {/* Note: Backend enforces RBAC; hide in UI if not admin */}
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
                  <Typography variant="subtitle2">Redis</Typography>
                  <Stack spacing={0.5}>
                    <Typography variant="body2">URL: {admin?.redis?.url}</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Ollama</Typography>
                  <Stack spacing={0.5}>
                    <Typography variant="body2">Base URL: {admin?.ollama?.base_url}</Typography>
                    <Typography variant="body2">Model: {admin?.ollama?.model}</Typography>
                    <Typography variant="body2">Timeout: {admin?.ollama?.timeout}</Typography>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Storage</Typography>
                  <Stack spacing={0.5}>
                    <Typography variant="body2">Temp: {admin?.storage?.temp_path}</Typography>
                    <Typography variant="body2">Path: {admin?.storage?.storage_path}</Typography>
                  </Stack>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        )}

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Dependencies Health
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>Overall: {health?.overall}</Typography>
            <Divider sx={{ mb: 1 }} />
            <Grid container spacing={2}>
              {health?.dependencies && Object.entries(health.dependencies).map(([name, status]) => (
                <Grid key={name} item>
                  <Chip label={`${name}: ${status}`} color={String(status) === 'healthy' ? 'success' : 'warning'} size="small" />
                </Grid>
              ))}
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