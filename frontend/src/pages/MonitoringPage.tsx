import React, { useMemo } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
  useTheme,
} from '@mui/material'
import {
  OpenInNew as OpenInNewIcon,
  Refresh as RefreshIcon,
  Circle as CircleIcon,
} from '@mui/icons-material'
import { motion } from 'framer-motion'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  Legend,
  BarChart,
  Bar,
} from 'recharts'
import { useGetMonitoringSnapshotQuery } from '../store/api'
import { PrecisionDial, NeedleGauge, ArcMeter, LiveTicker } from '../components/instruments'

const POLL_MS = 5000

function formatBytes(bytes?: number | null) {
  if (bytes == null || !Number.isFinite(bytes) || bytes < 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(Math.max(bytes, 1)) / Math.log(1024)), units.length - 1)
  const v = bytes / 1024 ** i
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}

function formatRps(v?: number | null) {
  if (v == null || !Number.isFinite(v)) return '—'
  if (v < 0.01) return '0.00'
  if (v < 1) return v.toFixed(2)
  if (v < 10) return v.toFixed(1)
  return v.toFixed(0)
}

function formatMs(v?: number | null) {
  if (v == null || !Number.isFinite(v)) return '—'
  if (v < 10) return `${v.toFixed(1)} ms`
  if (v < 1000) return `${Math.round(v)} ms`
  return `${(v / 1000).toFixed(2)} s`
}

function statusTone(status: string): 'ok' | 'warn' | 'error' {
  const s = status.toLowerCase()
  if (s === 'healthy' || s === 'ok' || s === 'up') return 'ok'
  if (s === 'degraded' || s === 'warn' || s === 'warning') return 'warn'
  return 'error'
}

function depShort(raw: string) {
  const head = raw.split(':')[0]?.trim().toLowerCase() || 'unknown'
  if (head === 'healthy' || head === 'ok') return 'OK'
  if (head === 'degraded' || head === 'warning') return 'WARN'
  return 'DOWN'
}

function depDetail(raw: string) {
  const idx = raw.indexOf(':')
  if (idx < 0) return null
  return raw.slice(idx + 1).trim() || null
}

const ChartCard: React.FC<{
  title: string
  subtitle?: string
  children: React.ReactNode
  height?: number
}> = ({ title, subtitle, children, height = 260 }) => (
  <Paper
    sx={{
      p: 2,
      height: '100%',
      borderRadius: 2.5,
      border: '1px solid',
      borderColor: 'divider',
      display: 'flex',
      flexDirection: 'column',
      minHeight: height + 72,
    }}
  >
    <Box sx={{ mb: 1.25 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 750, letterSpacing: '-0.01em' }}>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </Box>
    <Box sx={{ flex: 1, minHeight: height }}>{children}</Box>
  </Paper>
)

/**
 * Native live ops console — Prometheus-backed snapshot, not the Grafana welcome page.
 */
