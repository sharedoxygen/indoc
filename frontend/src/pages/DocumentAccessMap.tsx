import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Avatar,
    Chip,
    Button,
    Grid,
    Stack,
    Alert,
    CircularProgress,
    alpha,
    Paper,
    Tooltip,
    IconButton,
    TextField,
    InputAdornment
} from '@mui/material';
import {
    Person as PersonIcon,
    Description as DocumentIcon,
    AdminPanelSettings as AdminIcon,
    SupervisorAccount as ManagerIcon,
    WorkOutline as AnalystIcon,
    Search as SearchIcon,
    Refresh as RefreshIcon,
    Share as ShareIcon,
    Visibility as ViewIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    CalendarToday as CalendarIcon
} from '@mui/icons-material';
import { http } from '../services/http';
import { useSnackbar } from 'notistack';

interface DocumentAccess {
    document_id: number;
    document_title: string;
    document_type: string;
    owner_email: string;
    permissions: Array<{
        user_id: number;
        user_email: string;
        user_name: string;
        user_role: string;
        permission_type: string;
        granted_at: string;
        expires_at: string | null;
    }>;
}

const getRoleIcon = (role: string) => {
    switch (role.toLowerCase()) {
        case 'admin': return <AdminIcon fontSize="small" />;
        case 'manager': return <ManagerIcon fontSize="small" />;
        default: return <AnalystIcon fontSize="small" />;
    }
};

const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
        case 'admin': return '#f44336';
        case 'manager': return '#2196f3';
        default: return '#4caf50';
    }
};

const getPermissionColor = (permType: string) => {
    switch (permType.toLowerCase()) {
        case 'read': return '#2196f3';
        case 'write': return '#ff9800';
        case 'share': return '#9c27b0';
        case 'delete': return '#f44336';
        default: return '#757575';
    }
};

