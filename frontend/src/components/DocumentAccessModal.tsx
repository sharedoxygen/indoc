import React, { useState, useEffect } from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    IconButton,
    Chip,
    Avatar,
    Box,
    Typography,
    Alert,
    CircularProgress,
    Divider,
    Stack,
    Autocomplete,
    FormHelperText,
} from '@mui/material'
import {
    Delete as DeleteIcon,
    Add as AddIcon,
    Person as PersonIcon,
    Shield as ShieldIcon,
    AccessTime as AccessTimeIcon,
    CheckCircle as GrantedIcon,
} from '@mui/icons-material'
import { useSnackbar } from 'notistack'
import { http } from '../services/http'

interface User {
    id: number
    email: string
    username: string
    full_name: string
    role: string
}

interface Permission {
    id: number
    document_id: number
    user_id: number
    user_email: string
    user_name: string
    permission_type: string
    granted_by: number
    granted_by_email: string
    granted_at: string
    expires_at: string | null
    reason: string | null
}

interface DocumentAccessModalProps {
    open: boolean
    onClose: () => void
    documentId: number
    documentTitle: string
    ownerEmail: string
    onPermissionChange?: () => void
}

const DocumentAccessModal: React.FC<DocumentAccessModalProps> = ({
    open,
    onClose,
    documentId,
    documentTitle,
    ownerEmail,
    onPermissionChange,
}) => {
    const { enqueueSnackbar } = useSnackbar()

    // State
    const [loading, setLoading] = useState(false)
    const [permissions, setPermissions] = useState<Permission[]>([])
    const [allUsers, setAllUsers] = useState<User[]>([])
    const [selectedUser, setSelectedUser] = useState<User | null>(null)
    const [permissionType, setPermissionType] = useState<string>('read')
    const [expiresAt, setExpiresAt] = useState<string>('')
    const [reason, setReason] = useState<string>('')
    const [submitting, setSubmitting] = useState(false)

    // Fetch permissions and users
    useEffect(() => {
        if (open) {
            fetchPermissions()
            fetchUsers()
        }
    }, [open, documentId])

    const fetchPermissions = async () => {
        try {
            setLoading(true)
            const response = await http.get(`/access/document/${documentId}`)
            setPermissions(response.data.permissions || [])
        } catch (err: any) {
            console.error('Failed to load permissions:', err)
            enqueueSnackbar(
                err.response?.data?.detail || 'Failed to load permissions',
                { variant: 'error' }
            )
        } finally {
            setLoading(false)
        }
    }

    const fetchUsers = async () => {
        try {
            const response = await http.get('/users/')
            setAllUsers(response.data)
        } catch (err) {
            console.error('Failed to load users:', err)
        }
    }

    const handleGrantPermission = async () => {
        if (!selectedUser) {
            enqueueSnackbar('Please select a user', { variant: 'warning' })
            return
        }

        setSubmitting(true)
        try {
            await http.post('/access/grant', {
                document_id: documentId,
                user_id: selectedUser.id,
                permission_type: permissionType,
                expires_at: expiresAt || null,
                reason: reason || null,
            })

            enqueueSnackbar(
                `Granted ${permissionType} access to ${selectedUser.full_name}`,
                { variant: 'success' }
            )

            // Reset form
            setSelectedUser(null)
            setPermissionType('read')
            setExpiresAt('')
            setReason('')

            // Refresh permissions
            fetchPermissions()

            // Notify parent
            if (onPermissionChange) {
                onPermissionChange()
            }
        } catch (err: any) {
            enqueueSnackbar(
                err.response?.data?.detail || 'Failed to grant permission',
                { variant: 'error' }
            )
        } finally {
            setSubmitting(false)
        }
    }

    const handleRevokePermission = async (permission: Permission) => {
        try {
            await http.post('/access/revoke', null, {
                params: {
                    document_id: documentId,
                    user_id: permission.user_id,
                    permission_type: permission.permission_type,
                }
            })

            enqueueSnackbar('Permission revoked', { variant: 'success' })
            fetchPermissions()

            if (onPermissionChange) {
                onPermissionChange()
            }
        } catch (err: any) {
            enqueueSnackbar(
                err.response?.data?.detail || 'Failed to revoke permission',
                { variant: 'error' }
            )
        }
    }

    const getPermissionColor = (type: string) => {
        switch (type) {
            case 'read':
                return 'info'
            case 'write':
                return 'warning'
            case 'share':
                return 'success'
            case 'delete':
                return 'error'
            default:
                return 'default'
        }
    }

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <DialogTitle>
                <Stack direction="row" spacing={2} alignItems="center">
                    <ShieldIcon />
                    <Box>
                        <Typography variant="h6">Document Access Control</Typography>
                        <Typography variant="caption" color="text.secondary">
                            {documentTitle}
                        </Typography>
                    </Box>
                </Stack>
            </DialogTitle>

            <DialogContent dividers>
                {/* Document Owner */}
                <Box mb={3}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Document Owner
                    </Typography>
                    <Chip
                        avatar={<Avatar><PersonIcon /></Avatar>}
                        label={ownerEmail}
                        color="primary"
                        icon={<PersonIcon />}
                    />
                </Box>

                <Divider sx={{ my: 2 }} />

                {/* Grant New Permission */}
                <Box mb={3}>
                    <Typography variant="subtitle2" gutterBottom>
                        Grant Access
                    </Typography>
                    <Stack spacing={2}>
                        <Autocomplete
                            options={allUsers}
                            getOptionLabel={(user) => `${user.full_name} (${user.email})`}
                            value={selectedUser}
                            onChange={(_, newValue) => setSelectedUser(newValue)}
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    label="Select User"
                                    placeholder="Search by name or email..."
                                />
                            )}
                            disabled={submitting}
                        />

                        <FormControl fullWidth>
                            <InputLabel>Permission Type</InputLabel>
                            <Select
                                value={permissionType}
                                label="Permission Type"
                                onChange={(e) => setPermissionType(e.target.value)}
                                disabled={submitting}
                            >
                                <MenuItem value="read">Read - View document</MenuItem>
                                <MenuItem value="write">Write - Edit metadata</MenuItem>
                                <MenuItem value="share">Share - Grant access to others</MenuItem>
                                <MenuItem value="delete">Delete - Remove document</MenuItem>
                            </Select>
                            <FormHelperText>
                                Higher permissions include lower ones (delete includes all)
                            </FormHelperText>
                        </FormControl>

                        <TextField
                            label="Expires At (Optional)"
                            type="datetime-local"
                            value={expiresAt}
                            onChange={(e) => setExpiresAt(e.target.value)}
                            InputLabelProps={{ shrink: true }}
                            disabled={submitting}
                            helperText="Leave empty for permanent access"
                        />

                        <TextField
                            label="Reason (Optional)"
                            multiline
                            rows={2}
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="Why is this access being granted?"
                            disabled={submitting}
                        />

                        <Button
                            variant="contained"
                            startIcon={submitting ? <CircularProgress size={16} /> : <AddIcon />}
                            onClick={handleGrantPermission}
                            disabled={!selectedUser || submitting}
                        >
                            Grant Access
                        </Button>
                    </Stack>
                </Box>

                <Divider sx={{ my: 2 }} />

                {/* Current Permissions */}
                <Box>
                    <Typography variant="subtitle2" gutterBottom>
                        Users with Access ({permissions.length})
                    </Typography>

                    {loading ? (
                        <Box display="flex" justifyContent="center" py={3}>
                            <CircularProgress />
                        </Box>
                    ) : permissions.length === 0 ? (
                        <Alert severity="info">
                            No additional users have explicit permissions.
                            The owner always has full access.
                        </Alert>
                    ) : (
                        <List>
                            {permissions.map((permission) => (
                                <ListItem key={permission.id} divider>
                                    <ListItemText
                                        primary={
                                            <Stack direction="row" spacing={1} alignItems="center">
                                                <Typography variant="body1">
                                                    {permission.user_name}
                                                </Typography>
                                                <Chip
                                                    label={permission.permission_type}
                                                    size="small"
                                                    color={getPermissionColor(permission.permission_type) as any}
                                                />
                                                {permission.expires_at && (
                                                    <Chip
                                                        icon={<AccessTimeIcon />}
                                                        label={`Expires ${new Date(permission.expires_at).toLocaleDateString()}`}
                                                        size="small"
                                                        variant="outlined"
                                                    />
                                                )}
                                            </Stack>
                                        }
                                        secondary={
                                            <Box mt={0.5}>
                                                <Typography variant="caption" color="text.secondary">
                                                    {permission.user_email}
                                                </Typography>
                                                <br />
                                                <Typography variant="caption" color="text.secondary">
                                                    Granted by {permission.granted_by_email} on{' '}
                                                    {new Date(permission.granted_at).toLocaleString()}
                                                </Typography>
                                                {permission.reason && (
                                                    <>
                                                        <br />
                                                        <Typography variant="caption" color="text.secondary">
                                                            Reason: {permission.reason}
                                                        </Typography>
                                                    </>
                                                )}
                                            </Box>
                                        }
                                    />
                                    <ListItemSecondaryAction>
                                        <IconButton
                                            edge="end"
                                            color="error"
                                            onClick={() => handleRevokePermission(permission)}
                                        >
                                            <DeleteIcon />
                                        </IconButton>
                                    </ListItemSecondaryAction>
                                </ListItem>
                            ))}
                        </List>
                    )}
                </Box>
            </DialogContent>

            <DialogActions>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    )
}

export default DocumentAccessModal