const MonitoringPage: React.FC = () => {
  const theme = useTheme()
  const dark = theme.palette.mode === 'dark'
  const { data, isFetching, isError, error, refetch, fulfilledTimeStamp } = useGetMonitoringSnapshotQuery(
    undefined,
    { pollingInterval: POLL_MS, refetchOnFocus: true, refetchOnReconnect: true }
  )

  const gauges = data?.gauges
  const deps = data?.dependencies
  const series = data?.series

  const traffic = useMemo(() => {
    const req = series?.request_rate || []
    const err = series?.error_rate || []
    const byT = new Map<number, { t: number; label: string; rps: number; errors: number }>()
    req.forEach((p: any) => byT.set(p.t, { t: p.t, label: p.label, rps: p.v || 0, errors: 0 }))
    err.forEach((p: any) => {
      const row = byT.get(p.t) || { t: p.t, label: p.label, rps: 0, errors: 0 }
      row.errors = p.v || 0
      byT.set(p.t, row)
    })
    return Array.from(byT.values()).sort((a, b) => a.t - b.t)
  }, [series])

  const latency = useMemo(
    () =>
      (series?.latency_s || []).map((p: any) => ({
        label: p.label,
        ms: (p.v || 0) * 1000,
      })),
    [series]
  )

  const cpuSeries = useMemo(
    () =>
      (series?.cpu || []).map((p: any) => ({
        label: p.label,
        cpu: p.v || 0,
      })),
    [series]
  )

  const statusBars = useMemo(
    () =>
      (data?.status_codes || []).map((r: any) => ({
        status: String(r.status),
        count: Number(r.value) || 0,
      })),
    [data?.status_codes]
  )

  const overall = String(data?.overall || 'unknown')
  const overallTone = statusTone(overall)
  const lastUpdated = fulfilledTimeStamp
    ? new Date(fulfilledTimeStamp).toLocaleTimeString()
    : '—'

  const chartStroke = dark ? '#38bdf8' : '#0284c7'
  const errStroke = dark ? '#f87171' : '#dc2626'
  const grid = dark ? 'rgba(148,163,184,0.12)' : 'rgba(15,23,42,0.08)'

  return (
    <Box sx={{ pb: 3 }}>
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        alignItems={{ xs: 'stretch', md: 'flex-start' }}
        justifyContent="space-between"
        spacing={1.5}
        sx={{ mb: 2 }}
      >
        <Box>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="h4" sx={{ fontWeight: 750, letterSpacing: '-0.02em' }}>
              Monitoring
            </Typography>
            <Chip
              size="small"
              icon={<CircleIcon sx={{ fontSize: '10px !important' }} />}
              label={overallTone === 'ok' ? 'Healthy' : overallTone === 'warn' ? 'Degraded' : 'Attention'}
              color={overallTone === 'ok' ? 'success' : overallTone === 'warn' ? 'warning' : 'error'}
              sx={{ fontWeight: 700 }}
            />
            <LiveTicker
              label="Poll"
              value={`${POLL_MS / 1000}s`}
              live={!isError}
              help={{
                title: 'Live poll',
                body: 'This console refreshes from /monitoring/snapshot on a fixed interval.',
                reading: `Every ${POLL_MS / 1000}s · last ${lastUpdated}`,
              }}
            />
          </Stack>
          <Typography variant="body2" color="text.secondary">
            Real-time API, host, worker, and dependency telemetry — updated {lastUpdated}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Button size="small" startIcon={<RefreshIcon />} onClick={() => refetch()} disabled={isFetching}>
            Refresh
          </Button>
          {data?.grafana_url && (
            <Button
              size="small"
              variant="outlined"
              endIcon={<OpenInNewIcon />}
              href={`${data.grafana_url}/d/indoc-overview/indoc-enterprise-overview?kiosk=tv&theme=dark`}
              target="_blank"
              rel="noopener noreferrer"
            >
              Grafana
            </Button>
          )}
        </Stack>
      </Stack>

      {isFetching && !data && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load monitoring snapshot
          {error && 'status' in (error as object) ? ` (${(error as any).status})` : ''}. Check API auth and
          Prometheus reachability.
        </Alert>
      )}

      {(data?.warnings || []).length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {(data?.warnings || []).join(' · ')}
        </Alert>
      )}

      {/* Instrument cluster */}
      <Paper
        component={motion.div}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        sx={{
          p: { xs: 1.5, md: 2 },
          mb: 2.5,
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
          background: dark
            ? 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%)'
            : 'linear-gradient(180deg, rgba(0,0,0,0.02) 0%, transparent 100%)',
        }}
      >
        <Typography
          variant="caption"
          sx={{ fontWeight: 750, letterSpacing: 0.8, textTransform: 'uppercase', color: 'text.secondary', mb: 1, display: 'block' }}
        >
          Live instrument cluster
        </Typography>
        <Grid container spacing={1.5} alignItems="center">
          <Grid item xs={6} sm={4} md={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <PrecisionDial
                value={Number(gauges?.cpu_pct) || 0}
                label="CPU"
                unit="%"
                precision={0}
                size={118}
                status={(gauges?.cpu_pct || 0) > 85 ? 'error' : (gauges?.cpu_pct || 0) > 65 ? 'warn' : 'ok'}
                help={{
                  title: 'Host CPU',
                  body: 'Current host CPU utilization sampled with the monitoring snapshot.',
                  reading: `${Number(gauges?.cpu_pct || 0).toFixed(1)}%`,
                }}
              />
            </Box>
          </Grid>
          <Grid item xs={6} sm={4} md={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <PrecisionDial
                value={Number(gauges?.memory_pct) || 0}
                label="Memory"
                unit="%"
                precision={0}
                size={118}
                status={(gauges?.memory_pct || 0) > 90 ? 'error' : (gauges?.memory_pct || 0) > 75 ? 'warn' : 'ok'}
                help={{
                  title: 'Host memory',
                  body: 'Percent of system memory in use.',
                  reading: `${Number(gauges?.memory_pct || 0).toFixed(1)}% · ${formatBytes(gauges?.memory_used_bytes)}`,
                  details: [
                    { label: 'Used', value: formatBytes(gauges?.memory_used_bytes) },
                    { label: 'Total', value: formatBytes(gauges?.memory_total_bytes) },
                    { label: 'API RSS', value: formatBytes(gauges?.process_rss_bytes) },
                  ],
                }}
              />
            </Box>
          </Grid>
          <Grid item xs={6} sm={4} md={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <ArcMeter
                value={Math.min(100, (Number(gauges?.request_rate_rps) || 0) * 20)}
                label="Traffic"
                subtitle={`${formatRps(gauges?.request_rate_rps)} rps`}
                unit="%"
                precision={0}
                size={112}
                status={(gauges?.request_rate_rps || 0) > 0 ? 'active' : 'idle'}
                help={{
                  title: 'Request rate',
                  body: 'HTTP requests/sec excluding the Prometheus scrape endpoint.',
                  reading: `${formatRps(gauges?.request_rate_rps)} rps`,
                }}
              />
            </Box>
          </Grid>
          <Grid item xs={6} sm={4} md={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <NeedleGauge
                value={Number(gauges?.latency_p95_ms ?? gauges?.latency_avg_ms) || 0}
                max={Math.max(500, Number(gauges?.latency_p95_ms ?? gauges?.latency_avg_ms) || 0) * 1.4}
                label="p95 latency"
                size={112}
                status={
                  (gauges?.latency_p95_ms || 0) > 1500
                    ? 'error'
                    : (gauges?.latency_p95_ms || 0) > 500
                      ? 'warn'
                      : 'ok'
                }
                displayValue={formatMs(gauges?.latency_p95_ms ?? gauges?.latency_avg_ms)}
                help={{
                  title: 'Latency',
                  body: 'p95 request duration when histogram data is available; otherwise rolling average.',
                  reading: `p95 ${formatMs(gauges?.latency_p95_ms)} · avg ${formatMs(gauges?.latency_avg_ms)}`,
                }}
              />
            </Box>
          </Grid>
          <Grid item xs={6} sm={4} md={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <NeedleGauge
                value={Number(gauges?.success_rate_pct) || 0}
                label="Success"
                unit="%"
                precision={1}
                size={112}
                status={
                  (gauges?.success_rate_pct ?? 100) < 95
                    ? 'error'
                    : (gauges?.success_rate_pct ?? 100) < 99
                      ? 'warn'
                      : 'ok'
                }
                help={{
                  title: 'Success rate',
                  body: 'Share of non-5xx traffic over the last 5 minutes.',
                  reading: `${Number(gauges?.success_rate_pct ?? 100).toFixed(1)}%`,
                  details: [{ label: 'Error rps', value: formatRps(gauges?.error_rate_rps) }],
                }}
              />
            </Box>
          </Grid>
          <Grid item xs={6} sm={4} md={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <PrecisionDial
                value={Number(gauges?.disk_pct) || 0}
                label="Disk"
                unit="%"
                precision={0}
                size={118}
                status={(gauges?.disk_pct || 0) > 90 ? 'error' : (gauges?.disk_pct || 0) > 80 ? 'warn' : 'ok'}
                help={{
                  title: 'Root disk',
                  body: 'Percent used on the root volume.',
                  reading: `${Number(gauges?.disk_pct || 0).toFixed(1)}% · ${formatBytes(gauges?.disk_used_bytes)}`,
                }}
              />
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* KPI strip */}
      <Grid container spacing={1.5} sx={{ mb: 2.5 }}>
        {[
          { label: 'API process', value: gauges?.backend_up ? 'UP' : 'DOWN', tone: gauges?.backend_up ? 'success' : 'error' },
          { label: 'WebSockets', value: String(gauges?.websockets ?? 0), tone: 'default' },
          { label: 'Celery workers', value: String(gauges?.celery_workers_online ?? 0), tone: 'default' },
          { label: 'Tasks running', value: String(gauges?.celery_tasks_running ?? 0), tone: 'default' },
          { label: 'API RSS', value: formatBytes(gauges?.process_rss_bytes), tone: 'default' },
          {
            label: 'Deps healthy',
            value: deps ? `${deps.healthy}/${deps.total}` : '—',
            tone: deps?.overall === 'healthy' ? 'success' : 'warning',
          },
        ].map((card) => (
          <Grid item xs={6} sm={4} md={2} key={card.label}>
            <Paper
              sx={{
                p: 1.5,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                height: '100%',
              }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, letterSpacing: 0.4 }}>
                {card.label}
              </Typography>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 750,
                  mt: 0.35,
                  fontVariantNumeric: 'tabular-nums',
                  color:
                    card.tone === 'success'
                      ? 'success.main'
                      : card.tone === 'error'
                        ? 'error.main'
                        : card.tone === 'warning'
                          ? 'warning.main'
                          : 'text.primary',
                }}
              >
                {card.value}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} lg={7}>
          <ChartCard title="Request traffic" subtitle="Requests/sec and 5xx error rate · last 30 minutes">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={traffic}>
                <defs>
                  <linearGradient id="rpsFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={chartStroke} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={chartStroke} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis tick={{ fontSize: 11 }} width={42} />
                <RechartsTooltip
                  contentStyle={{
                    background: dark ? '#0f172a' : '#fff',
                    border: `1px solid ${grid}`,
                    borderRadius: 8,
                  }}
                />
                <Legend />
                <Area type="monotone" dataKey="rps" name="req/s" stroke={chartStroke} fill="url(#rpsFill)" strokeWidth={2} />
                <Area type="monotone" dataKey="errors" name="5xx/s" stroke={errStroke} fill="transparent" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
        <Grid item xs={12} lg={5}>
          <ChartCard title="Latency" subtitle="Average request duration (ms) · last 30 minutes">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={latency}>
                <defs>
                  <linearGradient id="latFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#a78bfa" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis tick={{ fontSize: 11 }} width={48} />
                <RechartsTooltip
                  contentStyle={{
                    background: dark ? '#0f172a' : '#fff',
                    border: `1px solid ${grid}`,
                    borderRadius: 8,
                  }}
                  formatter={(v: any) => [`${Number(v).toFixed(1)} ms`, 'latency']}
                />
                <Area type="monotone" dataKey="ms" name="ms" stroke="#a78bfa" fill="url(#latFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
        <Grid item xs={12} lg={7}>
          <ChartCard title="CPU utilization" subtitle="Host CPU % · last 30 minutes" height={220}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cpuSeries}>
                <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={36} />
                <RechartsTooltip
                  contentStyle={{
                    background: dark ? '#0f172a' : '#fff',
                    border: `1px solid ${grid}`,
                    borderRadius: 8,
                  }}
                />
                <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#34d399" fill="rgba(52,211,153,0.18)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
        <Grid item xs={12} lg={5}>
          <ChartCard title="Status codes · 1h" subtitle="Request volume by HTTP status" height={220}>
            {statusBars.length === 0 ? (
              <Box sx={{ height: '100%', display: 'grid', placeItems: 'center' }}>
                <Typography color="text.secondary">No traffic in window</Typography>
              </Box>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusBars} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid stroke={grid} strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="status" width={48} tick={{ fontSize: 12, fontWeight: 700 }} />
                  <RechartsTooltip
                    contentStyle={{
                      background: dark ? '#0f172a' : '#fff',
                      border: `1px solid ${grid}`,
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="count" name="requests" fill={chartStroke} radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2, borderRadius: 2.5, border: '1px solid', borderColor: 'divider', height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 750, mb: 1.5 }}>
              Dependencies
            </Typography>
            <Stack spacing={1}>
              {Object.entries(deps?.dependencies || {}).map(([name, raw]) => {
                const short = depShort(String(raw))
                const detail = depDetail(String(raw))
                const tone = statusTone(String(raw))
                return (
                  <Box
                    key={name}
                    sx={{
                      display: 'flex',
                      gap: 1.25,
                      alignItems: 'flex-start',
                      p: 1.1,
                      borderRadius: 1.5,
                      border: '1px solid',
                      borderColor: 'divider',
                      bgcolor: dark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.015)',
                    }}
                  >
                    <Chip
                      size="small"
                      label={short}
                      color={tone === 'ok' ? 'success' : tone === 'warn' ? 'warning' : 'error'}
                      sx={{ height: 22, fontWeight: 750, minWidth: 56 }}
                    />
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, textTransform: 'capitalize' }}>
                        {name}
                      </Typography>
                      {detail && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: 'block', wordBreak: 'break-word', lineHeight: 1.35 }}
                        >
                          {detail}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                )
              })}
              {!deps && (
                <Typography variant="body2" color="text.secondary">
                  Waiting for dependency probes…
                </Typography>
              )}
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 2, borderRadius: 2.5, border: '1px solid', borderColor: 'divider', height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 750, mb: 1 }}>
              Top endpoints · 1h
            </Typography>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 750 }}>Method</TableCell>
                  <TableCell sx={{ fontWeight: 750 }}>Endpoint</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 750 }}>
                    Requests
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(data?.top_endpoints || []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>
                      <Typography variant="body2" color="text.secondary">
                        No application traffic in the last hour (scrape traffic excluded).
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {(data?.top_endpoints || []).map((row: any) => (
                  <TableRow key={`${row.method}-${row.endpoint}`} hover>
                    <TableCell sx={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontWeight: 700 }}>
                      {row.method || '—'}
                    </TableCell>
                    <TableCell
                      sx={{
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                        fontSize: '0.85rem',
                        maxWidth: 420,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={row.endpoint}
                    >
                      {row.endpoint || '—'}
                    </TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', fontWeight: 700 }}>
                      {Math.round(Number(row.value) || 0).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default MonitoringPage
