import React, { useMemo } from 'react'
import { Box, Grid, Paper, Typography, useTheme, Chip } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  useGetAnalyticsSummaryQuery,
  useGetAnalyticsTimeseriesQuery,
  useGetAnalyticsStorageQuery,
  useGetProcessingAnalyticsQuery,
  useGetDocumentsQuery,
} from '../store/api'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  BarChart,
  Bar,
} from 'recharts'
import { PrecisionDial, ArcMeter, NeedleGauge, SegmentRing, LiveTicker } from '../components/instruments'
import type { SegmentStatus } from '../components/instruments'

const tileMotion = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45 },
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const theme = useTheme()
  const { data: summary } = useGetAnalyticsSummaryQuery(undefined as any, { pollingInterval: 5000 })
  const { data: timeseries } = useGetAnalyticsTimeseriesQuery({ days: 30 } as any, { pollingInterval: 10000 })
  const { data: storage } = useGetAnalyticsStorageQuery(undefined as any, { pollingInterval: 15000 })
  const { data: processing } = useGetProcessingAnalyticsQuery(undefined as any, { pollingInterval: 10000 })
  const { data: documentsData } = useGetDocumentsQuery({ skip: 0, limit: 1000 }, { pollingInterval: 5000 })

  const activityData = useMemo(() => {
    if (!timeseries) return []
    const dataByDate = new Map()
    ;(timeseries.uploads || []).forEach((d: any) => {
      const date = new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dataByDate.has(date)) dataByDate.set(date, { day: date, uploads: 0, views: 0, searches: 0 })
      dataByDate.get(date).uploads = d.count
    })
    ;(timeseries.views || []).forEach((d: any) => {
      const date = new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dataByDate.has(date)) dataByDate.set(date, { day: date, uploads: 0, views: 0, searches: 0 })
      dataByDate.get(date).views = d.count
    })
    ;(timeseries.searches || []).forEach((d: any) => {
      const date = new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dataByDate.has(date)) dataByDate.set(date, { day: date, uploads: 0, views: 0, searches: 0 })
      dataByDate.get(date).searches = d.count
    })
    const result = []
    const today = new Date()
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today)
      date.setDate(date.getDate() - i)
      const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      result.push(dataByDate.get(dateStr) || { day: dateStr, uploads: 0, views: 0, searches: 0 })
    }
    return result
  }, [timeseries])

  const storageByType = useMemo(() => {
    const items = (storage?.by_type || []).map((r: any) => ({
      name: (r.file_type || 'UNK').toUpperCase(),
      value: r.bytes,
    }))
    const total = items.reduce((sum: number, item: any) => sum + item.value, 0)
    return items.map((item: any) => ({
      ...item,
      percent: total > 0 ? ((item.value / total) * 100).toFixed(0) : 0,
    }))
  }, [storage])

  const realStatusCounts = useMemo(() => {
    const docs = documentsData?.documents || []
    const counts: Record<string, number> = {}
    docs.forEach((doc: any) => {
      counts[doc.status] = (counts[doc.status] || 0) + 1
    })
    return counts
  }, [documentsData])

  const totalDocs = summary?.totals?.documents ?? documentsData?.documents?.length ?? 0
  const inQueueNow =
    (realStatusCounts['uploaded'] || 0) +
    (realStatusCounts['processing'] || 0) +
    (realStatusCounts['text_extracted'] || 0)
  const processingNow = realStatusCounts['processing'] || 0
  const failedNow = realStatusCounts['failed'] || 0
  const indexedCount = realStatusCounts['indexed'] || 0
  const indexedPct = totalDocs > 0 ? (indexedCount / totalDocs) * 100 : 0
  const queueCap = Math.max(totalDocs, 10)
  const queuePct = Math.min(100, (inQueueNow / queueCap) * 100)
  const failPct = totalDocs > 0 ? (failedNow / totalDocs) * 100 : 0
  const storageBytes = summary?.totals?.storage_bytes ?? 0
  const storageSoftMax = Math.max(storageBytes, 1) * (storageBytes > 0 ? 1.25 : 1)
  const storagePct = Math.min(100, (storageBytes / storageSoftMax) * 100)

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

  const processGaugeMax = Math.max(avgProcessSecs * 1.5, 60)
  const processGaugeValue = Math.min(processGaugeMax, avgProcessSecs)

  const pipelineSegments: { key: string; label: string; status: SegmentStatus; value: number }[] = [
    {
      key: 'upload',
      label: 'Upload',
      status: totalDocs > 0 ? 'complete' : 'pending',
      value: totalDocs,
    },
    {
      key: 'postgres',
      label: 'Postgres',
      status: processingNow > 0 ? 'active' : totalDocs > 0 ? 'complete' : 'pending',
      value: totalDocs,
    },
    {
      key: 'es',
      label: 'Elastic',
      status: indexedCount > 0 ? 'complete' : processingNow > 0 ? 'active' : 'pending',
      value: indexedCount,
    },
    {
      key: 'qdrant',
      label: 'Qdrant',
      status: indexedCount > 0 ? 'complete' : inQueueNow > 0 ? 'active' : 'pending',
      value: indexedCount,
    },
    {
      key: 'done',
      label: 'Ready',
      status: failedNow > 0 && indexedCount === 0 ? 'failed' : indexedCount > 0 ? 'complete' : 'pending',
      value: indexedCount,
    },
  ]

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          Dashboard
        </Typography>
        <LiveTicker label="Live telemetry" value={`${totalDocs} docs`} live />
      </Box>

      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>
        Instrument Cluster
      </Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            component={motion.div}
            {...tileMotion}
            onClick={() => navigate('/documents')}
            sx={{
              p: 2,
              borderRadius: 3,
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'center',
              '&:hover': { borderColor: 'primary.main' },
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <PrecisionDial
              value={indexedPct}
              label="Indexed"
              unit="%"
              precision={1}
              size={150}
              status={indexedPct >= 90 ? 'ok' : indexedPct >= 50 ? 'warn' : 'active'}
            />
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            component={motion.div}
            {...tileMotion}
            transition={{ ...tileMotion.transition, delay: 0.05 }}
            sx={{ p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'center' }}
          >
            <ArcMeter
              value={queuePct}
              label="Queue"
              subtitle={`${inQueueNow} in flight`}
              unit="%"
              precision={0}
              size={140}
              status={inQueueNow > 0 ? 'warn' : 'ok'}
            />
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            component={motion.div}
            {...tileMotion}
            transition={{ ...tileMotion.transition, delay: 0.1 }}
            sx={{ p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'center' }}
          >
            <NeedleGauge
              value={failPct}
              label="Failure rate"
              unit="%"
              precision={1}
              size={140}
              status={failPct > 5 ? 'error' : failPct > 0 ? 'warn' : 'ok'}
              displayValue={`${failedNow}`}
            />
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            component={motion.div}
            {...tileMotion}
            transition={{ ...tileMotion.transition, delay: 0.15 }}
            sx={{ p: 2, borderRadius: 3, border: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'center' }}
          >
            <NeedleGauge
              value={processGaugeValue}
              max={processGaugeMax}
              label="Avg process"
              size={140}
              status="active"
              displayValue={formatSeconds(Number(avgProcessSecs) || 0)}
            />
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, borderRadius: 3, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Typography variant="subtitle2" sx={{ mb: 1, alignSelf: 'flex-start', color: 'text.secondary', fontWeight: 700 }}>
              Processing Pipeline
            </Typography>
            <SegmentRing
              segments={pipelineSegments}
              size={200}
              centerLabel="Ready"
              centerValue={String(indexedCount)}
            />
            {failedNow > 0 && (
              <Chip sx={{ mt: 1 }} label={`${failedNow} Failed`} color="error" size="small" />
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, borderRadius: 3, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <ArcMeter
              value={storagePct}
              label="Storage"
              subtitle={formatBytes(storageBytes)}
              unit="%"
              precision={0}
              size={160}
              status="ok"
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              Processing now: {processingNow}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, borderRadius: 3, height: '100%' }}>
            <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary', fontWeight: 700 }}>
              System Pulse (30d)
            </Typography>
            <Grid container spacing={2}>
              {[
                { label: 'Uploads', value: summary?.totals?.events?.uploads ?? 0 },
                { label: 'Views', value: summary?.totals?.events?.views ?? 0 },
                { label: 'Searches', value: summary?.totals?.events?.searches ?? 0 },
                { label: 'File types', value: summary?.documents_by_type?.length ?? 0 },
              ].map((item) => (
                <Grid item xs={6} key={item.label}>
                  <LiveTicker label={item.label} value={item.value} live={false} />
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.secondary' }}>
        Performance Analytics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 2 }}>
        <Grid item xs={12} md={8}>
          <Paper
            sx={{
              p: 3,
              borderRadius: 3,
              height: 400,
              background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${
                theme.palette.mode === 'dark' ? 'rgba(25, 118, 210, 0.05)' : 'rgba(25, 118, 210, 0.02)'
              } 100%)`,
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              User Activity Trends (30 days)
            </Typography>
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
                  tickFormatter={(value, index) =>
                    index % 5 === 0 || index === activityData.length - 1 ? value : ''
                  }
                />
                <YAxis stroke={theme.palette.text.secondary} style={{ fontSize: '0.75rem' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                    boxShadow: theme.shadows[4],
                  }}
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
          <Paper
            sx={{
              p: 3,
              borderRadius: 3,
              height: 400,
              background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${
                theme.palette.mode === 'dark' ? 'rgba(76, 175, 80, 0.05)' : 'rgba(76, 175, 80, 0.02)'
              } 100%)`,
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              Storage by File Type
            </Typography>
            <ResponsiveContainer width="100%" height="85%">
              <BarChart
                data={storageByType.slice(0, 6).map((item: any, idx: number) => ({
                  name: item.name,
                  value: item.value,
                  percent: Number(item.percent),
                  fill: [
                    theme.palette.primary.main,
                    theme.palette.success.main,
                    theme.palette.info.main,
                    theme.palette.warning.main,
                    theme.palette.error.main,
                    theme.palette.secondary.main,
                  ][idx % 6],
                }))}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} opacity={0.2} horizontal vertical={false} />
                <XAxis type="number" stroke={theme.palette.text.secondary} style={{ fontSize: '0.7rem' }} tickFormatter={(v) => formatBytes(v)} />
                <YAxis type="category" dataKey="name" stroke={theme.palette.text.secondary} style={{ fontSize: '0.75rem', fontWeight: 600 }} width={60} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                  }}
                  formatter={(value: any, _name: any, props: any) => [
                    `${formatBytes(Number(value))} (${props.payload.percent}%)`,
                    props.payload.name,
                  ]}
                />
                <Bar dataKey="value" radius={[0, 8, 8, 0]} animationDuration={1200} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default DashboardPage
