/**
 * System Log Viewer Page (Admin Only)
 * 
 * Provides comprehensive log viewing, filtering, and real-time tailing
 * Per AI Prompt Engineering Guide §8: Uses theme tokens only
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
    Box,
    Container,
    Typography,
    Paper,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    TextField,
    Button,
    Chip,
    IconButton,
    Switch,
    FormControlLabel,
    Alert,
    CircularProgress,
    Divider,
    Grid,
    Card,
    CardContent,
    Stack,
    Tooltip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions
} from '@mui/material'
import {
    Refresh as RefreshIcon,
    Download as DownloadIcon,
    Delete as DeleteIcon,
    Search as SearchIcon,
    PlayArrow as PlayIcon,
    Stop as StopIcon,
    Error as ErrorIcon,
    Warning as WarningIcon,
    Info as InfoIcon
} from '@mui/icons-material'
import { useSnackbar } from 'notistack'
import { useAppSelector } from '../hooks/redux'

interface LogEntry {
    timestamp: string
    level: string
    logger: string
    message: string
    line_number: number
    exception?: string
}

interface LogStats {
    total_lines: number
    error_count: number
    warning_count: number
    info_count: number
    last_error?: string
    last_error_time?: string
    file_size_mb: number
    last_modified: string
}

const LogViewerPage: React.FC = () => {
    const { enqueueSnackbar } = useSnackbar()
    const user = useAppSelector(state => state.auth.user)

    // State
    const [availableLogs, setAvailableLogs] = useState<string[]>([])
    const [selectedLog, setSelectedLog] = useState<string>('')
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [stats, setStats] = useState<LogStats | null>(null)
    const [loading, setLoading] = useState(false)
    const [autoRefresh, setAutoRefresh] = useState(false)
    const [realTime, setRealTime] = useState(false)
    const [level, setLevel] = useState<string>('all')
    const [searchTerm, setSearchTerm] = useState('')
    const [lines, setLines] = useState(100)
    const [selectedLogEntry, setSelectedLogEntry] = useState<LogEntry | null>(null)
    const [detailsOpen, setDetailsOpen] = useState(false)

    // Refs
    const logContainerRef = useRef<HTMLDivElement>(null)
    const wsRef = useRef<WebSocket | null>(null)
    const autoRefreshInterval = useRef<NodeJS.Timeout | null>(null)

    // Check if user is admin
    const isAdmin = user?.role === 'Admin'

    // Fetch available logs
    const fetchAvailableLogs = useCallback(async () => {
        try {
            const token = localStorage.getItem('token')
            const response = await fetch('http://localhost:8000/api/v1/logs/available', {
                headers: { 'Authorization': `Bearer ${token}` }
            })

            if (response.ok) {
                const data = await response.json()
                setAvailableLogs(data)
                // Set first available log as default if no log is selected
                if (data.length > 0 && (!selectedLog || !data.includes(selectedLog))) {
                    setSelectedLog(data[0])
                }
            }
        } catch (error) {
            console.error('Failed to fetch available logs:', error)
        }
    }, [selectedLog])

    // Fetch log stats
    const fetchStats = useCallback(async () => {
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`http://localhost:8000/api/v1/logs/stats/${selectedLog}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })

            if (response.ok) {
                const data = await response.json()
                setStats(data)
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error)
        }
    }, [selectedLog])

    // Fetch logs
    const fetchLogs = useCallback(async () => {
        setLoading(true)
        try {
            const token = localStorage.getItem('token')
            const params = new URLSearchParams({
                lines: lines.toString(),
                tail: 'true'
            })

            if (level !== 'all') {
                params.append('level', level.toUpperCase())
            }

            if (searchTerm) {
                params.append('search', searchTerm)
            }

            const response = await fetch(
                `http://localhost:8000/api/v1/logs/view/${selectedLog}?${params}`,
                { headers: { 'Authorization': `Bearer ${token}` } }
            )

            if (response.ok) {
                const data = await response.json()
                setLogs(data.logs)

                // Auto-scroll to bottom
                setTimeout(() => {
                    if (logContainerRef.current) {
                        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
                    }
                }, 100)
            } else {
                enqueueSnackbar('Failed to fetch logs', { variant: 'error' })
            }
        } catch (error) {
            enqueueSnackbar('Error fetching logs', { variant: 'error' })
        } finally {
            setLoading(false)
        }
    }, [selectedLog, level, searchTerm, lines, enqueueSnackbar])

    // Download logs
    const handleDownload = async () => {
        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`http://localhost:8000/api/v1/logs/download/${selectedLog}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })

            if (response.ok) {
                const blob = await response.blob()
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${selectedLog}_${new Date().toISOString()}.log`
                a.click()
                window.URL.revokeObjectURL(url)
                enqueueSnackbar('Log downloaded successfully', { variant: 'success' })
            }
        } catch (error) {
            enqueueSnackbar('Failed to download log', { variant: 'error' })
        }
    }

    // Clear logs
    const handleClear = async () => {
        if (!confirm('Are you sure you want to clear this log? A backup will be created.')) {
            return
        }

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`http://localhost:8000/api/v1/logs/clear/${selectedLog}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            })

            if (response.ok) {
                enqueueSnackbar('Log cleared successfully', { variant: 'success' })
                fetchLogs()
                fetchStats()
            }
        } catch (error) {
            enqueueSnackbar('Failed to clear log', { variant: 'error' })
        }
    }

    // Real-time WebSocket connection
    const connectWebSocket = useCallback(() => {
        const token = localStorage.getItem('token')
        const ws = new WebSocket(`ws://localhost:8000/api/v1/logs/ws/tail/${selectedLog}`)

        ws.onopen = () => {
            // Send auth
            ws.send(JSON.stringify({ type: 'auth', token: `Bearer ${token}` }))
            enqueueSnackbar('Real-time log streaming started', { variant: 'info' })
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            if (data.type === 'log_entry') {
                setLogs(prev => [...prev.slice(-lines + 1), data.entry])
                // Auto-scroll
                setTimeout(() => {
                    if (logContainerRef.current) {
                        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
                    }
                }, 50)
            } else if (data.error) {
                enqueueSnackbar(`WebSocket error: ${data.error}`, { variant: 'error' })
                setRealTime(false)
            }
        }

        ws.onerror = () => {
            enqueueSnackbar('WebSocket connection error', { variant: 'error' })
            setRealTime(false)
        }

        ws.onclose = () => {
            enqueueSnackbar('Real-time streaming stopped', { variant: 'info' })
        }

        wsRef.current = ws
    }, [selectedLog, lines, enqueueSnackbar])

    // Toggle real-time
    const toggleRealTime = () => {
        if (realTime) {
            // Stop real-time
            if (wsRef.current) {
                wsRef.current.close()
                wsRef.current = null
            }
            setRealTime(false)
        } else {
            // Start real-time
            connectWebSocket()
            setRealTime(true)
        }
    }

    // Auto-refresh
    useEffect(() => {
        if (autoRefresh && !realTime) {
            autoRefreshInterval.current = setInterval(() => {
                fetchLogs()
                fetchStats()
            }, 5000)
        } else if (autoRefreshInterval.current) {
            clearInterval(autoRefreshInterval.current)
            autoRefreshInterval.current = null
        }

        return () => {
            if (autoRefreshInterval.current) {
                clearInterval(autoRefreshInterval.current)
            }
        }
    }, [autoRefresh, realTime, fetchLogs, fetchStats])

    // Initial load
    useEffect(() => {
        fetchAvailableLogs()
    }, [fetchAvailableLogs])

    useEffect(() => {
        if (selectedLog) {
            fetchLogs()
            fetchStats()
        }
    }, [selectedLog, fetchLogs, fetchStats])

    // Cleanup WebSocket on unmount
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [])

    // Get log level color
    const getLevelColor = (logLevel: string) => {
        switch (logLevel.toUpperCase()) {
            case 'ERROR': return 'error'
            case 'WARNING': return 'warning'
            case 'INFO': return 'info'
            case 'DEBUG': return 'default'
            default: return 'default'
        }
    }

    // Get log level icon
    const getLevelIcon = (logLevel: string) => {
        switch (logLevel.toUpperCase()) {
            case 'ERROR': return <ErrorIcon fontSize="small" />
            case 'WARNING': return <WarningIcon fontSize="small" />
            case 'INFO': return <InfoIcon fontSize="small" />
            default: return null
        }
    }

    if (!isAdmin) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4 }}>
                <Alert severity="error">
                    Admin access required to view system logs
                </Alert>
            </Container>
        )
    }

    return (
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
            <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
                System Log Viewer
            </Typography>

            {/* Stats Cards */}
            {stats && (
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>Total Lines</Typography>
                                <Typography variant="h5">{stats.total_lines.toLocaleString()}</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>Errors</Typography>
                                <Typography variant="h5" color="error.main">{stats.error_count}</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>Warnings</Typography>
                                <Typography variant="h5" color="warning.main">{stats.warning_count}</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={12} md={3}>
                        <Card>
                            <CardContent>
                                <Typography color="text.secondary" gutterBottom>File Size</Typography>
                                <Typography variant="h5">{stats.file_size_mb} MB</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            )}

            {/* Controls */}
            <Paper sx={{ p: 2, mb: 2 }}>
                <Stack direction="row" spacing={2} flexWrap="wrap" alignItems="center">
                    <FormControl size="small" sx={{ minWidth: 200 }}>
                        <InputLabel>Log File</InputLabel>
                        <Select
                            value={selectedLog}
                            label="Log File"
                            onChange={(e) => setSelectedLog(e.target.value)}
                        >
                            {availableLogs.map(log => (
                                <MenuItem key={log} value={log}>{log}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Level</InputLabel>
                        <Select
                            value={level}
                            label="Level"
                            onChange={(e) => setLevel(e.target.value)}
                        >
                            <MenuItem value="all">All</MenuItem>
                            <MenuItem value="error">Error</MenuItem>
                            <MenuItem value="warning">Warning</MenuItem>
                            <MenuItem value="info">Info</MenuItem>
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 100 }}>
                        <InputLabel>Lines</InputLabel>
                        <Select
                            value={lines}
                            label="Lines"
                            onChange={(e) => setLines(Number(e.target.value))}
                        >
                            <MenuItem value={50}>50</MenuItem>
                            <MenuItem value={100}>100</MenuItem>
                            <MenuItem value={500}>500</MenuItem>
                            <MenuItem value={1000}>1000</MenuItem>
                        </Select>
                    </FormControl>

                    <TextField
                        size="small"
                        label="Search"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        InputProps={{
                            endAdornment: <SearchIcon />
                        }}
                        sx={{ minWidth: 200 }}
                    />

                    <Tooltip title="Refresh">
                        <IconButton onClick={fetchLogs} disabled={loading}>
                            <RefreshIcon />
                        </IconButton>
                    </Tooltip>

                    <Tooltip title="Download">
                        <IconButton onClick={handleDownload}>
                            <DownloadIcon />
                        </IconButton>
                    </Tooltip>

                    <Tooltip title="Clear Log">
                        <IconButton onClick={handleClear} color="error">
                            <DeleteIcon />
                        </IconButton>
                    </Tooltip>

                    <FormControlLabel
                        control={
                            <Switch
                                checked={autoRefresh}
                                onChange={(e) => setAutoRefresh(e.target.checked)}
                                disabled={realTime}
                            />
                        }
                        label="Auto-refresh"
                    />

                    <Button
                        variant={realTime ? "contained" : "outlined"}
                        color={realTime ? "error" : "primary"}
                        startIcon={realTime ? <StopIcon /> : <PlayIcon />}
                        onClick={toggleRealTime}
                    >
                        {realTime ? 'Stop' : 'Real-time'}
                    </Button>
                </Stack>
            </Paper>

            {/* Last Error Alert */}
            {stats?.last_error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2">Last Error ({stats.last_error_time}):</Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                        {stats.last_error}
                    </Typography>
                </Alert>
            )}

            {/* Log Display */}
            <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                <Box
                    ref={logContainerRef}
                    sx={{
                        height: '60vh',
                        overflow: 'auto',
                        fontFamily: 'monospace',
                        fontSize: '0.875rem',
                        bgcolor: 'background.paper',
                        p: 2,
                        borderRadius: 1
                    }}
                >
                    {loading && logs.length === 0 ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                            <CircularProgress />
                        </Box>
                    ) : logs.length === 0 ? (
                        <Typography color="text.secondary">No logs found</Typography>
                    ) : (
                        logs.map((log, index) => (
                            <Box
                                key={index}
                                onClick={() => {
                                    setSelectedLogEntry(log)
                                    setDetailsOpen(true)
                                }}
                                sx={{
                                    py: 0.75,
                                    px: 1.5,
                                    mb: 0.25,
                                    borderLeft: '3px solid',
                                    borderLeftColor: getLevelColor(log.level) === 'error' ? 'error.main' :
                                        getLevelColor(log.level) === 'warning' ? 'warning.main' : 'info.main',
                                    bgcolor: 'background.paper',
                                    '&:hover': {
                                        bgcolor: 'action.hover',
                                        cursor: 'pointer',
                                        borderLeftWidth: '4px'
                                    },
                                    display: 'flex',
                                    gap: 2,
                                    alignItems: 'flex-start',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <Typography
                                    component="span"
                                    sx={{
                                        color: 'text.secondary',
                                        minWidth: 180,
                                        fontWeight: 600,
                                        fontSize: '0.813rem',
                                        fontFamily: 'monospace',
                                        flexShrink: 0
                                    }}
                                >
                                    {log.timestamp || new Date().toISOString().replace('T', ' ').substring(0, 23)}
                                </Typography>
                                <Typography
                                    component="span"
                                    sx={{
                                        flex: 1,
                                        wordBreak: 'break-word',
                                        color: 'text.primary',
                                        fontSize: '0.875rem',
                                        whiteSpace: 'pre-wrap',
                                        fontFamily: 'monospace'
                                    }}
                                >
                                    {log.message}
                                </Typography>
                            </Box>
                        ))
                    )}
                </Box>
            </Paper>

            {/* Log Details Modal */}
            <Dialog
                open={detailsOpen}
                onClose={() => setDetailsOpen(false)}
                maxWidth="md"
                fullWidth
            >
                <DialogTitle>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        {selectedLogEntry && getLevelIcon(selectedLogEntry.level)}
                        <Typography variant="h6">Log Entry Details</Typography>
                        <Chip
                            label={selectedLogEntry?.level || 'INFO'}
                            size="small"
                            color={selectedLogEntry ? getLevelColor(selectedLogEntry.level) as any : 'default'}
                        />
                    </Box>
                </DialogTitle>
                <DialogContent dividers>
                    {selectedLogEntry && (
                        <Stack spacing={2}>
                            <Box>
                                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                    Timestamp
                                </Typography>
                                <Typography
                                    variant="body1"
                                    sx={{ fontFamily: 'monospace', fontWeight: 600 }}
                                >
                                    {selectedLogEntry.timestamp || 'No timestamp'}
                                </Typography>
                            </Box>

                            <Divider />

                            <Box>
                                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                    Logger / Source
                                </Typography>
                                <Typography
                                    variant="body1"
                                    sx={{ fontFamily: 'monospace' }}
                                >
                                    {selectedLogEntry.logger}
                                </Typography>
                            </Box>

                            <Divider />

                            <Box>
                                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                    Line Number
                                </Typography>
                                <Typography variant="body1">
                                    {selectedLogEntry.line_number}
                                </Typography>
                            </Box>

                            <Divider />

                            <Box>
                                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                    Message
                                </Typography>
                                <Paper
                                    variant="outlined"
                                    sx={{
                                        p: 2,
                                        bgcolor: 'background.default',
                                        maxHeight: '300px',
                                        overflow: 'auto'
                                    }}
                                >
                                    <Typography
                                        variant="body2"
                                        component="pre"
                                        sx={{
                                            fontFamily: 'monospace',
                                            whiteSpace: 'pre-wrap',
                                            wordBreak: 'break-word',
                                            m: 0
                                        }}
                                    >
                                        {selectedLogEntry.message}
                                    </Typography>
                                </Paper>
                            </Box>

                            {selectedLogEntry.exception && (
                                <>
                                    <Divider />
                                    <Box>
                                        <Typography variant="subtitle2" color="error" gutterBottom>
                                            Exception / Stack Trace
                                        </Typography>
                                        <Paper
                                            variant="outlined"
                                            sx={{
                                                p: 2,
                                                bgcolor: 'error.dark',
                                                color: 'error.contrastText',
                                                maxHeight: '300px',
                                                overflow: 'auto'
                                            }}
                                        >
                                            <Typography
                                                variant="body2"
                                                component="pre"
                                                sx={{
                                                    fontFamily: 'monospace',
                                                    whiteSpace: 'pre-wrap',
                                                    wordBreak: 'break-word',
                                                    m: 0
                                                }}
                                            >
                                                {selectedLogEntry.exception}
                                            </Typography>
                                        </Paper>
                                    </Box>
                                </>
                            )}
                        </Stack>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDetailsOpen(false)}>Close</Button>
                </DialogActions>
            </Dialog>
        </Container>
    )
}

export default LogViewerPage

