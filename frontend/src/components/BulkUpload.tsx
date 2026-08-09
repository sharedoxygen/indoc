import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Alert,
  IconButton,
  Collapse
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Folder as FolderIcon,
  InsertDriveFile as FileIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useWebSocket } from '../hooks/useWebSocket';

interface UploadFile {
  filename: string;
  path?: string;
  size?: number;
  status: 'pending' | 'uploading' | 'success' | 'failed' | 'duplicate';
  error?: string;
}

interface UploadProgress {
  message: string;
  progress: number;
}

export const BulkUpload: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [showResults, setShowResults] = useState(true);
  const [preserveStructure] = useState(true);

  const { lastMessage } = useWebSocket(
    isUploading ? '/api/v1/files/ws/upload' : null
  );

  // Handle WebSocket messages for upload progress
  React.useEffect(() => {
    if (lastMessage) {
      const data = JSON.parse(lastMessage.data);

      if (data.type === 'upload_progress') {
        setUploadProgress({
          message: data.message,
          progress: data.progress
        });
      }
    }
  }, [lastMessage]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    noClick: false
  });

  const handleUpload = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadResults([]);
    setUploadProgress({ message: 'Preparing upload...', progress: 0 });

    try {
      // Check if any file is a ZIP
      const zipFiles = files.filter(f => f.name.toLowerCase().endsWith('.zip'));
      const regularFiles = files.filter(f => !f.name.toLowerCase().endsWith('.zip'));

      // Handle ZIP files
      for (const zipFile of zipFiles) {
        const formData = new FormData();
        formData.append('file', zipFile);
        formData.append('preserve_structure', preserveStructure.toString());

        const response = await fetch('/api/v1/files/upload/zip', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });

        if (response.ok) {
          const result = await response.json();
          setUploadResults(prev => [...prev, ...result.files]);
        }
      }

      // Handle regular files
      if (regularFiles.length > 0) {
        const formData = new FormData();
        regularFiles.forEach(file => {
          formData.append('files', file);
        });

        const response = await fetch('/api/v1/files/upload/bulk', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });

        if (response.ok) {
          const result = await response.json();
          setUploadResults(prev => [...prev, ...result.files]);
        }
      }

      setUploadProgress({ message: 'Upload complete!', progress: 100 });
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadProgress({ message: 'Upload failed', progress: 0 });
    } finally {
      setIsUploading(false);
      setFiles([]);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'duplicate':
        return <WarningIcon color="warning" />;
      default:
        return <FileIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'duplicate':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Bulk File Upload
        </Typography>

        {/* Dropzone */}
        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.400',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            cursor: 'pointer',
            bgcolor: isDragActive ? 'action.hover' : 'background.paper',
            transition: 'all 0.3s',
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'action.hover'
            }
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive ? 'Drop files here' : 'Drag & drop files or folders'}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            or click to browse (supports ZIP archives)
          </Typography>
        </Box>

        {/* Selected Files */}
        {files.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Selected Files ({files.length})
            </Typography>
            <List dense>
              {files.slice(0, 5).map((file, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    {file.name.toLowerCase().endsWith('.zip') ? <FolderIcon /> : <FileIcon />}
                  </ListItemIcon>
                  <ListItemText
                    primary={file.name}
                    secondary={formatFileSize(file.size)}
                  />
                </ListItem>
              ))}
              {files.length > 5 && (
                <ListItem>
                  <ListItemText
                    primary={`... and ${files.length - 5} more files`}
                    sx={{ fontStyle: 'italic' }}
                  />
                </ListItem>
              )}
            </List>

            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={isUploading}
              startIcon={<CloudUploadIcon />}
              fullWidth
              sx={{ mt: 2 }}
            >
              {isUploading ? 'Uploading...' : `Upload ${files.length} Files`}
            </Button>
          </Box>
        )}

        {/* Upload Progress */}
        {uploadProgress && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="body2" gutterBottom>
              {uploadProgress.message}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={uploadProgress.progress}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
        )}

        {/* Upload Results */}
        {uploadResults.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Upload Results
              </Typography>
              <IconButton onClick={() => setShowResults(!showResults)}>
                {showResults ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>

            <Collapse in={showResults}>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Successfully uploaded: {uploadResults.filter(f => f.status === 'success').length} |
                  Duplicates: {uploadResults.filter(f => f.status === 'duplicate').length} |
                  Failed: {uploadResults.filter(f => f.status === 'failed').length}
                </Typography>
              </Alert>

              <List dense>
                {uploadResults.map((file, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {getStatusIcon(file.status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={file.filename}
                      secondary={file.error || file.path}
                    />
                    <Chip
                      label={file.status}
                      size="small"
                      color={getStatusColor(file.status) as any}
                    />
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </Box>
        )}
      </Paper>
    </Box>
  );
};