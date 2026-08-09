import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Tab,
    Tabs,
    Paper,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Chip,
    Alert,
    CircularProgress,
    Grid,
    Avatar,
    Tooltip,
    Divider,
    Stack,
    alpha
} from '@mui/material';
import {
    Security as SecurityIcon,
    Person as PersonIcon,
    VpnKey as PermissionIcon,
    CheckCircle as CheckIcon,
    DragIndicator as DragIcon,
    AdminPanelSettings as AdminIcon,
    SupervisorAccount as ManagerIcon,
    WorkOutline as AnalystIcon,
    Close as CloseIcon,
    AccountBox as UserIcon,
    Edit as EditIcon
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { http } from '../services/http';
import '../styles/RoleManagement.css';

interface Role {
    id: number;
    name: string;
    description: string | null;
    is_system: boolean;
    is_active: boolean;
}

interface Permission {
    id: number;
    name: string;
    resource: string;
    action: string;
    description: string | null;
}

interface User {
    id: number;
    username: string;
    email: string;
    full_name: string;
}

const getRoleIcon = (roleName: string) => {
    switch (roleName.toLowerCase()) {
        case 'admin': return <AdminIcon />;
        case 'manager': return <ManagerIcon />;
        case 'analyst': return <AnalystIcon />;
        default: return <SecurityIcon />;
    }
};

const getRoleColor = (roleName: string) => {
    switch (roleName.toLowerCase()) {
        case 'admin': return '#f44336';
        case 'manager': return '#2196f3';
        case 'analyst': return '#4caf50';
        default: return '#9e9e9e';
    }
};

const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
        case 'create': return '#4caf50';
        case 'read': return '#2196f3';
        case 'update': return '#ff9800';
        case 'delete': return '#f44336';
        case 'list': return '#9c27b0';
        case 'admin': return '#607d8b';
        default: return '#757575';
    }
};

