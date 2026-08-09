import React, { useState, useEffect, useMemo } from 'react';
import { http } from '../services/http';
import {
    Box,
    Grid,
    Paper,
    Typography,
    Chip,
    Stack,
    TextField,
    InputAdornment,
    Button,
    Avatar,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    MenuItem,
    Select,
    FormControl,
    InputLabel,
    Table,
    TableHead,
    TableBody,
    TableRow,
    TableCell,
    Skeleton,
    Tooltip
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import AssignmentIndIcon from '@mui/icons-material/AssignmentInd';
import StorageIcon from '@mui/icons-material/Storage';
import DescriptionIcon from '@mui/icons-material/Description';

interface OwnershipStats {
    user_id: number;
    user_email: string;
    user_name: string;
    user_role: string;
    department: string | null;
    total_documents: number;
    by_file_type: Record<string, number>;
    by_classification: Record<string, number>;
    total_size_mb: number;
}

interface User {
    id: number;
    email: string;
    full_name: string;
    role: string;
}

const roleColor: Record<string, string> = {
    admin: '#ef4444',
    manager: '#3b82f6',
    analyst: '#22c55e'
};

const DocumentOwnership: React.FC = () => {
    const [ownershipStats, setOwnershipStats] = useState<OwnershipStats[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<OwnershipStats | null>(null);
    const [targetUserId, setTargetUserId] = useState<number | ''>('');
    const [reason, setReason] = useState('');

    useEffect(() => {
        void bootstrap();
    }, []);

    const bootstrap = async () => {
        setLoading(true);
        try {
            const [statsRes, usersRes] = await Promise.all([
                http.get('/ownership/stats'),
                http.get('/users/')
            ]);
            setOwnershipStats(statsRes.data || []);
            setUsers(Array.isArray(usersRes.data) ? usersRes.data : (usersRes.data.users || []));
        } finally {
            setLoading(false);
        }
    };

    const totals = useMemo(() => {
        const usersCount = ownershipStats.length;
        const docs = ownershipStats.reduce((s, r) => s + r.total_documents, 0);
        const storage = ownershipStats.reduce((s, r) => s + r.total_size_mb, 0);
        return { usersCount, docs, storage: Number(storage.toFixed(2)) };
    }, [ownershipStats]);

    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        if (!q) return ownershipStats;
        return ownershipStats.filter((r) =>
            r.user_name.toLowerCase().includes(q) ||
            r.user_email.toLowerCase().includes(q) ||
            (r.department?.toLowerCase().includes(q) ?? false)
        );
    }, [ownershipStats, search]);

    const onReassign = (row: OwnershipStats) => {
        setSelectedUser(row);
        setTargetUserId('');
        setReason('');
        setDialogOpen(true);
    };

    const confirmReassign = async () => {
        if (!selectedUser || !targetUserId) return;
        await http.post('/ownership/bulk-reassign', {
            from_user_id: selectedUser.user_id,
            to_user_id: targetUserId,
            reason: reason || 'Bulk ownership reassignment'
        });
        setDialogOpen(false);
        await bootstrap();
    };

    return (
        <Box>
            {/* Hero */}
            <Paper
                sx={{
                    p: 2,
                    mb: 2,
                    borderRadius: 3,
                    background: (t) =>
                        t.palette.mode === 'light'
                            ? 'linear-gradient(135deg, #ECFEFF 0%, #EEF2FF 100%)'
                            : 'linear-gradient(135deg, #0B1020 0%, #0F172A 100%)'
                }}
                elevation={0}
            >
                <Stack direction="row" alignItems="center" spacing={1}>
                    <Chip label="Documents Hub" color="primary" variant="outlined" />
                    <Typography variant="h5" fontWeight={700}>Document Ownership Management</Typography>
                </Stack>
            </Paper>

            {/* Controls + Stats */}
            <Grid container spacing={2} alignItems="stretch">
                <Grid item xs={12} md={4}>
                    <TextField
                        fullWidth
                        placeholder="Search by name, email, or department"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start"><SearchIcon /></InputAdornment>
                            )
                        }}
                    />
                </Grid>
                <Grid item xs={12} md={8}>
                    <Grid container spacing={2}>
                        <Grid item xs={12} sm={4}>
                            <Paper sx={{ p: 2, borderRadius: 3 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                    <Avatar sx={{ bgcolor: 'primary.main' }}><AssignmentIndIcon /></Avatar>
                                    <Box>
                                        <Typography variant="overline" color="text.secondary">Users</Typography>
                                        <Typography variant="h6" fontWeight={700}>{loading ? <Skeleton width={40} /> : totals.usersCount}</Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper sx={{ p: 2, borderRadius: 3 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                    <Avatar sx={{ bgcolor: 'success.main' }}><DescriptionIcon /></Avatar>
                                    <Box>
                                        <Typography variant="overline" color="text.secondary">Documents</Typography>
                                        <Typography variant="h6" fontWeight={700}>{loading ? <Skeleton width={60} /> : totals.docs}</Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper sx={{ p: 2, borderRadius: 3 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                    <Avatar sx={{ bgcolor: 'info.main' }}><StorageIcon /></Avatar>
                                    <Box>
                                        <Typography variant="overline" color="text.secondary">Storage (MB)</Typography>
                                        <Typography variant="h6" fontWeight={700}>{loading ? <Skeleton width={80} /> : totals.storage}</Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2, mb: 1 }}>
                <Button startIcon={<RefreshIcon />} onClick={() => void bootstrap()} variant="outlined">Refresh</Button>
            </Box>

            {/* Table */}
            <Paper sx={{ borderRadius: 3, overflow: 'hidden' }}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>User</TableCell>
                            <TableCell>Role</TableCell>
                            <TableCell>Department</TableCell>
                            <TableCell align="right">Documents</TableCell>
                            <TableCell align="right">Storage (MB)</TableCell>
                            <TableCell>File Types</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {(loading ? Array.from({ length: 6 }) : filtered).map((row, idx) => (
                            <TableRow key={loading ? idx : row.user_id} hover>
                                <TableCell>
                                    {loading ? (
                                        <Skeleton width={220} />
                                    ) : (
                                        <Stack>
                                            <Typography fontWeight={600}>{row.user_name}</Typography>
                                            <Typography variant="caption" color="text.secondary">{row.user_email}</Typography>
                                        </Stack>
                                    )}
                                </TableCell>
                                <TableCell>
                                    {loading ? <Skeleton width={80} /> : (
                                        <Chip
                                            label={row.user_role}
                                            size="small"
                                            sx={{ bgcolor: `${roleColor[row.user_role?.toLowerCase?.()] || '#e5e7eb'}33` }}
                                            color={row.user_role?.toLowerCase?.() === 'admin' ? 'error' : row.user_role?.toLowerCase?.() === 'manager' ? 'info' : 'success'}
                                        />
                                    )}
                                </TableCell>
                                <TableCell>{loading ? <Skeleton width={120} /> : (row as any)?.department || '-'}</TableCell>
                                <TableCell align="right">{loading ? <Skeleton width={40} /> : (row as any)?.total_documents}</TableCell>
                                <TableCell align="right">{loading ? <Skeleton width={60} /> : (row as any)?.total_size_mb.toFixed(2)}</TableCell>
                                <TableCell>
                                    {loading ? (
                                        <Skeleton width={200} />
                                    ) : (
                                        <Stack direction="row" spacing={0.5} flexWrap="wrap">
                                            {Object.entries((row as any).by_file_type || {}).slice(0, 4).map(([t, c]) => (
                                                <Tooltip key={t} title={`${t.toUpperCase()}: ${c}`}>
                                                    <Chip size="small" variant="outlined" label={`${t.toUpperCase()} ${c}`} />
                                                </Tooltip>
                                            ))}
                                        </Stack>
                                    )}
                                </TableCell>
                                <TableCell align="right">
                                    {loading ? (
                                        <Skeleton width={90} />
                                    ) : (
                                        <Button
                                            size="small"
                                            variant="outlined"
                                            disabled={(row as any).total_documents === 0}
                                            onClick={() => onReassign(row as OwnershipStats)}
                                        >
                                            Reassign
                                        </Button>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Paper>

            {/* Reassign dialog */}
            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Reassign Documents</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} mt={1}>
                        <Typography variant="body2" color="text.secondary">
                            From: <strong>{selectedUser?.user_name}</strong> ({selectedUser?.total_documents} documents)
                        </Typography>
                        <FormControl fullWidth>
                            <InputLabel>New Owner</InputLabel>
                            <Select
                                label="New Owner"
                                value={targetUserId}
                                onChange={(e) => setTargetUserId(e.target.value as number | '')}
                            >
                                {users.filter(u => u.id !== selectedUser?.user_id).map(u => (
                                    <MenuItem key={u.id} value={u.id}>{u.full_name || u.email} — {u.role}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <TextField
                            label="Reason (optional)"
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            fullWidth
                        />
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button onClick={() => void confirmReassign()} variant="contained" disabled={!targetUserId}>Confirm</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default DocumentOwnership;

