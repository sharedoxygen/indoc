import React, { useEffect, useState } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Button,
    TextField,
    InputAdornment,
    Avatar,
    Chip,
    Grid,
    Stack,
    Alert,
    CircularProgress,
    IconButton,
    Tooltip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    alpha,
    Badge
} from '@mui/material';
import {
    Search as SearchIcon,
    Add as AddIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    Refresh as RefreshIcon,
    AdminPanelSettings as AdminIcon,
    SupervisorAccount as ManagerIcon,
    WorkOutline as AnalystIcon,
    CheckCircle as ActiveIcon,
    Cancel as InactiveIcon,
    LockReset as ResetPasswordIcon,
    Person as PersonIcon,
    Cancel as CancelIcon
} from '@mui/icons-material';
import { http } from '../services/http';
import { useSnackbar } from 'notistack';

interface User {
    id: number;
    email: string;
    username: string;
    full_name: string | null;
    role: string;
    is_active: boolean;
    is_verified: boolean;
    created_at: string;
    department?: string;
    phone?: string;
    location?: string;
}

interface UserFormData {
    email: string;
    username: string;
    full_name: string;
    role: string;
    is_active: boolean;
    password?: string;
    department?: string;
    phone?: string;
    location?: string;
    manager_id?: number;
}

const getRoleIcon = (role: string) => {
    switch (role.toLowerCase()) {
        case 'admin': return <AdminIcon />;
        case 'manager': return <ManagerIcon />;
        default: return <AnalystIcon />;
    }
};

const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
        case 'admin': return '#f44336';
        case 'manager': return '#2196f3';
        default: return '#4caf50';
    }
};