const RoleManagement: React.FC = () => {
    const [tabValue, setTabValue] = useState(0);
    const [roles, setRoles] = useState<Role[]>([]);
    const [permissions, setPermissions] = useState<Permission[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Dialog states
    const [selectedRole, setSelectedRole] = useState<Role | null>(null);
    const [rolePermissions, setRolePermissions] = useState<Permission[]>([]);
    const [availablePermissions, setAvailablePermissions] = useState<Permission[]>([]);
    const [openPermissionDialog, setOpenPermissionDialog] = useState(false);

    // User-Role assignment
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [userRoles, setUserRoles] = useState<Role[]>([]);
    const [openUserDialog, setOpenUserDialog] = useState(false);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch roles and permissions (RBAC endpoints)
            const [rolesRes, permsRes] = await Promise.all([
                http.get('/rbac/roles'),
                http.get('/rbac/permissions')
            ]);
            setRoles(rolesRes.data || []);
            setPermissions(permsRes.data || []);

            // Fetch users - handle 403 gracefully for non-admins
            try {
                const usersRes = await http.get('/users/');
                setUsers(usersRes.data || []);
            } catch (usersErr: any) {
                // If 403, silently ignore (non-admin users can't see users list)
                if (usersErr.response?.status === 403) {
                    setUsers([]);
                } else {
                    throw usersErr;
                }
            }
        } catch (err: any) {
            const status = err.response?.status;
            const message = err.response?.data?.detail;

            // Provide more specific error messages
            if (status === 403) {
                setError('Access denied. You need administrator privileges to manage roles and permissions.');
            } else if (status === 404) {
                setError('RBAC system not found. Please contact your administrator.');
            } else if (status === 500) {
                setError('Server error. Please try again later or contact support.');
            } else {
                setError(message || 'Failed to load RBAC data. Please refresh the page.');
            }
        } finally {
            setLoading(false);
        }
    };

    // Debug: Log permissions when they change
    React.useEffect(() => {
        console.log('Permissions loaded:', permissions);
        console.log('Permissions grouped:', permissions.reduce((acc, perm) => {
            if (!acc[perm.resource]) acc[perm.resource] = [];
            acc[perm.resource].push(perm);
            return acc;
        }, {} as Record<string, Permission[]>));
    }, [permissions]);

    const handleOpenRolePermissions = async (role: Role) => {
        try {
            setSelectedRole(role);
            const [rolePermsRes, availPermsRes] = await Promise.all([
                http.get(`/rbac/roles/${role.id}/permissions`),
                http.get('/rbac/permissions')
            ]);
            setRolePermissions(rolePermsRes.data);
            setAvailablePermissions(availPermsRes.data);
            setOpenPermissionDialog(true);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load permissions');
        }
    };

    const handleDragEnd = async (result: any) => {
        if (!result.destination || !selectedRole) return;

        const { source, destination, draggableId } = result;

        // Moving from available to assigned
        if (source.droppableId === 'available' && destination.droppableId === 'assigned') {
            const permId = parseInt(draggableId.replace('perm-', ''));
            await handleAssignPermission(permId);
        }

        // Moving from assigned to available
        if (source.droppableId === 'assigned' && destination.droppableId === 'available') {
            const permId = parseInt(draggableId.replace('perm-', ''));
            await handleRemovePermission(permId);
        }
    };

    const handleAssignPermission = async (permissionId: number) => {
        if (!selectedRole) return;
        try {
            await http.post(`/rbac/roles/${selectedRole.id}/permissions/${permissionId}`);
            setSuccess('Permission assigned successfully');
            // Reload permissions
            const rolePermsRes = await http.get(`/rbac/roles/${selectedRole.id}/permissions`);
            setRolePermissions(rolePermsRes.data || []);
        } catch (err: any) {
            const status = err.response?.status;
            const message = err.response?.data?.detail;

            if (status === 403) {
                setError('Access denied. You cannot modify system role permissions.');
            } else if (status === 404) {
                setError('Role or permission not found.');
            } else if (status === 409) {
                setError('Permission is already assigned to this role.');
            } else {
                setError(message || 'Failed to assign permission');
            }
        }
    };

    const handleRemovePermission = async (permissionId: number) => {
        if (!selectedRole) return;
        try {
            await http.delete(`/rbac/roles/${selectedRole.id}/permissions/${permissionId}`);
            setSuccess('Permission removed successfully');
            // Reload permissions
            const rolePermsRes = await http.get(`/rbac/roles/${selectedRole.id}/permissions`);
            setRolePermissions(rolePermsRes.data || []);
        } catch (err: any) {
            const status = err.response?.status;
            const message = err.response?.data?.detail;

            if (status === 403) {
                setError('Access denied. You cannot modify system role permissions.');
            } else if (status === 404) {
                setError('Role or permission not found.');
            } else {
                setError(message || 'Failed to remove permission');
            }
        }
    };

    const handleOpenUserRoles = async (user: User) => {
        try {
            setSelectedUser(user);
            const rolesRes = await http.get(`/rbac/users/${user.id}/roles`);
            setUserRoles(rolesRes.data);
            setOpenUserDialog(true);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load user roles');
        }
    };

    const handleAssignRoleToUser = async (roleId: number) => {
        if (!selectedUser) return;
        try {
            await http.post(`/rbac/users/${selectedUser.id}/roles/${roleId}`);
            setSuccess('Role assigned successfully');
            // Reload user roles
            const rolesRes = await http.get(`/rbac/users/${selectedUser.id}/roles`);
            setUserRoles(rolesRes.data || []);
        } catch (err: any) {
            const status = err.response?.status;
            const message = err.response?.data?.detail;

            if (status === 403) {
                setError('Access denied. You cannot assign system roles.');
            } else if (status === 404) {
                setError('User or role not found.');
            } else if (status === 409) {
                setError('User already has this role assigned.');
            } else {
                setError(message || 'Failed to assign role');
            }
        }
    };

    const handleRemoveRoleFromUser = async (roleId: number) => {
        if (!selectedUser) return;
        try {
            await http.delete(`/rbac/users/${selectedUser.id}/roles/${roleId}`);
            setSuccess('Role removed successfully');
            // Reload user roles
            const rolesRes = await http.get(`/rbac/users/${selectedUser.id}/roles`);
            setUserRoles(rolesRes.data || []);
        } catch (err: any) {
            const status = err.response?.status;
            const message = err.response?.data?.detail;

            if (status === 403) {
                setError('Access denied. You cannot remove system roles from users.');
            } else if (status === 404) {
                setError('User or role not found.');
            } else {
                setError(message || 'Failed to remove role');
            }
        }
    };

    if (loading) {
        return (
            <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="60vh">
                <CircularProgress size={60} />
                <Typography variant="h6" sx={{ mt: 2 }}>Loading RBAC System...</Typography>
            </Box>
        );
    }

    const assignedPerms = rolePermissions.map(p => p.id);
    const availPerms = availablePermissions.filter(p => !assignedPerms.includes(p.id));

    return (
        <Box sx={{ p: 3, bgcolor: 'background.default', minHeight: '100vh' }}>
            {/* Header */}
            <Box sx={{ mb: 4 }}>
                <Stack direction="row" spacing={2} alignItems="center">
                    <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
                        <SecurityIcon fontSize="large" />
                    </Avatar>
                    <Box>
                        <Typography variant="h4" fontWeight="bold">
                            Role & Permission Management
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Enterprise-grade access control system
                        </Typography>
                    </Box>
                </Stack>
            </Box>

            {/* Alerts */}
            {error && (
                <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}
            {success && (
                <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>
                    {success}
                </Alert>
            )}

            {/* Enhanced Tabs */}
            <Paper
                elevation={2}
                sx={{
                    mb: 3,
                    borderRadius: 3,
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255,255,255,0.1)'
                }}
            >
                <Tabs
                    value={tabValue}
                    onChange={(_, v) => setTabValue(v)}
                    variant="fullWidth"
                    sx={{
                        '& .MuiTabs-indicator': {
                            height: 4,
                            borderRadius: 2,
                            background: 'linear-gradient(90deg, #2196f3 0%, #21cbf3 100%)'
                        },
                        '& .MuiTab-root': {
                            py: 2.5,
                            fontSize: '1rem',
                            fontWeight: 600,
                            textTransform: 'none',
                            color: 'text.secondary',
                            transition: 'all 0.3s ease',
                            '&:hover': {
                                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                                color: 'primary.main'
                            },
                            '&.Mui-selected': {
                                color: 'primary.main',
                                fontWeight: 700
                            }
                        }
                    }}
                >
                    <Tab
                        icon={<SecurityIcon sx={{ mr: 1 }} />}
                        label="Roles"
                        iconPosition="start"
                        sx={{
                            '& .MuiTab-iconWrapper': {
                                color: tabValue === 0 ? '#2196f3' : 'inherit'
                            }
                        }}
                    />
                    <Tab
                        icon={<PermissionIcon sx={{ mr: 1 }} />}
                        label="Permissions Matrix"
                        iconPosition="start"
                        sx={{
                            '& .MuiTab-iconWrapper': {
                                color: tabValue === 1 ? '#ff9800' : 'inherit'
                            }
                        }}
                    />
                    <Tab
                        icon={<PersonIcon sx={{ mr: 1 }} />}
                        label="User Assignments"
                        iconPosition="start"
                        sx={{
                            '& .MuiTab-iconWrapper': {
                                color: tabValue === 2 ? '#4caf50' : 'inherit'
                            }
                        }}
                    />
                </Tabs>
            </Paper>

            {/* Tab Panels */}
            {tabValue === 0 && (
                <Box>
                    {/* Role Overview Stats */}
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={12} sm={4}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 203, 243, 0.05) 100%)',
                                    border: '1px solid rgba(33, 150, 243, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#2196f3', width: 48, height: 48 }}>
                                        <SecurityIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="primary.main">
                                            {roles.length}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Total Roles
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(139, 195, 74, 0.05) 100%)',
                                    border: '1px solid rgba(76, 175, 80, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#4caf50', width: 48, height: 48 }}>
                                        <CheckIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="success.main">
                                            {roles.filter(r => r.is_active).length}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Active Roles
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(233, 30, 99, 0.05) 100%)',
                                    border: '1px solid rgba(244, 67, 54, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#f44336', width: 48, height: 48 }}>
                                        <AdminIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="error.main">
                                            {roles.filter(r => r.is_system).length}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            System Roles
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                    </Grid>

                    {/* Enhanced Role Cards */}
                    <Grid container spacing={3}>
                        {roles.map((role) => (
                            <Grid item xs={12} md={6} lg={4} key={role.id}>
                                <Card
                                    className="interactive-card"
                                    sx={{
                                        height: '100%',
                                        position: 'relative',
                                        background: `linear-gradient(135deg, ${alpha(getRoleColor(role.name), 0.1)} 0%, rgba(255,255,255,0.05) 100%)`,
                                        border: `2px solid ${alpha(getRoleColor(role.name), 0.3)}`,
                                        borderRadius: 3,
                                        overflow: 'hidden'
                                    }}
                                >
                                    {/* Header gradient overlay */}
                                    <Box
                                        sx={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                            right: 0,
                                            height: 4,
                                            background: `linear-gradient(90deg, ${getRoleColor(role.name)} 0%, ${alpha(getRoleColor(role.name), 0.7)} 100%)`
                                        }}
                                    />

                                    {role.is_system && (
                                        <Chip
                                            label="System Role"
                                            size="small"
                                            sx={{
                                                position: 'absolute',
                                                top: 12,
                                                right: 12,
                                                background: alpha('#2196f3', 0.9),
                                                color: 'white',
                                                fontWeight: 600,
                                                zIndex: 1
                                            }}
                                        />
                                    )}

                                    <CardContent sx={{ p: 3 }}>
                                        <Stack spacing={2.5}>
                                            <Box display="flex" alignItems="center" gap={2.5}>
                                                <Box
                                                    sx={{
                                                        position: 'relative',
                                                        '&::before': {
                                                            content: '""',
                                                            position: 'absolute',
                                                            top: -4,
                                                            left: -4,
                                                            right: -4,
                                                            bottom: -4,
                                                            background: `radial-gradient(circle, ${alpha(getRoleColor(role.name), 0.3)} 0%, transparent 70%)`,
                                                            borderRadius: '50%',
                                                            zIndex: -1
                                                        }
                                                    }}
                                                >
                                                    <Avatar
                                                        sx={{
                                                            bgcolor: getRoleColor(role.name),
                                                            width: 64,
                                                            height: 64,
                                                            boxShadow: `0 8px 24px ${alpha(getRoleColor(role.name), 0.4)}`
                                                        }}
                                                    >
                                                        {getRoleIcon(role.name)}
                                                    </Avatar>
                                                </Box>
                                                <Box flex={1}>
                                                    <Typography variant="h5" fontWeight="bold" gutterBottom>
                                                        {role.name}
                                                    </Typography>
                                                    <Stack direction="row" spacing={1} alignItems="center">
                                                        <Chip
                                                            label={role.is_active ? 'Active' : 'Inactive'}
                                                            size="small"
                                                            color={role.is_active ? 'success' : 'default'}
                                                            sx={{
                                                                fontWeight: 600,
                                                                '& .MuiChip-label': {
                                                                    px: 2
                                                                }
                                                            }}
                                                        />
                                                        {role.is_system && (
                                                            <Chip
                                                                label="Protected"
                                                                size="small"
                                                                variant="outlined"
                                                                sx={{
                                                                    fontWeight: 600,
                                                                    borderColor: alpha('#2196f3', 0.7),
                                                                    color: '#2196f3'
                                                                }}
                                                            />
                                                        )}
                                                    </Stack>
                                                </Box>
                                            </Box>

                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                                sx={{
                                                    minHeight: 48,
                                                    lineHeight: 1.6,
                                                    display: '-webkit-box',
                                                    WebkitLineClamp: 2,
                                                    WebkitBoxOrient: 'vertical',
                                                    overflow: 'hidden'
                                                }}
                                            >
                                                {role.description || 'No description provided'}
                                            </Typography>

                                            <Button
                                                variant="contained"
                                                fullWidth
                                                startIcon={<PermissionIcon />}
                                                onClick={() => handleOpenRolePermissions(role)}
                                                sx={{
                                                    background: `linear-gradient(135deg, ${getRoleColor(role.name)} 0%, ${alpha(getRoleColor(role.name), 0.8)} 100%)`,
                                                    color: 'white',
                                                    fontWeight: 600,
                                                    py: 1.5,
                                                    borderRadius: 2,
                                                    textTransform: 'none',
                                                    fontSize: '0.95rem',
                                                    '&:hover': {
                                                        background: `linear-gradient(135deg, ${alpha(getRoleColor(role.name), 0.9)} 0%, ${alpha(getRoleColor(role.name), 0.7)} 100%)`,
                                                        transform: 'translateY(-1px)',
                                                        boxShadow: `0 8px 20px ${alpha(getRoleColor(role.name), 0.4)}`
                                                    }
                                                }}
                                            >
                                                Manage Permissions
                                            </Button>
                                        </Stack>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                </Box>
            )}

            {tabValue === 1 && (
                <Box>
                    {/* Permissions Overview */}
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={12} sm={6} md={3}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(255, 193, 7, 0.05) 100%)',
                                    border: '1px solid rgba(255, 152, 0, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#ff9800', width: 48, height: 48 }}>
                                        <PermissionIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="warning.main">
                                            {permissions?.length || 0}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Total Permissions
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 203, 243, 0.05) 100%)',
                                    border: '1px solid rgba(33, 150, 243, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#2196f3', width: 48, height: 48 }}>
                                        <SecurityIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="primary.main">
                                            {permissions?.length ? new Set(permissions.map(p => p.resource)).size : 0}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Resource Types
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(139, 195, 74, 0.05) 100%)',
                                    border: '1px solid rgba(76, 175, 80, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#4caf50', width: 48, height: 48 }}>
                                        <CheckIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="success.main">
                                            {permissions?.length ? permissions.filter(p => p.action === 'create').length : 0}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Create Actions
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(156, 39, 176, 0.1) 0%, rgba(233, 30, 99, 0.05) 100%)',
                                    border: '1px solid rgba(156, 39, 176, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#9c27b0', width: 48, height: 48 }}>
                                        <EditIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="secondary.main">
                                            {permissions?.length ? permissions.filter(p => p.action === 'update').length : 0}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Update Actions
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                    </Grid>

                    {/* Enhanced Permissions Matrix */}
                    {permissions && permissions.length > 0 ? (
                        <Grid container spacing={3}>
                            {(() => {
                                try {
                                    const groupedPermissions = permissions.reduce((acc, perm) => {
                                        if (!acc[perm.resource]) acc[perm.resource] = [];
                                        acc[perm.resource].push(perm);
                                        return acc;
                                    }, {} as Record<string, Permission[]>);

                                    return Object.entries(groupedPermissions).map(([resource, perms]) => (
                                        <Grid item xs={12} md={6} lg={4} key={resource}>
                                            <Card
                                                className="interactive-card"
                                                sx={{
                                                    height: '100%',
                                                    background: 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
                                                    border: '2px solid rgba(255,255,255,0.1)',
                                                    borderRadius: 3,
                                                    overflow: 'hidden'
                                                }}
                                            >
                                                {/* Header gradient */}
                                                <Box
                                                    sx={{
                                                        position: 'absolute',
                                                        top: 0,
                                                        left: 0,
                                                        right: 0,
                                                        height: 4,
                                                        background: 'linear-gradient(90deg, #ff9800 0%, #ffc107 100%)'
                                                    }}
                                                />

                                                <CardContent sx={{ p: 3 }}>
                                                    <Stack spacing={2.5}>
                                                        <Box display="flex" alignItems="center" gap={2}>
                                                            <Box
                                                                sx={{
                                                                    position: 'relative',
                                                                    '&::before': {
                                                                        content: '""',
                                                                        position: 'absolute',
                                                                        top: -3,
                                                                        left: -3,
                                                                        right: -3,
                                                                        bottom: -3,
                                                                        background: `radial-gradient(circle, rgba(255, 152, 0, 0.3) 0%, transparent 70%)`,
                                                                        borderRadius: '50%',
                                                                        zIndex: -1
                                                                    }
                                                                }}
                                                            >
                                                                <Avatar
                                                                    sx={{
                                                                        bgcolor: '#ff9800',
                                                                        width: 56,
                                                                        height: 56,
                                                                        boxShadow: '0 8px 24px rgba(255, 152, 0, 0.4)'
                                                                    }}
                                                                >
                                                                    <PermissionIcon />
                                                                </Avatar>
                                                            </Box>
                                                            <Box flex={1}>
                                                                <Typography variant="h6" fontWeight="bold" gutterBottom>
                                                                    {resource}
                                                                </Typography>
                                                                <Typography variant="body2" color="text.secondary">
                                                                    {perms.length} permission{perms.length !== 1 ? 's' : ''}
                                                                </Typography>
                                                            </Box>
                                                        </Box>

                                                        <Box>
                                                            <Typography variant="subtitle2" gutterBottom fontWeight="600" color="text.primary">
                                                                Available Actions:
                                                            </Typography>
                                                            <Box display="flex" flexWrap="wrap" gap={1}>
                                                                {perms.map((perm) => (
                                                                    <Tooltip key={perm.id} title={perm.description || `${perm.action} ${resource}`}>
                                                                        <Chip
                                                                            label={perm.action}
                                                                            size="small"
                                                                            sx={{
                                                                                background: `linear-gradient(135deg, ${getActionColor(perm.action)} 0%, ${alpha(getActionColor(perm.action), 0.8)} 100%)`,
                                                                                color: 'white',
                                                                                fontWeight: 600,
                                                                                textTransform: 'capitalize',
                                                                                '&:hover': {
                                                                                    transform: 'scale(1.05)',
                                                                                    boxShadow: `0 4px 12px ${alpha(getActionColor(perm.action), 0.4)}`
                                                                                }
                                                                            }}
                                                                        />
                                                                    </Tooltip>
                                                                ))}
                                                            </Box>
                                                        </Box>
                                                    </Stack>
                                                </CardContent>
                                            </Card>
                                        </Grid>
                                    ));
                                } catch (error) {
                                    console.error('Error rendering permissions matrix:', error);
                                    return (
                                        <Grid item xs={12}>
                                            <Alert severity="error">
                                                Error rendering permissions. Please check the console for details.
                                            </Alert>
                                        </Grid>
                                    );
                                }
                            })()}
                        </Grid>
                    ) : (
                        <Box textAlign="center" py={8}>
                            <PermissionIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
                            <Typography variant="h6" color="text.secondary">
                                No permissions found
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Permissions will appear here once they are configured in the system.
                            </Typography>
                        </Box>
                    )}
                </Box>
            )}

            {tabValue === 2 && (
                <Box>
                    {/* User Assignment Overview */}
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={12} sm={4}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(156, 39, 176, 0.1) 0%, rgba(233, 30, 99, 0.05) 100%)',
                                    border: '1px solid rgba(156, 39, 176, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#9c27b0', width: 48, height: 48 }}>
                                        <PersonIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="secondary.main">
                                            {users.length}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Total Users
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(233, 30, 99, 0.05) 100%)',
                                    border: '1px solid rgba(244, 67, 54, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#f44336', width: 48, height: 48 }}>
                                        <AdminIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="error.main">
                                            {users.filter(u => u.email.includes('admin')).length}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Administrators
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                        <Grid item xs={12} sm={4}>
                            <Paper
                                elevation={1}
                                sx={{
                                    p: 2,
                                    background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 203, 243, 0.05) 100%)',
                                    border: '1px solid rgba(33, 150, 243, 0.2)',
                                    borderRadius: 2
                                }}
                            >
                                <Stack direction="row" spacing={2} alignItems="center">
                                    <Avatar sx={{ bgcolor: '#2196f3', width: 48, height: 48 }}>
                                        <ManagerIcon />
                                    </Avatar>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold" color="primary.main">
                                            {users.filter(u => u.email.includes('manager')).length}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Managers
                                        </Typography>
                                    </Box>
                                </Stack>
                            </Paper>
                        </Grid>
                    </Grid>

                    {/* Enhanced User Assignment Cards */}
                    <Grid container spacing={3}>
                        {users.slice(0, 50).map((user) => (
                            <Grid item xs={12} sm={6} md={4} lg={3} key={user.id}>
                                <Card
                                    className="interactive-card"
                                    sx={{
                                        cursor: 'pointer',
                                        background: 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
                                        border: '2px solid rgba(255,255,255,0.1)',
                                        borderRadius: 3,
                                        overflow: 'hidden',
                                        '&:hover': {
                                            borderColor: '#2196f3',
                                            background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(255,255,255,0.05) 100%)'
                                        }
                                    }}
                                    onClick={() => handleOpenUserRoles(user)}
                                >
                                    {/* Header gradient */}
                                    <Box
                                        sx={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                            right: 0,
                                            height: 4,
                                            background: `linear-gradient(90deg, ${getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst')} 0%, ${alpha(getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst'), 0.7)} 100%)`
                                        }}
                                    />

                                    <CardContent sx={{ p: 3 }}>
                                        <Stack spacing={2.5} alignItems="center">
                                            <Box
                                                sx={{
                                                    position: 'relative',
                                                    '&::before': {
                                                        content: '""',
                                                        position: 'absolute',
                                                        top: -3,
                                                        left: -3,
                                                        right: -3,
                                                        bottom: -3,
                                                        background: `radial-gradient(circle, ${alpha(getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst'), 0.3)} 0%, transparent 70%)`,
                                                        borderRadius: '50%',
                                                        zIndex: -1
                                                    }
                                                }}
                                            >
                                                <Avatar
                                                    sx={{
                                                        bgcolor: getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst'),
                                                        width: 64,
                                                        height: 64,
                                                        boxShadow: `0 8px 24px ${alpha(getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst'), 0.4)}`
                                                    }}
                                                >
                                                    <UserIcon />
                                                </Avatar>
                                            </Box>

                                            <Box textAlign="center" sx={{ width: '100%' }}>
                                                <Typography variant="h6" fontWeight="bold" gutterBottom noWrap>
                                                    {user.username}
                                                </Typography>
                                                <Typography
                                                    variant="body2"
                                                    color="text.secondary"
                                                    sx={{
                                                        display: '-webkit-box',
                                                        WebkitLineClamp: 2,
                                                        WebkitBoxOrient: 'vertical',
                                                        overflow: 'hidden',
                                                        minHeight: '2.5em',
                                                        lineHeight: 1.25
                                                    }}
                                                >
                                                    {user.email}
                                                </Typography>
                                            </Box>

                                            <Button
                                                variant="contained"
                                                size="small"
                                                startIcon={<SecurityIcon />}
                                                sx={{
                                                    background: `linear-gradient(135deg, ${getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst')} 0%, ${alpha(getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst'), 0.8)} 100%)`,
                                                    color: 'white',
                                                    fontWeight: 600,
                                                    textTransform: 'none',
                                                    borderRadius: 2,
                                                    '&:hover': {
                                                        transform: 'translateY(-1px)',
                                                        boxShadow: `0 4px 12px ${alpha(getRoleColor(user.email.includes('admin') ? 'admin' : user.email.includes('manager') ? 'manager' : 'analyst'), 0.4)}`
                                                    }
                                                }}
                                            >
                                                Manage Roles
                                            </Button>
                                        </Stack>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>

                    {users.length > 50 && (
                        <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ mt: 2 }}>
                            Showing first 50 users. Use search to find specific users.
                        </Typography>
                    )}
                </Box>
            )}

            {/* Permission Drag-and-Drop Dialog */}
            <Dialog
                open={openPermissionDialog}
                onClose={() => setOpenPermissionDialog(false)}
                maxWidth="lg"
                fullWidth
                PaperProps={{
                    sx: { minHeight: '70vh', borderRadius: 3 }
                }}
            >
                <DialogTitle>
                    <Stack direction="row" alignItems="center" spacing={2}>
                        <Avatar sx={{ bgcolor: selectedRole ? getRoleColor(selectedRole.name) : 'grey.500' }}>
                            {selectedRole && getRoleIcon(selectedRole.name)}
                        </Avatar>
                        <Box>
                            <Typography variant="h5">Manage Permissions</Typography>
                            <Typography variant="body2" color="text.secondary">
                                {selectedRole?.name} role - Drag permissions between lists
                            </Typography>
                        </Box>
                    </Stack>
                </DialogTitle>

                <DialogContent>
                    <DragDropContext onDragEnd={handleDragEnd}>
                        <Grid container spacing={3}>
                            {/* Available Permissions */}
                            <Grid item xs={12} md={6}>
                                <Paper
                                    sx={{
                                        p: 2,
                                        bgcolor: alpha('#2196f3', 0.05),
                                        border: `2px dashed ${alpha('#2196f3', 0.3)}`,
                                        minHeight: 400
                                    }}
                                >
                                    <Typography variant="h6" gutterBottom color="primary">
                                        📦 Available Permissions ({availPerms.length})
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                                        Drag permissions here to assign them
                                    </Typography>

                                    <Droppable droppableId="available">
                                        {(provided, snapshot) => (
                                            <Box
                                                ref={provided.innerRef}
                                                {...provided.droppableProps}
                                                sx={{
                                                    mt: 2,
                                                    minHeight: 300,
                                                    bgcolor: snapshot.isDraggingOver ? alpha('#2196f3', 0.1) : 'transparent',
                                                    borderRadius: 2,
                                                    p: 1
                                                }}
                                            >
                                                {availPerms.map((perm, index) => (
                                                    <Draggable
                                                        key={perm.id}
                                                        draggableId={`perm-${perm.id}`}
                                                        index={index}
                                                    >
                                                        {(provided, snapshot) => (
                                                            <Paper
                                                                ref={provided.innerRef}
                                                                {...provided.draggableProps}
                                                                {...provided.dragHandleProps}
                                                                sx={{
                                                                    p: 1.5,
                                                                    mb: 1,
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: 1,
                                                                    cursor: 'grab',
                                                                    bgcolor: snapshot.isDragging ? 'primary.light' : 'background.paper',
                                                                    '&:hover': {
                                                                        bgcolor: 'action.hover'
                                                                    }
                                                                }}
                                                            >
                                                                <DragIcon color="action" />
                                                                <Chip
                                                                    label={perm.name}
                                                                    size="small"
                                                                    variant="outlined"
                                                                    sx={{ flex: 1 }}
                                                                />
                                                            </Paper>
                                                        )}
                                                    </Draggable>
                                                ))}
                                                {provided.placeholder}
                                            </Box>
                                        )}
                                    </Droppable>
                                </Paper>
                            </Grid>

                            {/* Assigned Permissions */}
                            <Grid item xs={12} md={6}>
                                <Paper
                                    sx={{
                                        p: 2,
                                        bgcolor: alpha('#4caf50', 0.05),
                                        border: `2px dashed ${alpha('#4caf50', 0.3)}`,
                                        minHeight: 400
                                    }}
                                >
                                    <Typography variant="h6" gutterBottom color="success.main">
                                        ✅ Assigned Permissions ({rolePermissions.length})
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                                        Drag permissions here to remove them
                                    </Typography>

                                    <Droppable droppableId="assigned">
                                        {(provided, snapshot) => (
                                            <Box
                                                ref={provided.innerRef}
                                                {...provided.droppableProps}
                                                sx={{
                                                    mt: 2,
                                                    minHeight: 300,
                                                    bgcolor: snapshot.isDraggingOver ? alpha('#4caf50', 0.1) : 'transparent',
                                                    borderRadius: 2,
                                                    p: 1
                                                }}
                                            >
                                                {rolePermissions.map((perm, index) => (
                                                    <Draggable
                                                        key={perm.id}
                                                        draggableId={`perm-${perm.id}`}
                                                        index={index}
                                                    >
                                                        {(provided, snapshot) => (
                                                            <Paper
                                                                ref={provided.innerRef}
                                                                {...provided.draggableProps}
                                                                {...provided.dragHandleProps}
                                                                sx={{
                                                                    p: 1.5,
                                                                    mb: 1,
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: 1,
                                                                    cursor: 'grab',
                                                                    bgcolor: snapshot.isDragging ? 'success.light' : 'background.paper',
                                                                    border: '1px solid',
                                                                    borderColor: 'success.main',
                                                                    '&:hover': {
                                                                        bgcolor: 'action.hover'
                                                                    }
                                                                }}
                                                            >
                                                                <CheckIcon color="success" />
                                                                <Chip
                                                                    label={perm.name}
                                                                    size="small"
                                                                    color="success"
                                                                    sx={{ flex: 1 }}
                                                                />
                                                                <DragIcon color="action" />
                                                            </Paper>
                                                        )}
                                                    </Draggable>
                                                ))}
                                                {provided.placeholder}
                                            </Box>
                                        )}
                                    </Droppable>
                                </Paper>
                            </Grid>
                        </Grid>
                    </DragDropContext>
                </DialogContent>

                <DialogActions>
                    <Button onClick={() => setOpenPermissionDialog(false)} variant="contained">
                        Done
                    </Button>
                </DialogActions>
            </Dialog>

            {/* User Roles Dialog */}
            <Dialog
                open={openUserDialog}
                onClose={() => setOpenUserDialog(false)}
                maxWidth="sm"
                fullWidth
                PaperProps={{ sx: { borderRadius: 3 } }}
            >
                <DialogTitle>
                    <Stack direction="row" alignItems="center" spacing={2}>
                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                            <PersonIcon />
                        </Avatar>
                        <Box>
                            <Typography variant="h6">{selectedUser?.username}</Typography>
                            <Typography variant="caption" color="text.secondary">
                                {selectedUser?.email}
                            </Typography>
                        </Box>
                    </Stack>
                </DialogTitle>

                <DialogContent>
                    <Stack spacing={3}>
                        {/* Current Roles */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Current Roles:
                            </Typography>
                            <Stack direction="row" spacing={1} flexWrap="wrap">
                                {userRoles.map((role) => (
                                    <Chip
                                        key={role.id}
                                        avatar={
                                            <Avatar sx={{ bgcolor: getRoleColor(role.name) }}>
                                                {getRoleIcon(role.name)}
                                            </Avatar>
                                        }
                                        label={role.name}
                                        onDelete={
                                            role.is_system && role.name === 'admin' && selectedUser?.username === 'admin'
                                                ? undefined
                                                : () => handleRemoveRoleFromUser(role.id)
                                        }
                                        sx={{
                                            borderColor: getRoleColor(role.name),
                                            borderWidth: 2
                                        }}
                                        variant="outlined"
                                    />
                                ))}
                                {userRoles.length === 0 && (
                                    <Typography color="text.secondary">No roles assigned</Typography>
                                )}
                            </Stack>
                        </Box>

                        <Divider />

                        {/* Available Roles */}
                        <Box>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Assign New Role:
                            </Typography>
                            <Stack direction="row" spacing={1} flexWrap="wrap">
                                {roles
                                    .filter(r => !userRoles.some(ur => ur.id === r.id))
                                    .map((role) => (
                                        <Chip
                                            key={role.id}
                                            avatar={
                                                <Avatar sx={{ bgcolor: getRoleColor(role.name) }}>
                                                    {getRoleIcon(role.name)}
                                                </Avatar>
                                            }
                                            label={role.name}
                                            onClick={() => handleAssignRoleToUser(role.id)}
                                            sx={{
                                                cursor: 'pointer',
                                                '&:hover': {
                                                    bgcolor: alpha(getRoleColor(role.name), 0.1)
                                                }
                                            }}
                                            variant="outlined"
                                        />
                                    ))}
                            </Stack>
                        </Box>
                    </Stack>
                </DialogContent>

                <DialogActions>
                    <Button onClick={() => setOpenUserDialog(false)} variant="contained">
                        Done
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default RoleManagement;
