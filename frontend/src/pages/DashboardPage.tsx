import React, { useMemo } from 'react';
import { Box, Grid, Paper, Typography, useTheme, Chip, LinearProgress } from '@mui/material';
import { useNavigate } from 'react-router-dom'
import { useGetAnalyticsSummaryQuery, useGetAnalyticsTimeseriesQuery, useGetAnalyticsStorageQuery, useGetProcessingAnalyticsQuery, useGetDocumentsQuery } from '../store/api';
import { ResponsiveContainer, LineChart, Line, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, Legend, PieChart, Pie, Cell, RadialBarChart, RadialBar, BarChart, Bar } from 'recharts'
import { TrendingUp as TrendingUpIcon, TrendingDown as TrendingDownIcon } from '@mui/icons-material'

const DashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const theme = useTheme()
  const { data: summary } = useGetAnalyticsSummaryQuery(undefined as any, { pollingInterval: 5000 })
  const { data: timeseries } = useGetAnalyticsTimeseriesQuery({ days: 30 } as any, { pollingInterval: 10000 })
  const { data: storage } = useGetAnalyticsStorageQuery(undefined as any, { pollingInterval: 15000 })
  const { data: processing } = useGetProcessingAnalyticsQuery(undefined as any, { pollingInterval: 10000 })

  // Get real document counts for accurate queue metrics
  const { data: documentsData } = useGetDocumentsQuery({ skip: 0, limit: 1000 }, { pollingInterval: 5000 })

  // Transform timeseries data with formatted dates
  const activityData = useMemo(() => {
    if (!timeseries) return []

    // Create a map of all data by date
    const dataByDate = new Map();

    // Parse uploads
    (timeseries.uploads || []).forEach((d: any) => {
      const date = new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dataByDate.has(date)) dataByDate.set(date, { day: date, uploads: 0, views: 0, searches: 0 })
      dataByDate.get(date).uploads = d.count
    });

    // Parse views
    (timeseries.views || []).forEach((d: any) => {
      const date = new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dataByDate.has(date)) dataByDate.set(date, { day: date, uploads: 0, views: 0, searches: 0 })
      dataByDate.get(date).views = d.count
    });

    // Parse searches
    (timeseries.searches || []).forEach((d: any) => {
      const date = new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dataByDate.has(date)) dataByDate.set(date, { day: date, uploads: 0, views: 0, searches: 0 })
      dataByDate.get(date).searches = d.count
    });

    // Fill in last 30 days with zeros if missing
    const result = [];
    const today = new Date();
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      result.push(dataByDate.get(dateStr) || { day: dateStr, uploads: 0, views: 0, searches: 0 });
    }

    return result;
  }, [timeseries])
  const storageByType = useMemo(() => {
    const items = (storage?.by_type || []).map((r: any) => ({
      name: (r.file_type || 'UNK').toUpperCase(),
      value: r.bytes
    }))
    const total = items.reduce((sum: number, item: any) => sum + item.value, 0)
    return items.map((item: any) => ({
      ...item,
      percent: total > 0 ? ((item.value / total) * 100).toFixed(0) : 0
    }))
  }, [storage])

  // Calculate real queue KPIs from documents data (no hard-coding)
  const realStatusCounts = useMemo(() => {
    const docs = documentsData?.documents || []
    const counts: Record<string, number> = {}
    docs.forEach((doc: any) => {
      counts[doc.status] = (counts[doc.status] || 0) + 1
    })
    return counts
  }, [documentsData])

  const inQueueNow = (realStatusCounts['uploaded'] || 0) + (realStatusCounts['processing'] || 0) + (realStatusCounts['text_extracted'] || 0)
  const processingNow = realStatusCounts['processing'] || 0
  const failedNow = realStatusCounts['failed'] || 0
  const indexedCount = realStatusCounts['indexed'] || 0
  const avgProcessSecs = useMemo(() => {
    const rows = processing?.avg_time_to_process_by_type || []
    if (!rows.length) return 0
    const total = rows.reduce((acc: number, r: any) => acc + (Number(r.avg_seconds) || 0), 0)
    return total / rows.length
  }, [processing])

  const formatSeconds = (totalSeconds: number) => {
    if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return '0:00'
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = Math.round(totalSeconds % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const formatBytes = (bytes: number) => {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
    const value = bytes / Math.pow(1024, idx)
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[idx]}`
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, mb: 4 }}>Dashboard</Typography>

      {/* Key Performance Indicators */}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>Key Metrics</Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3} onClick={() => navigate('/documents')} style={{ cursor: 'pointer' }}>
          <Paper sx={{ p: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', transition: 'border-color 0.2s ease', '&:hover': { borderColor: 'primary.main' } }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>TOTAL DOCUMENTS</Typography>
            <Typography variant="h5" sx={{ fontWeight: 600, my: 0.5, color: 'text.primary' }}>{summary?.totals?.documents ?? 0}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>Click to view all</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', transition: 'border-color 0.2s ease', '&:hover': { borderColor: 'success.main' } }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>SUCCESSFULLY INDEXED</Typography>
            <Typography variant="h5" sx={{ fontWeight: 600, my: 0.5, color: 'success.main' }}>{indexedCount}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>Ready for search & chat</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', transition: 'border-color 0.2s ease', '&:hover': { borderColor: 'warning.main' } }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>IN PROCESSING QUEUE</Typography>
            <Typography variant="h5" sx={{ fontWeight: 600, my: 0.5, color: 'warning.main' }}>{inQueueNow}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>Being processed</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', transition: 'border-color 0.2s ease', '&:hover': { borderColor: 'error.main' } }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>PROCESSING FAILURES</Typography>
            <Typography variant="h5" sx={{ fontWeight: 600, my: 0.5, color: 'error.main' }}>{failedNow}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>Require attention</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Operational Metrics */}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>Operational Status</Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={2.4}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>PROCESSING NOW</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'info.main' }}>{processingNow}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>IN QUEUE</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'warning.main' }}>{inQueueNow}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>FAILED</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'error.main' }}>{failedNow}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>AVG PROCESS TIME</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>{formatSeconds(Number(avgProcessSecs) || 0)}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={2.4}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>STORAGE USED</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'success.main' }}>{formatBytes(summary?.totals?.storage_bytes ?? 0)}</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Analytics Charts - Using theme tokens for colors per AI Guide §8 */}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>Performance Analytics</Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, borderRadius: 3, height: 400, background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.mode === 'dark' ? 'rgba(25, 118, 210, 0.05)' : 'rgba(25, 118, 210, 0.02)'} 100%)` }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>User Activity Trends (30 days)</Typography>
            <ResponsiveContainer width="100%" height="88%">
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="uploadsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.success.main} stopOpacity={0.8} />
                    <stop offset="95%" stopColor={theme.palette.success.main} stopOpacity={0.1} />
                  </linearGradient>
                  <linearGradient id="viewsGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.info.main} stopOpacity={0.8} />
                    <stop offset="95%" stopColor={theme.palette.info.main} stopOpacity={0.1} />
                  </linearGradient>
                  <linearGradient id="searchesGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.warning.main} stopOpacity={0.8} />
                    <stop offset="95%" stopColor={theme.palette.warning.main} stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} opacity={0.3} />
                <XAxis
                  dataKey="day"
                  stroke={theme.palette.text.secondary}
                  style={{ fontSize: '0.7rem' }}
                  interval="preserveStartEnd"
                  tickFormatter={(value, index) => {
                    // Show only every 5th day to avoid crowding
                    if (index % 5 === 0 || index === activityData.length - 1) return value
                    return ''
                  }}
                />
                <YAxis stroke={theme.palette.text.secondary} style={{ fontSize: '0.75rem' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                    boxShadow: theme.shadows[4]
                  }}
                  labelStyle={{ color: theme.palette.text.primary, fontWeight: 600 }}
                  formatter={(value: any, name) => [value, name.charAt(0).toUpperCase() + name.slice(1)]}
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '10px' }} />
                <Area type="monotone" dataKey="uploads" stroke={theme.palette.success.main} fill="url(#uploadsGrad)" strokeWidth={2.5} animationDuration={1200} />
                <Area type="monotone" dataKey="views" stroke={theme.palette.info.main} fill="url(#viewsGrad)" strokeWidth={2.5} animationDuration={1200} animationBegin={200} />
                <Area type="monotone" dataKey="searches" stroke={theme.palette.warning.main} fill="url(#searchesGrad)" strokeWidth={2.5} animationDuration={1200} animationBegin={400} />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, borderRadius: 3, height: 400, background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.mode === 'dark' ? 'rgba(76, 175, 80, 0.05)' : 'rgba(76, 175, 80, 0.02)'} 100%)` }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Storage by File Type</Typography>
            <ResponsiveContainer width="100%" height="85%">
              <BarChart
                data={storageByType.slice(0, 6).map((item: any, idx: number) => ({
                  name: item.name,
                  value: item.value,
                  percent: Number(item.percent),
                  fill: [theme.palette.primary.main, theme.palette.success.main, theme.palette.info.main, theme.palette.warning.main, theme.palette.error.main, theme.palette.secondary.main][idx % 6]
                }))}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} opacity={0.2} horizontal={true} vertical={false} />
                <XAxis
                  type="number"
                  stroke={theme.palette.text.secondary}
                  style={{ fontSize: '0.7rem' }}
                  tickFormatter={(value) => formatBytes(value)}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke={theme.palette.text.secondary}
                  style={{ fontSize: '0.75rem', fontWeight: 600 }}
                  width={60}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                    padding: '12px',
                    boxShadow: theme.shadows[4]
                  }}
                  labelStyle={{ color: theme.palette.text.primary, fontWeight: 600, marginBottom: 4 }}
                  formatter={(value: any, name: any, props: any) => [
                    `${formatBytes(Number(value))} (${props.payload.percent}%)`,
                    props.payload.name
                  ]}
                  cursor={{ fill: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' }}
                />
                <Bar
                  dataKey="value"
                  radius={[0, 8, 8, 0]}
                  animationDuration={1200}
                  label={{
                    position: 'right',
                    fill: theme.palette.text.primary,
                    fontSize: 11,
                    fontWeight: 600,
                    formatter: (value: number, entry: any, index: number) => {
                      const item = storageByType.slice(0, 6)[index];
                      return item ? `${item.percent}%` : '';
                    }
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Processing Pipeline Ticker - Live per-stage throughput */}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>Processing Pipeline</Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3, borderRadius: 3, background: `linear-gradient(90deg, ${theme.palette.background.paper} 0%, ${theme.palette.mode === 'dark' ? 'rgba(99, 102, 241, 0.08)' : 'rgba(99, 102, 241, 0.03)'} 100%)` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              {/* Upload Stage */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.5, borderRadius: 2, bgcolor: theme.palette.mode === 'dark' ? 'rgba(76, 175, 80, 0.15)' : 'rgba(76, 175, 80, 0.1)', border: `2px solid ${theme.palette.success.main}`, minWidth: 140 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: theme.palette.success.main, animation: processingNow > 0 ? 'pulse 2s ease-in-out infinite' : 'none', '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } } }} />
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', fontWeight: 600 }}>UPLOAD</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: theme.palette.success.main }}>{summary?.totals?.documents ?? 0}</Typography>
                </Box>
              </Box>
              <Typography sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '1.2rem' }}>→</Typography>

              {/* PostgreSQL Stage */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.5, borderRadius: 2, bgcolor: theme.palette.mode === 'dark' ? 'rgba(25, 118, 210, 0.15)' : 'rgba(25, 118, 210, 0.1)', border: `2px solid ${theme.palette.primary.main}`, minWidth: 140 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: theme.palette.primary.main, animation: processingNow > 0 ? 'pulse 2s ease-in-out infinite 0.3s' : 'none' }} />
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', fontWeight: 600 }}>POSTGRESQL</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: theme.palette.primary.main }}>{summary?.totals?.documents ?? 0}</Typography>
                </Box>
              </Box>
              <Typography sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '1.2rem' }}>→</Typography>

              {/* Elasticsearch Stage */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.5, borderRadius: 2, bgcolor: theme.palette.mode === 'dark' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(6, 182, 212, 0.1)', border: `2px solid ${theme.palette.info.main}`, minWidth: 140 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: theme.palette.info.main, animation: processingNow > 0 ? 'pulse 2s ease-in-out infinite 0.6s' : 'none' }} />
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', fontWeight: 600 }}>ELASTICSEARCH</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: theme.palette.info.main }}>{indexedCount}</Typography>
                </Box>
              </Box>
              <Typography sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '1.2rem' }}>→</Typography>

              {/* Qdrant Stage */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.5, borderRadius: 2, bgcolor: theme.palette.mode === 'dark' ? 'rgba(255, 193, 7, 0.15)' : 'rgba(255, 193, 7, 0.1)', border: `2px solid ${theme.palette.warning.main}`, minWidth: 140 }}>
                <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: theme.palette.warning.main, animation: processingNow > 0 ? 'pulse 2s ease-in-out infinite 0.9s' : 'none' }} />
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', fontWeight: 600 }}>QDRANT</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: theme.palette.warning.main }}>{indexedCount}</Typography>
                </Box>
              </Box>
              <Typography sx={{ color: 'text.secondary', fontWeight: 700, fontSize: '1.2rem' }}>✓</Typography>

              {/* Completion Stage */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.5, borderRadius: 2, bgcolor: theme.palette.mode === 'dark' ? 'rgba(76, 175, 80, 0.20)' : 'rgba(76, 175, 80, 0.15)', border: `2px dashed ${theme.palette.success.main}`, minWidth: 120 }}>
                <Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', fontWeight: 600 }}>COMPLETE</Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, color: theme.palette.success.dark }}>{indexedCount}</Typography>
                </Box>
              </Box>
            </Box>
            {failedNow > 0 && (
              <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip label={`${failedNow} Failed`} color="error" size="small" sx={{ fontWeight: 600 }} />
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>Require attention</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Secondary Metrics */}
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>System Health</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>UPLOADS (30D)</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>{summary?.totals?.events?.uploads ?? 0}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>VIEWS (30D)</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>{summary?.totals?.events?.views ?? 0}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>SEARCHES (30D)</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>{summary?.totals?.events?.searches ?? 0}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 500 }}>FILE TYPES</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>{summary?.documents_by_type?.length ?? 0}</Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;