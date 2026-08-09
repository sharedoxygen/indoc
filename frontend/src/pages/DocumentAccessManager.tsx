import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Avatar,
    Chip,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Stack,
    Alert,
    TextField,
    Grid,
    alpha,
    Paper,
    Divider,
    IconButton,
    Tooltip,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction
} from '@mui/material';
import {
    Share as ShareIcon,
    Person as PersonIcon,
    Close as CloseIcon,
    Delete as DeleteIcon,
    AdminPanelSettings as AdminIcon,
    SupervisorAccount as ManagerIcon,
    WorkOutline as AnalystIcon,
    CalendarToday as CalendarIcon,
    CheckCircle as GrantedIcon
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { http } from '../services/http';
import { useSnackbar } from 'notistack';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DateTimePicker } from '@mui/x-date-pickers';

interface Document {
    id: number;
    uuid: string;
    filename: string;
    title: string;
    file_type: string;
}

interface User {
    id: number;
    email: string;
    full_name: string;
    role: string;
}

interface Role {
    id: number;
    name: string;
    description: string;
}

interface Permission {
    id: number;
    user_id: number;
    user_email: string;
    user_name: string;
    permission_type: string;
    granted_at: string;
    expires_at: string | null;
}

interface DocumentAccessManagerProps {
    open: boolean;
    onClose: () => void;
    selectedDocuments: Document[];
    onSuccess: () => void;
}

const getRoleIcon = (roleName: string) => {
    switch (roleName.toLowerCase()) {
        case 'admin': return <AdminIcon />;
        case 'manager': return <ManagerIcon />;
        default: return <AnalystIcon />;
    }
};

const getRoleColor = (roleName: string) => {
    switch (roleName.toLowerCase()) {
        case 'admin': return '#f44336';
        case 'manager': return '#2196f3';
        default: return '#4caf50';
    }
};

