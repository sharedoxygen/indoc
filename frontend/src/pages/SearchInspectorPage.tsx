import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Button,
  TextField,
  InputAdornment
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Storage as ElasticsearchIcon,
  Cloud as QdrantIcon,
  TableChart as PostgresIcon
} from '@mui/icons-material';
import { http } from '../services/http';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const SearchInspectorPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Stats
  const [stats, setStats] = useState({
    postgresql: 0,
    elasticsearch: 0,
    qdrant: 0
  });

  // Data
  const [elasticsearchDocs, setElasticsearchDocs] = useState<any[]>([]);
  const [qdrantVectors, setQdrantVectors] = useState<any[]>([]);
  const [postgresqlDocs, setPostgresqlDocs] = useState<any[]>([]);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadStats(),
        loadElasticsearchData(),
        loadQdrantData(),
        loadPostgresData()
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadElasticsearchData = async () => {
    try {
      const response = await http.get('/search-inspector/elasticsearch');
      setElasticsearchDocs(response.data || []);
    } catch (error) {
      console.error('Elasticsearch error:', error);
    }
  };

  const loadQdrantData = async () => {
    try {
      const response = await http.get('/search-inspector/qdrant');
      setQdrantVectors(response.data || []);
    } catch (error) {
      console.error('Qdrant error:', error);
    }
  };

  const loadPostgresData = async () => {
    try {
      const response = await http.get('/search-inspector/postgresql');
      setPostgresqlDocs(response.data || []);
    } catch (error) {
      console.error('PostgreSQL error:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await http.get('/search-inspector/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Stats error:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      // For now, just reload all data (could add search endpoint later)
      await loadAllData();
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          🔍 Search Inspector
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadAllData}
          disabled={loading}
        >
          Refresh All
        </Button>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <PostgresIcon sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h6">PostgreSQL</Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700 }}>
                {stats.postgresql}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Documents
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ElasticsearchIcon sx={{ mr: 1, color: 'warning.main' }} />
                <Typography variant="h6">Elasticsearch</Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700 }}>
                {stats.elasticsearch}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Indexed Documents
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <QdrantIcon sx={{ mr: 1, color: 'success.main' }} />
                <Typography variant="h6">Qdrant</Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700 }}>
                {stats.qdrant}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Vector Points
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search Bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search across all systems..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <Button onClick={handleSearch} disabled={loading}>
                  Search
                </Button>
              </InputAdornment>
            )
          }}
        />
      </Paper>

      {/* Tabs */}
      <Paper>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label={`PostgreSQL (${stats.postgresql})`} />
          <Tab label={`Elasticsearch (${stats.elasticsearch})`} />
          <Tab label={`Qdrant (${stats.qdrant})`} />
        </Tabs>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* PostgreSQL Tab */}
        <TabPanel value={tabValue} index={0}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Filename</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>ES</TableCell>
                  <TableCell>Qdrant</TableCell>
                  <TableCell>Uploaded By</TableCell>
                  <TableCell>Processing Time</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {postgresqlDocs.map((doc: any) => (
                  <TableRow key={doc.uuid}>
                    <TableCell>
                      <Tooltip title={doc.uuid}>
                        <Typography variant="body2">{doc.filename}</Typography>
                      </Tooltip>
                      {doc.error_message && (
                        <Tooltip title={doc.error_message}>
                          <Chip label="Error" size="small" color="error" sx={{ mt: 0.5 }} />
                        </Tooltip>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip label={doc.file_type || 'unknown'} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={doc.status}
                        size="small"
                        color={doc.status === 'indexed' ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>
                      {doc.has_elasticsearch_id ? (
                        <Chip label="✓" size="small" color="success" />
                      ) : (
                        <Chip label="✗" size="small" color="error" />
                      )}
                    </TableCell>
                    <TableCell>
                      {doc.has_qdrant_id ? (
                        <Chip label="✓" size="small" color="success" />
                      ) : (
                        <Chip label="✗" size="small" color="error" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{doc.uploaded_by || 'N/A'}</Typography>
                    </TableCell>
                    <TableCell>
                      {doc.processing_time_ms ? `${doc.processing_time_ms}ms` : 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {new Date(doc.created_at).toLocaleString()}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Elasticsearch Tab */}
        <TabPanel value={tabValue} index={1}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Filename</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Tags</TableCell>
                  <TableCell>Uploaded By</TableCell>
                  <TableCell>Content Preview</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {elasticsearchDocs.map((doc: any) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <Tooltip title={doc.id}>
                        <Typography variant="body2">{doc.filename || 'N/A'}</Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Chip label={doc.file_type || 'unknown'} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{doc.title || doc.filename || 'N/A'}</Typography>
                    </TableCell>
                    <TableCell>
                      {doc.tags && doc.tags.length > 0 ? (
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {doc.tags.slice(0, 3).map((tag: string) => (
                            <Chip key={tag} label={tag} size="small" variant="outlined" />
                          ))}
                          {doc.tags.length > 3 && (
                            <Chip label={`+${doc.tags.length - 3}`} size="small" />
                          )}
                        </Box>
                      ) : (
                        <Typography variant="caption" color="text.secondary">No tags</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{doc.uploaded_by || 'N/A'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={doc.content_preview || ''}>
                        <Typography variant="caption" noWrap sx={{ maxWidth: 250, display: 'block' }}>
                          {doc.content_preview || 'N/A'}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {doc.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Qdrant Tab */}
        <TabPanel value={tabValue} index={2}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Filename</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Chunk</TableCell>
                  <TableCell>Vector Dim</TableCell>
                  <TableCell>Content Preview</TableCell>
                  <TableCell>Document ID</TableCell>
                  <TableCell>Indexed At</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {qdrantVectors.map((point: any) => (
                  <TableRow key={point.id}>
                    <TableCell>
                      <Typography variant="body2">{point.filename || 'N/A'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={point.file_type || 'unknown'} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip label={`#${point.chunk_index || 0}`} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Embedding vector dimension">
                        <Chip label={point.vector_dimension || 384} size="small" color="info" />
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={point.content_preview || ''}>
                        <Typography variant="caption" noWrap sx={{ maxWidth: 250, display: 'block' }}>
                          {point.content_preview || 'N/A'}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={point.document_id}>
                        <Typography variant="caption" noWrap sx={{ maxWidth: 120, display: 'block' }}>
                          {point.document_id?.substring(0, 8)}...
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {point.indexed_at ? new Date(point.indexed_at).toLocaleString() : 'N/A'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>
      </Paper>

      {/* Summary Alert */}
      {stats.postgresql !== stats.elasticsearch || stats.postgresql !== stats.qdrant ? (
        <Alert severity="warning" sx={{ mt: 3 }}>
          <Typography variant="body2">
            <strong>Data Mismatch Detected!</strong><br />
            PostgreSQL: {stats.postgresql} | Elasticsearch: {stats.elasticsearch} | Qdrant: {stats.qdrant}
            <br />
            Some documents may not be fully indexed.
          </Typography>
        </Alert>
      ) : stats.postgresql > 0 && (
        <Alert severity="success" sx={{ mt: 3 }}>
          <Typography variant="body2">
            <strong>All systems in sync!</strong> {stats.postgresql} documents indexed across all systems.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default SearchInspectorPage;

