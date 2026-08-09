import React, { useEffect, useState } from 'react'
import {
    Box,
    Paper,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    IconButton,
    Tooltip,
    Stack,
    Alert,
    CircularProgress,
} from '@mui/material'
import {
    Visibility as ViewIcon,
    BarChart as StatsIcon,
} from '@mui/icons-material'
import { useAppSelector } from '../hooks/redux'
import { http } from '../services/http'

interface Analyst {
    id: number
    email: string
    username: string
    full_name: string
    role: string
    is_active: boolean
    created_at: string
}

const TeamPage: React.FC = () => {
    const { user } = useAppSelector((state) => state.auth)
    const [analysts, setAnalysts] = useState<Analyst[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        fetchTeamAnalysts()
    }, [])

    const fetchTeamAnalysts = async () => {
        try {
            setLoading(true)
            const response = await http.get('/users/team/analysts')
            setAnalysts(response.data)
            setError(null)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load team analysts')
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
            </Box>
        )
    }

    return (
        <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
                <Box>
                    <Typography variant="h4" gutterBottom fontWeight={600}>
                        My Team
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Manage and monitor your team's analysts
                    </Typography>
                </Box>
                <Chip
                    label={`${analysts.length} Analyst${analysts.length !== 1 ? 's' : ''}`}
                    color="primary"
                    variant="outlined"
                />
            </Stack>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            <Paper sx={{ width: '100%', overflow: 'hidden' }}>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Name</TableCell>
                                <TableCell>Email</TableCell>
                                <TableCell>Username</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Joined</TableCell>
                                <TableCell align="right">Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {analysts.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} align="center">
                                        <Typography variant="body2" color="text.secondary" py={4}>
                                            No analysts assigned to your team yet
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                analysts.map((analyst) => (
                                    <TableRow key={analyst.id} hover>
                                        <TableCell>
                                            <Typography variant="body2" fontWeight={500}>
                                                {analyst.full_name || analyst.username}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" color="text.secondary">
                                                {analyst.email}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" color="text.secondary">
                                                {analyst.username}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={analyst.is_active ? 'Active' : 'Inactive'}
                                                color={analyst.is_active ? 'success' : 'default'}
                                                size="small"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2" color="text.secondary">
                                                {new Date(analyst.created_at).toLocaleDateString()}
                                            </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                            <Stack direction="row" spacing={1} justifyContent="flex-end">
                                                <Tooltip title="View Documents">
                                                    <IconButton size="small" color="primary">
                                                        <ViewIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="View Activity">
                                                    <IconButton size="small" color="primary">
                                                        <StatsIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>

            {/* Team Statistics Summary */}
            <Box mt={3}>
                <Typography variant="h6" gutterBottom>
                    Team Summary
                </Typography>
                <Stack direction="row" spacing={2}>
                    <Paper sx={{ p: 2, flex: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Total Analysts
                        </Typography>
                        <Typography variant="h4" fontWeight={600}>
                            {analysts.length}
                        </Typography>
                    </Paper>
                    <Paper sx={{ p: 2, flex: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Active
                        </Typography>
                        <Typography variant="h4" fontWeight={600} color="success.main">
                            {analysts.filter(a => a.is_active).length}
                        </Typography>
                    </Paper>
                    <Paper sx={{ p: 2, flex: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Inactive
                        </Typography>
                        <Typography variant="h4" fontWeight={600} color="text.secondary">
                            {analysts.filter(a => !a.is_active).length}
                        </Typography>
                    </Paper>
                </Stack>
            </Box>
        </Box>
    )
}

export default TeamPage