const DocumentAccessManager: React.FC<DocumentAccessManagerProps> = ({
    open,
    onClose,
    selectedDocuments,
    onSuccess
}) => {
    const [users, setUsers] = useState<User[]>([]);
    const [roles, setRoles] = useState<Role[]>([]);
    const [availableUsers, setAvailableUsers] = useState<User[]>([]);
    const [grantedUsers, setGrantedUsers] = useState<User[]>([]);
    const [expirationDate, setExpirationDate] = useState<Date | null>(null);
    const [permissionType, setPermissionType] = useState<string>('read');
    const [loading, setLoading] = useState(false);
    const { enqueueSnackbar } = useSnackbar();

    useEffect(() => {
        if (open) {
            fetchData();
        }
    }, [open]);

    const fetchData = async () => {
        try {
            setLoading(true);

            // Fetch roles (required for role-based sharing)
            const rolesRes = await http.get('/rbac/roles');
            setRoles(rolesRes.data || []);

            // Try to fetch users for individual user sharing (admin only)
            try {
                const usersRes = await http.get('/users/');
                const usersData = usersRes.data || [];
                setUsers(usersData);
                setAvailableUsers(usersData);
                setGrantedUsers([]);
            } catch (usersErr: any) {
                // If users API fails (non-admin), enable role-only mode
                if (usersErr.response?.status === 403) {
                    console.log('User list not available - using role-based sharing only');
                    setUsers([]);
                    setAvailableUsers([]);
                    setGrantedUsers([]);
                } else {
                    throw usersErr;
                }
            }
        } catch (err: any) {
            console.error('Failed to load sharing data:', err);
            enqueueSnackbar('Failed to load sharing options', { variant: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleDragEnd = (result: any) => {
        if (!result.destination) return;

        const { source, destination, draggableId } = result;
        const userId = parseInt(draggableId.replace('user-', ''));
        const user = users.find(u => u.id === userId);

        if (!user) return;

        // Moving from available to granted
        if (source.droppableId === 'available' && destination.droppableId === 'granted') {
            setAvailableUsers(prev => prev.filter(u => u.id !== userId));
            setGrantedUsers(prev => [...prev, user]);
        }

        // Moving from granted to available
        if (source.droppableId === 'granted' && destination.droppableId === 'available') {
            setGrantedUsers(prev => prev.filter(u => u.id !== userId));
            setAvailableUsers(prev => [...prev, user]);
        }
    };

    const handleGrantAccess = async () => {
        if (grantedUsers.length === 0) {
            enqueueSnackbar('No users or roles selected for access grant', { variant: 'warning' });
            return;
        }

        try {
            setLoading(true);

            const documentIds = selectedDocuments.map(d => d.id);

            if (availableUsers.length > 0) {
                // Individual user sharing mode
                const userIds = grantedUsers.map(u => u.id);
                await http.post('/access/bulk-grant', {
                    document_ids: documentIds,
                    user_ids: userIds,
                    permission_type: permissionType,
                    expires_at: expirationDate ? expirationDate.toISOString() : null,
                    reason: `Bulk access grant via drag-and-drop: ${grantedUsers.length} users to ${selectedDocuments.length} documents`
                });

                enqueueSnackbar(
                    `Access granted to ${grantedUsers.length} user(s) for ${selectedDocuments.length} document(s)`,
                    { variant: 'success' }
                );
            } else {
                // Role-based sharing mode (when users API is not available)
                // For role-based sharing, we need to use a different approach
                // Since we don't have individual users, we'll use role-based permissions
                // This would require a different API endpoint for role-based bulk grants

                enqueueSnackbar(
                    'Role-based sharing not yet implemented in this version. Please use individual user sharing.',
                    { variant: 'info' }
                );
                return;
            }

            onSuccess();
            onClose();
        } catch (err: any) {
            enqueueSnackbar(
                err.response?.data?.detail || 'Failed to grant access',
                { variant: 'error' }
            );
        } finally {
            setLoading(false);
        }
    };

    const handleGrantByRole = async (role: Role) => {
        const roleUsers = users.filter(u => u.role.toLowerCase() === role.name.toLowerCase());
        setGrantedUsers(prev => {
            const existing = new Set(prev.map(u => u.id));
            const newUsers = roleUsers.filter(u => !existing.has(u.id));
            return [...prev, ...newUsers];
        });
        setAvailableUsers(prev => prev.filter(u => u.role.toLowerCase() !== role.name.toLowerCase()));

        enqueueSnackbar(`Added all ${role.name} users to granted list`, { variant: 'info' });
    };

    const handleRevokeByRole = async (role: Role) => {
        const roleUsers = users.filter(u => u.role.toLowerCase() === role.name.toLowerCase());
        setGrantedUsers(prev => prev.filter(u => u.role.toLowerCase() !== role.name.toLowerCase()));
        setAvailableUsers(prev => {
            const existing = new Set(prev.map(u => u.id));
            const newUsers = roleUsers.filter(u => !existing.has(u.id));
            return [...prev, ...newUsers];
        });

        enqueueSnackbar(`Removed all ${role.name} users from granted list`, { variant: 'info' });
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: { minHeight: '80vh', borderRadius: 3 }
            }}
        >
            <DialogTitle>
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                    <Stack direction="row" spacing={2} alignItems="center">
                        <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
                            <ShareIcon fontSize="large" />
                        </Avatar>
                        <Box>
                            <Typography variant="h5">Manage Document Access</Typography>
                            <Typography variant="body2" color="text.secondary">
                                {selectedDocuments.length} document{selectedDocuments.length > 1 ? 's' : ''} selected
                            </Typography>
                        </Box>
                    </Stack>
                    <IconButton onClick={onClose}>
                        <CloseIcon />
                    </IconButton>
                </Stack>
            </DialogTitle>

            <DialogContent>
                {/* Selected Documents */}
                <Paper sx={{ p: 2, mb: 3, bgcolor: alpha('#2196f3', 0.05) }}>
                    <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                        Selected Documents:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                        {selectedDocuments.map(doc => (
                            <Chip
                                key={doc.id}
                                label={doc.title || doc.filename}
                                size="small"
                                color="primary"
                                variant="outlined"
                            />
                        ))}
                    </Stack>
                </Paper>

                {/* Quick Role Assignment */}
                <Paper sx={{ p: 2, mb: 3 }}>
                    <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                        Quick Grant by Role:
                    </Typography>
                    <Stack direction="row" spacing={1}>
                        {roles.slice(0, 3).map((role) => (
                            <Button
                                key={role.id}
                                variant="outlined"
                                size="small"
                                startIcon={getRoleIcon(role.name)}
                                onClick={() => handleGrantByRole(role)}
                                sx={{
                                    borderColor: getRoleColor(role.name),
                                    color: getRoleColor(role.name),
                                    '&:hover': {
                                        borderColor: getRoleColor(role.name),
                                        bgcolor: alpha(getRoleColor(role.name), 0.1)
                                    }
                                }}
                            >
                                Grant to All {role.name}s
                            </Button>
                        ))}
                    </Stack>
                </Paper>

                {/* Permission Settings */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} md={6}>
                        <TextField
                            select
                            fullWidth
                            label="Permission Type"
                            value={permissionType}
                            onChange={(e) => setPermissionType(e.target.value)}
                            SelectProps={{ native: true }}
                        >
                            <option value="read">Read Only</option>
                            <option value="write">Read & Write</option>
                            <option value="share">Read, Write & Share</option>
                            <option value="delete">Full Control (Delete)</option>
                        </TextField>
                    </Grid>
                    <Grid item xs={12} md={6}>
                        <LocalizationProvider dateAdapter={AdapterDateFns}>
                            <DateTimePicker
                                label="Expiration Date (Optional)"
                                value={expirationDate}
                                onChange={(newValue) => setExpirationDate(newValue)}
                                slotProps={{
                                    textField: { fullWidth: true }
                                }}
                            />
                        </LocalizationProvider>
                    </Grid>
                </Grid>

                {/* Drag and Drop Interface */}
                <DragDropContext onDragEnd={handleDragEnd}>
                    <Grid container spacing={3}>
                        {/* Available Users */}
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
                                    📦 Available Users ({availableUsers.length})
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                                    {availableUsers.length > 0
                                        ? "Drag users here to grant access"
                                        : "User list not available - use role-based sharing above"}
                                </Typography>

                                <Droppable droppableId="available">
                                    {(provided, snapshot) => (
                                        <Box
                                            ref={provided.innerRef}
                                            {...provided.droppableProps}
                                            sx={{
                                                minHeight: 300,
                                                bgcolor: snapshot.isDraggingOver ? alpha('#2196f3', 0.1) : 'transparent',
                                                borderRadius: 2,
                                                p: 1
                                            }}
                                        >
                                            {availableUsers.map((user, index) => (
                                                <Draggable
                                                    key={user.id}
                                                    draggableId={`user-${user.id}`}
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
                                                            <Avatar sx={{ bgcolor: getRoleColor(user.role), width: 32, height: 32 }}>
                                                                {getRoleIcon(user.role)}
                                                            </Avatar>
                                                            <Box flex={1}>
                                                                <Typography variant="body2" fontWeight="bold">
                                                                    {user.full_name || user.email}
                                                                </Typography>
                                                                <Chip
                                                                    label={user.role}
                                                                    size="small"
                                                                    sx={{
                                                                        bgcolor: getRoleColor(user.role),
                                                                        color: 'white',
                                                                        height: 18,
                                                                        fontSize: '0.7rem'
                                                                    }}
                                                                />
                                                            </Box>
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

                        {/* Granted Users */}
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
                                    ✅ Access Granted ({grantedUsers.length})
                                </Typography>
                                <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                                    {availableUsers.length > 0
                                        ? "Drag users here to revoke access"
                                        : "Role-based permissions will be applied to all users in selected roles"}
                                </Typography>

                                <Droppable droppableId="granted">
                                    {(provided, snapshot) => (
                                        <Box
                                            ref={provided.innerRef}
                                            {...provided.droppableProps}
                                            sx={{
                                                minHeight: 300,
                                                bgcolor: snapshot.isDraggingOver ? alpha('#4caf50', 0.1) : 'transparent',
                                                borderRadius: 2,
                                                p: 1
                                            }}
                                        >
                                            {grantedUsers.map((user, index) => (
                                                <Draggable
                                                    key={user.id}
                                                    draggableId={`user-${user.id}`}
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
                                                            <GrantedIcon color="success" />
                                                            <Avatar sx={{ bgcolor: getRoleColor(user.role), width: 32, height: 32 }}>
                                                                {getRoleIcon(user.role)}
                                                            </Avatar>
                                                            <Box flex={1}>
                                                                <Typography variant="body2" fontWeight="bold">
                                                                    {user.full_name || user.email}
                                                                </Typography>
                                                                <Chip
                                                                    label={user.role}
                                                                    size="small"
                                                                    sx={{
                                                                        bgcolor: getRoleColor(user.role),
                                                                        color: 'white',
                                                                        height: 18,
                                                                        fontSize: '0.7rem'
                                                                    }}
                                                                />
                                                            </Box>
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

                {/* Summary */}
                {grantedUsers.length > 0 && (
                    <Alert severity="info" sx={{ mt: 3 }}>
                        <Typography variant="body2">
                            <strong>{grantedUsers.length} user(s)</strong> will receive{' '}
                            <strong>{permissionType}</strong> access to{' '}
                            <strong>{selectedDocuments.length} document(s)</strong>
                            {expirationDate && (
                                <> until <strong>{expirationDate.toLocaleDateString()}</strong></>
                            )}
                        </Typography>
                    </Alert>
                )}
            </DialogContent>

            <DialogActions sx={{ p: 3 }}>
                <Button onClick={onClose} variant="outlined">
                    Cancel
                </Button>
                <Button
                    onClick={handleGrantAccess}
                    variant="contained"
                    disabled={loading || grantedUsers.length === 0}
                    startIcon={<ShareIcon />}
                >
                    Grant Access
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default DocumentAccessManager;

