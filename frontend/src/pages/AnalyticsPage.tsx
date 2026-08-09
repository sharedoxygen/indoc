import React from 'react'
import { Box, Paper, Typography, Grid, Chip, LinearProgress } from '@mui/material'
import { useGetAnalyticsSummaryQuery } from '../store/api'

const bytesToSize = (bytes: number): string => {
    if (!bytes || bytes <= 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

const AnalyticsPage: React.FC = () => {
    const { data: summary, isLoading: loadingSummary } = useGetAnalyticsSummaryQuery(undefined as any)

    return (
        <Box>
            <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, mb: 1 }}>
                Analytics 📈
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 4, fontSize: '1.1rem' }}>
                Business insights across documents, storage, and activity
            </Typography>

            <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3, borderRadius: 3 }}>
                        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Total Documents</Typography>
                        <Typography variant="h3" sx={{ fontWeight: 700 }}>
                            {loadingSummary ? '…' : summary?.totals?.documents ?? 0}
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3, borderRadius: 3 }}>
                        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Total Storage</Typography>
                        <Typography variant="h3" sx={{ fontWeight: 700 }}>
                            {loadingSummary ? '…' : bytesToSize(summary?.totals?.storage_bytes ?? 0)}
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3, borderRadius: 3 }}>
                        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>Events (30d)</Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {['uploads', 'views', 'downloads', 'searches'].map((k) => (
                                <Chip key={k} label={`${k}: ${summary?.totals?.events?.[k] ?? 0}`} />
                            ))}
                        </Box>
                    </Paper>
                </Grid>
            </Grid>

            <Grid container spacing={3} sx={{ mt: 1 }}>
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3, borderRadius: 3 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Documents by Type</Typography>
                        {loadingSummary ? (
                            <LinearProgress />
                        ) : (
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 1 }}>
                                {(summary?.documents_by_type || []).map((row: any) => (
                                    <React.Fragment key={row.file_type}>
                                        <Typography>{row.file_type?.toUpperCase()}</Typography>
                                        <Typography color="text.secondary">{row.count}</Typography>
                                        <Typography color="text.secondary">{bytesToSize(row.total_size)}</Typography>
                                    </React.Fragment>
                                ))}
                            </Box>
                        )}
                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper sx={{ p: 3, borderRadius: 3 }}>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Top Uploaders</Typography>
                        {loadingSummary ? (
                            <LinearProgress />
                        ) : (
                            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 1 }}>
                                {(summary?.top_uploaders || []).map((row: any) => (
                                    <React.Fragment key={row.user_email}>
                                        <Typography>{row.user_email}</Typography>
                                        <Typography color="text.secondary">{row.uploads}</Typography>
                                    </React.Fragment>
                                ))}
                            </Box>
                        )}
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    )
}

export default AnalyticsPage