const UsersPage: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [managers, setManagers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create');
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [formData, setFormData] = useState<UserFormData>({
        email: '',
        username: '',
        full_name: '',
        role: 'Analyst',
        is_active: true,
        password: '',
    });

    const { enqueueSnackbar } = useSnackbar();

    useEffect(() => {
        fetchUsers();
        fetchManagers();
    }, []);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            setError(null);
            console.log('🔄 Fetching users...');
            const response = await http.get('/users/');
            console.log('✅ Users response:', response.status, 'Data type:', Array.isArray(response.data) ? 'array' : typeof response.data, 'Count:', response.data?.length);
            setUsers(Array.isArray(response.data) ? response.data : []);
        } catch (err: any) {
            console.error('❌ fetchUsers error:', err);
            console.error('Status:', err.response?.status);
            console.error('Data:', err.response?.data);
            // If non-admin, backend returns 403. Show friendly message instead of error banner.
            const status = err.response?.status;
            if (status === 403) {
                setUsers([]);
                setError(null);
            } else {
                const errorDetail = err.response?.data?.detail || err.message || 'Failed to load users';
                setError(errorDetail);
                console.error('Setting error state:', errorDetail);
            }
        } finally {
            setLoading(false);
        }
    };

    const fetchManagers = async () => {
        try {
            const response = await http.get('/users/?role=Manager');
            setManagers(Array.isArray(response.data) ? response.data : []);
        } catch (err: any) {
            console.error('❌ Failed to load managers:', err);
            // Don't show error for managers loading failure as it's not critical
        }
    };

    const handleCreateUser = () => {
        setDialogMode('create');
        setFormData({
            email: '',
            username: '',
            full_name: '',
            role: 'Analyst',
            is_active: true,
            password: '',
            manager_id: undefined,
        });
        setSelectedUser(null);
        setDialogOpen(true);
    };

    const handleEditUser = (user: User) => {
        setDialogMode('edit');
        setSelectedUser(user);
        setFormData({
            email: user.email,
            username: user.username,
            full_name: user.full_name || '',
            role: user.role,
            is_active: user.is_active,
            department: user.department,
            phone: user.phone,
            location: user.location,
            manager_id: (user as any).manager_id,
        });
        setDialogOpen(true);
    };

    const handleDeleteClick = (user: User) => {
        setSelectedUser(user);
        setDeleteDialogOpen(true);
    };

    const handleSubmit = async () => {
        try {
            setSubmitting(true);

            // Validation: Analysts must have a manager assigned
            if (formData.role === 'Analyst' && !formData.manager_id) {
                enqueueSnackbar('Analysts must be assigned to a manager', { variant: 'error' });
                return;
            }

            if (dialogMode === 'create') {
                await http.post('/users/', formData);
                enqueueSnackbar('User created successfully', { variant: 'success' });
            } else if (selectedUser) {
                await http.put(`/users/${selectedUser.id}`, formData);
                enqueueSnackbar('User updated successfully', { variant: 'success' });
            }
            setDialogOpen(false);
            fetchUsers();
            fetchManagers(); // Refresh managers list in case new manager was created
        } catch (err: any) {
            enqueueSnackbar(
                err.response?.data?.detail || `Failed to ${dialogMode} user`,
                { variant: 'error' }
            );
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async () => {
        if (!selectedUser) return;
        try {
            setSubmitting(true);
            await http.delete(`/users/${selectedUser.id}`);
            enqueueSnackbar('User deleted successfully', { variant: 'success' });
            setDeleteDialogOpen(false);
            fetchUsers();
        } catch (err: any) {
            enqueueSnackbar(
                err.response?.data?.detail || 'Failed to delete user',
                { variant: 'error' }
            );
        } finally {
            setSubmitting(false);
        }
    };

    const handleToggleStatus = async (user: User) => {
        try {
            await http.patch(`/users/${user.id}/status`, {
                is_active: !user.is_active,
            });
            enqueueSnackbar(
                `User ${user.is_active ? 'deactivated' : 'activated'} successfully`,
                { variant: 'success' }
            );
            fetchUsers();
        } catch (err: any) {
            enqueueSnackbar(
                err.response?.data?.detail || 'Failed to update user status',
                { variant: 'error' }
            );
        }
    };

    const filteredUsers = users.filter(user =>
        user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.department?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return (
            <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="60vh">
                <CircularProgress size={60} />
                <Typography variant="h6" sx={{ mt: 2 }}>Loading users...</Typography>
            </Box>
        );
    }

    const usersByRole = filteredUsers.reduce((acc, user) => {
        if (!acc[user.role]) acc[user.role] = [];
        acc[user.role].push(user);
        return acc;
    }, {} as Record<string, User[]>);

    return (
        <Box sx={{ p: 3, bgcolor: 'background.default', minHeight: '100vh' }}>
            {/* Header */}
            <Box sx={{ mb: 4 }}>
                <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                    <Stack direction="row" spacing={2} alignItems="center">
                        <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
                            <PersonIcon fontSize="large" />
                        </Avatar>
                        <Box>
                            <Typography variant="h4" fontWeight="bold">
                                User Management
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                {users.length} users across the organization
                            </Typography>
                        </Box>
                    </Stack>
                    <Stack direction="row" spacing={2}>
                        <Button
                            variant="outlined"
                            startIcon={<RefreshIcon />}
                            onClick={fetchUsers}
                            disabled={loading}
                        >
                            Refresh
                        </Button>
                        <Button
                            variant="contained"
                            startIcon={<AddIcon />}
                            onClick={handleCreateUser}
                        >
                            Add User
                        </Button>
                    </Stack>
                </Stack>
            </Box>

            {/* Error Alert */}
            {error && (
                <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            {/* Search */}
            <TextField
                fullWidth
                placeholder="Search users by name, email, username, or department..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchIcon />
                        </InputAdornment>
                    ),
                }}
                sx={{ mb: 3 }}
            />

            {/* Stats Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                {['Admin', 'Manager', 'Analyst'].map((role) => (
                    <Grid item xs={12} sm={4} key={role}>
                        <Card
                            sx={{
                                bgcolor: alpha(getRoleColor(role), 0.1),
                                border: `2px solid ${alpha(getRoleColor(role), 0.3)}`,
                                transition: 'all 0.3s',
                                '&:hover': {
                                    transform: 'translateY(-4px)',
                                    boxShadow: 4
                                }
                            }}
                        >
                            <CardContent>
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: getRoleColor(role), width: 48, height: 48 }}>
                                        {getRoleIcon(role)}
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h3" fontWeight="bold" color={getRoleColor(role)}>
                                            {usersByRole[role]?.length || 0}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {role}{usersByRole[role]?.length !== 1 ? 's' : ''}
                                        </Typography>
                                    </Box>
                                </Stack>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* User Cards Grid */}
            <Grid container spacing={2}>
                {filteredUsers.map((user) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={user.id}>
                        <Card
                            sx={{
                                height: '100%',
                                transition: 'all 0.3s',
                                border: `2px solid ${alpha(getRoleColor(user.role), 0.3)}`,
                                '&:hover': {
                                    transform: 'translateY(-4px)',
                                    boxShadow: `0 8px 24px ${alpha(getRoleColor(user.role), 0.3)}`
                                }
                            }}
                        >
                            <CardContent>
                                <Stack spacing={2}>
                                    {/* User Avatar & Status */}
                                    <Stack direction="row" spacing={2} alignItems="center">
                                        <Badge
                                            overlap="circular"
                                            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                                            badgeContent={
                                                user.is_active ? (
                                                    <ActiveIcon sx={{ color: '#4caf50', fontSize: 16 }} />
                                                ) : (
                                                    <InactiveIcon sx={{ color: '#f44336', fontSize: 16 }} />
                                                )
                                            }
                                        >
                                            <Avatar
                                                sx={{
                                                    bgcolor: getRoleColor(user.role),
                                                    width: 56,
                                                    height: 56
                                                }}
                                            >
                                                {getRoleIcon(user.role)}
                                            </Avatar>
                                        </Badge>
                                        <Box sx={{ flex: 1, minWidth: 0 }}>
                                            <Typography variant="subtitle1" fontWeight="bold" noWrap>
                                                {user.full_name || user.username}
                                            </Typography>
                                            <Chip
                                                label={user.role}
                                                size="small"
                                                sx={{
                                                    bgcolor: getRoleColor(user.role),
                                                    color: 'white',
                                                    fontWeight: 'bold'
                                                }}
                                            />
                                        </Box>
                                    </Stack>

                                    {/* User Details */}
                                    <Stack spacing={0.5}>
                                        <Typography variant="caption" color="text.secondary" noWrap>
                                            📧 {user.email}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary" noWrap>
                                            👤 {user.username}
                                        </Typography>
                                        {user.department && (
                                            <Typography variant="caption" color="text.secondary" noWrap>
                                                🏢 {user.department}
                                            </Typography>
                                        )}
                                    </Stack>

                                    {/* Actions */}
                                    <Stack direction="row" spacing={1}>
                                        <Tooltip title="Edit User">
                                            <IconButton
                                                size="small"
                                                onClick={() => handleEditUser(user)}
                                                sx={{
                                                    bgcolor: alpha('#2196f3', 0.1),
                                                    '&:hover': { bgcolor: alpha('#2196f3', 0.2) }
                                                }}
                                            >
                                                <EditIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title={user.is_active ? 'Deactivate' : 'Activate'}>
                                            <IconButton
                                                size="small"
                                                onClick={() => handleToggleStatus(user)}
                                                sx={{
                                                    bgcolor: alpha(user.is_active ? '#f44336' : '#4caf50', 0.1),
                                                    '&:hover': { bgcolor: alpha(user.is_active ? '#f44336' : '#4caf50', 0.2) }
                                                }}
                                            >
                                                {user.is_active ? <InactiveIcon fontSize="small" /> : <ActiveIcon fontSize="small" />}
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title="Delete User">
                                            <IconButton
                                                size="small"
                                                onClick={() => handleDeleteClick(user)}
                                                sx={{
                                                    bgcolor: alpha('#f44336', 0.1),
                                                    '&:hover': { bgcolor: alpha('#f44336', 0.2) }
                                                }}
                                            >
                                                <DeleteIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </Stack>
                                </Stack>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {filteredUsers.length === 0 && !loading && (
                <Box textAlign="center" py={8}>
                    <PersonIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                        No users found
                    </Typography>
                </Box>
            )}

            {/* Create/Edit User Dialog */}
            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {dialogMode === 'create' ? 'Create New User' : 'Edit User'}
                </DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1 }}>
                        <TextField
                            label="Email"
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            fullWidth
                            required
                        />
                        <TextField
                            label="Username"
                            value={formData.username}
                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                            fullWidth
                            required
                        />
                        <TextField
                            label="Full Name"
                            value={formData.full_name}
                            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            fullWidth
                            required
                        />
                        <FormControl fullWidth>
                            <InputLabel>Role</InputLabel>
                            <Select
                                value={formData.role}
                                label="Role"
                                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                            >
                                <MenuItem value="Admin">Admin</MenuItem>
                                <MenuItem value="Manager">Manager</MenuItem>
                                <MenuItem value="Analyst">Analyst</MenuItem>
                            </Select>
                        </FormControl>

                        {/* Manager Assignment - Only show for Analysts */}
                        {formData.role === 'Analyst' && (
                            <FormControl fullWidth>
                                <InputLabel>Manager (Required for Analysts)</InputLabel>
                                <Select
                                    value={formData.manager_id || ''}
                                    label="Manager (Required for Analysts)"
                                    onChange={(e) => setFormData({ ...formData, manager_id: Number(e.target.value) || undefined })}
                                    required
                                >
                                    <MenuItem value="">
                                        <em>-- Select Manager --</em>
                                    </MenuItem>
                                    {managers.map(manager => (
                                        <MenuItem key={manager.id} value={manager.id}>
                                            <Stack direction="row" spacing={1} alignItems="center">
                                                <Avatar sx={{ bgcolor: getRoleColor('manager'), width: 24, height: 24 }}>
                                                    <ManagerIcon sx={{ fontSize: 16 }} />
                                                </Avatar>
                                                <Typography>
                                                    {manager.full_name || manager.username} ({manager.email})
                                                </Typography>
                                            </Stack>
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}

                        {dialogMode === 'create' && (
                            <TextField
                                label="Password"
                                type="password"
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                fullWidth
                                required
                                helperText="Minimum 8 characters"
                            />
                        )}
                        <TextField
                            label="Department (Optional)"
                            value={formData.department || ''}
                            onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                            fullWidth
                        />
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button
                        onClick={() => {
                            setDialogOpen(false);
                            setFormData({
                                email: '',
                                username: '',
                                full_name: '',
                                role: 'Analyst',
                                is_active: true,
                                password: '',
                                manager_id: undefined,
                            });
                        }}
                        startIcon={<CancelIcon />}
                        sx={{ color: 'text.secondary' }}
                    >
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} variant="contained" disabled={submitting}>
                        {submitting ? <CircularProgress size={20} /> : dialogMode === 'create' ? 'Create' : 'Update'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
                <DialogTitle>Confirm Delete</DialogTitle>
                <DialogContent>
                    <Typography>
                        Are you sure you want to delete user <strong>{selectedUser?.email}</strong>?
                        This action cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleDelete} variant="contained" color="error" disabled={submitting}>
                        {submitting ? <CircularProgress size={20} /> : 'Delete'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default UsersPage;