const DocumentAccessMap: React.FC = () => {
    const [accessData, setAccessData] = useState<DocumentAccess[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const { enqueueSnackbar } = useSnackbar();

    useEffect(() => {
        fetchAccessData();
    }, []);

    const fetchAccessData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Get all documents with their permissions
            const response = await http.get('/access/documents');
            const data = Array.isArray(response.data) ? response.data : [];
            setAccessData(data);
        } catch (err: any) {
            const status = err.response?.status;
            // Treat 404 as no explicit grants yet
            const errorMsg = status === 404
                ? null
                : (err.response?.data?.detail || 'Failed to load access data');
            setError(errorMsg);
            if (errorMsg) enqueueSnackbar(errorMsg, { variant: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const filteredData = accessData.filter(doc =>
        doc.document_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.owner_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.permissions.some(p => p.user_email.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    if (loading) {
        return (
            <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" minHeight="60vh">
                <CircularProgress size={60} />
                <Typography variant="h6" sx={{ mt: 2 }}>Loading access map...</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ p: 3, bgcolor: 'background.default', minHeight: '100vh' }}>
            {/* Header */}
            <Box sx={{ mb: 4 }}>
                <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                    <Stack direction="row" spacing={2} alignItems="center">
                        <Avatar sx={{ bgcolor: 'secondary.main', width: 56, height: 56 }}>
                            <ShareIcon fontSize="large" />
                        </Avatar>
                        <Box>
                            <Typography variant="h4" fontWeight="bold">
                                Document Access Map
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Visual overview of who has access to which documents
                            </Typography>
                        </Box>
                    </Stack>
                    <Button
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={fetchAccessData}
                        disabled={loading}
                    >
                        Refresh
                    </Button>
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
                placeholder="Search documents or users..."
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

            {/* Stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={4}>
                    <Card sx={{ bgcolor: alpha('#2196f3', 0.1) }}>
                        <CardContent>
                            <Stack direction="row" spacing={2} alignItems="center">
                                <Avatar sx={{ bgcolor: '#2196f3' }}>
                                    <DocumentIcon />
                                </Avatar>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {accessData.length}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Shared Documents
                                    </Typography>
                                </Box>
                            </Stack>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card sx={{ bgcolor: alpha('#4caf50', 0.1) }}>
                        <CardContent>
                            <Stack direction="row" spacing={2} alignItems="center">
                                <Avatar sx={{ bgcolor: '#4caf50' }}>
                                    <PersonIcon />
                                </Avatar>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {new Set(accessData.flatMap(d => d.permissions.map(p => p.user_id))).size}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Users with Access
                                    </Typography>
                                </Box>
                            </Stack>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card sx={{ bgcolor: alpha('#ff9800', 0.1) }}>
                        <CardContent>
                            <Stack direction="row" spacing={2} alignItems="center">
                                <Avatar sx={{ bgcolor: '#ff9800' }}>
                                    <ShareIcon />
                                </Avatar>
                                <Box>
                                    <Typography variant="h4" fontWeight="bold">
                                        {accessData.reduce((sum, d) => sum + d.permissions.length, 0)}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Total Access Grants
                                    </Typography>
                                </Box>
                            </Stack>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Access Map */}
            <Grid container spacing={2}>
                {filteredData.map((docAccess) => (
                    <Grid item xs={12} key={docAccess.document_id}>
                        <Card
                            sx={{
                                transition: 'all 0.3s',
                                '&:hover': {
                                    boxShadow: 4,
                                    transform: 'translateY(-2px)'
                                }
                            }}
                        >
                            <CardContent>
                                {/* Document Info */}
                                <Stack direction="row" spacing={2} alignItems="center" mb={2}>
                                    <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48 }}>
                                        <DocumentIcon />
                                    </Avatar>
                                    <Box flex={1}>
                                        <Typography variant="h6" fontWeight="bold">
                                            {docAccess.document_title}
                                        </Typography>
                                        <Stack direction="row" spacing={1} mt={0.5}>
                                            <Chip
                                                label={docAccess.document_type.toUpperCase()}
                                                size="small"
                                                variant="outlined"
                                            />
                                            <Chip
                                                label={`Owner: ${docAccess.owner_email}`}
                                                size="small"
                                                icon={<PersonIcon />}
                                            />
                                        </Stack>
                                    </Box>
                                    <Chip
                                        label={`${docAccess.permissions.length} user${docAccess.permissions.length !== 1 ? 's' : ''} have access`}
                                        color="primary"
                                    />
                                </Stack>

                                <Divider sx={{ mb: 2 }} />

                                {/* Access Grants */}
                                {docAccess.permissions.length > 0 ? (
                                    <Grid container spacing={1}>
                                        {docAccess.permissions.map((perm, idx) => (
                                            <Grid item xs={12} sm={6} md={4} key={idx}>
                                                <Paper
                                                    sx={{
                                                        p: 1.5,
                                                        border: `1px solid ${alpha(getRoleColor(perm.user_role), 0.3)}`,
                                                        bgcolor: alpha(getRoleColor(perm.user_role), 0.05)
                                                    }}
                                                >
                                                    <Stack direction="row" spacing={1} alignItems="center">
                                                        <Avatar
                                                            sx={{
                                                                bgcolor: getRoleColor(perm.user_role),
                                                                width: 32,
                                                                height: 32
                                                            }}
                                                        >
                                                            {getRoleIcon(perm.user_role)}
                                                        </Avatar>
                                                        <Box flex={1}>
                                                            <Typography variant="body2" fontWeight="bold">
                                                                {perm.user_name || perm.user_email}
                                                            </Typography>
                                                            <Stack direction="row" spacing={0.5} mt={0.5}>
                                                                <Chip
                                                                    label={perm.permission_type}
                                                                    size="small"
                                                                    sx={{
                                                                        bgcolor: getPermissionColor(perm.permission_type),
                                                                        color: 'white',
                                                                        height: 18,
                                                                        fontSize: '0.7rem'
                                                                    }}
                                                                />
                                                                {perm.expires_at && (
                                                                    <Tooltip title={`Expires: ${new Date(perm.expires_at).toLocaleString()}`}>
                                                                        <Chip
                                                                            icon={<CalendarIcon sx={{ fontSize: '0.8rem' }} />}
                                                                            label={new Date(perm.expires_at).toLocaleDateString()}
                                                                            size="small"
                                                                            color="warning"
                                                                            sx={{ height: 18, fontSize: '0.7rem' }}
                                                                        />
                                                                    </Tooltip>
                                                                )}
                                                            </Stack>
                                                        </Box>
                                                    </Stack>
                                                </Paper>
                                            </Grid>
                                        ))}
                                    </Grid>
                                ) : (
                                    <Alert severity="info">
                                        No additional access grants for this document
                                    </Alert>
                                )}
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {filteredData.length === 0 && !loading && (
                <Box textAlign="center" py={8}>
                    <ShareIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                        No shared documents found
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Documents with explicit access grants will appear here
                    </Typography>
                </Box>
            )}
        </Box>
    );
};

export default DocumentAccessMap;

