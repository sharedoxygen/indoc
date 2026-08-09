import React, { useState, useCallback } from 'react'
import { useSelector } from 'react-redux'
import type { RootState } from '../store'
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Chip,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
} from '@mui/material'
import {
  CloudUpload as UploadIcon,
  InsertDriveFile as FileIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Delete as DeleteIcon,
  Close as CloseIcon,
  ContentCopy as DuplicateIcon,
  Refresh as RetryIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { useDropzone } from 'react-dropzone'
import { useUploadDocumentMutation } from '../store/api'
import { useAppDispatch } from '../hooks/redux'
import { showNotification } from '../store/slices/uiSlice'
import { useSnackbar } from 'notistack'
import { useNavigate } from 'react-router-dom'
import { useProcessingWebSocket } from '../hooks/useProcessingWebSocket'
import { useDocumentProcessing } from '../hooks/useDocumentProcessing'
import DocumentProcessingProgress from '../components/DocumentProcessingProgress'

interface UploadFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'success' | 'error' | 'duplicate'
  progress: number
  error?: string
  response?: any
  relativePath?: string
  processingSteps?: {
    upload?: { status: string; progress?: number; message?: string };
    virus_scan?: { status: string; progress?: number; message?: string };
    text_extraction?: { status: string; progress?: number; message?: string };
    elasticsearch_indexing?: { status: string; progress?: number; message?: string };
    qdrant_vector_index?: { status: string; progress?: number; message?: string };
  };
}

const UploadPage: React.FC = () => {
  const dispatch = useAppDispatch()
  const { enqueueSnackbar } = useSnackbar()
  const navigate = useNavigate()
  const [uploadDocument] = useUploadDocumentMutation()
  const [files, setFiles] = useState<UploadFile[]>([])
  const [metadata, setMetadata] = useState({
    title: '',
    description: '',
    tags: '',
    documentSetId: '',
  })
  const [showResultModal, setShowResultModal] = useState(false)
  const [showProcessingModal, setShowProcessingModal] = useState(false)
  const [selectedResult, setSelectedResult] = useState<any>(null)
  const [showProcessingProgress, setShowProcessingProgress] = useState(false)

  // WebSocket for real-time processing updates
  const handleProcessingUpdate = useCallback((update: any) => {
    console.log('📨 Processing update received:', update);

    if (update.type === 'processing_update') {
      setFiles(prev => prev.map(f => {
        // Match by document UUID
        const matchesDoc = f.response?.document_uuid === update.documentId;
        if (matchesDoc) {
          console.log('✅ Updating file:', f.file.name, 'Step:', update.step, 'Status:', update.status);
        }
        if (!matchesDoc) return f;

        return {
          ...f,
          processingSteps: {
            ...f.processingSteps,
            [update.step]: {
              status: update.status,
              progress: update.progress,
              message: update.message,
              details: update.details,
              errorMessage: update.errorMessage,
            },
          },
        };
      }));
    }
  }, []);

  const { isConnected: wsConnected } = useProcessingWebSocket(handleProcessingUpdate);
  const { addDocumentToProcessing } = useDocumentProcessing();


  const onDrop = useCallback((acceptedFiles: any[]) => {
    const newFiles = acceptedFiles.map((file: any) => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending' as const,
      progress: 0,
      relativePath: (file as any).path || (file as any).webkitRelativePath || undefined,
    }))
    setFiles((prev) => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive, open: openFileDialog } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
      'text/html': ['.html'],
      'text/xml': ['.xml'],
      'application/json': ['.json'],
      'message/rfc822': ['.eml'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/tiff': ['.tiff'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
  })

  const handleFolderSelect = () => {
    // Programmatically open directory picker via a hidden input appended to DOM
    const input = document.createElement('input') as HTMLInputElement & { webkitdirectory?: boolean }
    input.type = 'file'
    input.style.display = 'none'
    input.multiple = true
    input.setAttribute('directory', '')
    input.setAttribute('webkitdirectory', '')
      ; (input as any).webkitdirectory = true
    document.body.appendChild(input)
    input.onchange = (e: any) => {
      try {
        const fileList: FileList = e.target.files
        const arr: any[] = []
        for (let i = 0; i < fileList.length; i += 1) {
          const f: any = fileList[i]
          arr.push(f)
        }
        onDrop(arr)
      } finally {
        // Clean up the temporary input
        document.body.removeChild(input)
      }
    }
    input.click()
  }

  const handleUpload = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending')

    // Initialize processing steps for all files before upload
    setFiles((prev) =>
      prev.map((f) =>
        pendingFiles.find(pf => pf.id === f.id)
          ? {
              ...f,
              status: 'uploading' as const,
              progress: 0,
              processingSteps: {
                upload: { status: 'processing', progress: 0, message: 'Starting upload...' },
                virusScan: { status: 'pending', progress: 0 },
                extraction: { status: 'pending', progress: 0 },
                elasticsearch: { status: 'pending', progress: 0 },
                qdrant: { status: 'pending', progress: 0 },
              }
            }
          : f
      )
    )

    // Show processing modal immediately when upload is submitted
    console.log('📊 Opening processing modal at upload start')
    setShowProcessingModal(true)

    // Check if this is a folder upload (files have relativePath)
    const isFolderUpload = pendingFiles.some(f => f.relativePath)

    if (isFolderUpload) {
      await handleBulkUpload(pendingFiles)
    } else {
      await handleSingleFileUpload(pendingFiles)
    }
  }

  const handleBulkUpload = async (pendingFiles: UploadFile[]) => {
    // Mark all as uploading
    setFiles((prev) =>
      prev.map((f) =>
        pendingFiles.find(pf => pf.id === f.id)
          ? { ...f, status: 'uploading', progress: 10 }
          : f
      )
    )

    try {
      const formData = new FormData()

      // Add all files to the form data
      pendingFiles.forEach((uploadFile) => {
        formData.append('files', uploadFile.file)
      })

      // Add folder structure mapping as JSON
      const folderMapping: Record<string, string> = {}
      pendingFiles.forEach((uploadFile, idx) => {
        if (uploadFile.relativePath) {
          folderMapping[uploadFile.file.name] = uploadFile.relativePath
        }
      })
      formData.append('folder_mapping', JSON.stringify(folderMapping))

      // Add metadata
      if (metadata.title) formData.append('title', metadata.title)
      if (metadata.description) formData.append('description', metadata.description)
      if (metadata.tags) formData.append('tags', metadata.tags)
      if (metadata.documentSetId) formData.append('document_set_id', metadata.documentSetId)

      console.log('🚀 Starting bulk upload for', pendingFiles.length, 'files')

      const token = localStorage.getItem('token')
      console.log('📡 Token available:', !!token)

      const response = await fetch('/api/v1/files/upload/bulk', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json'
        },
        body: formData
      })

      console.log('📊 Response status:', response.status, response.statusText)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Response error:', errorText)
        throw new Error(`Upload failed: ${response.statusText} - ${errorText}`)
      }

      const result = await response.json()
      console.log('✅ Bulk upload response:', result)

      // Update all files based on result
      setFiles((prev) => {
        const updated = prev.map((f) => {
          const uploadFile = pendingFiles.find(pf => pf.id === f.id)
          if (!uploadFile) return f

          const resultFile = result.files?.find((rf: any) =>
            rf.filename === uploadFile.file.name
          )

          if (resultFile) {
            if (resultFile.status === 'success') {
              const updatedFile = {
                ...f,
                status: 'success' as const,
                progress: 100,
                response: resultFile,
                processingSteps: {
                  upload: { status: 'completed', progress: 100, message: 'Uploaded' },
                  text_extraction: { status: 'processing', progress: 50, message: 'Extracting text...' },
                  elasticsearch_indexing: { status: 'pending', progress: 0 },
                  qdrant_vector_index: { status: 'pending', progress: 0 },
                }
              };
              console.log('✅ Setting processingSteps for:', f.file.name, updatedFile.processingSteps);
              return updatedFile;
            } else if (resultFile.status === 'duplicate') {
              return {
                ...f,
                status: 'duplicate' as const,
                progress: 100,
                error: 'Already in system',
                response: resultFile
              }
            } else if (resultFile.status === 'failed') {
              return {
                ...f,
                status: 'error' as const,
                progress: 0,
                error: resultFile.error || 'Upload failed',
                response: resultFile
              }
            }
          }

          return { ...f, status: 'success' as const, progress: 100 }
        });

        console.log('📦 Updated files state:', updated.map(f => ({
          name: f.file.name,
          status: f.status,
          hasProcessingSteps: !!f.processingSteps
        })));

        return updated;
      })

      // Show detailed feedback
      const { successful_uploads = 0, skipped_duplicates = 0, failed_uploads = 0 } = result

      if (successful_uploads > 0) {
        enqueueSnackbar(
          `Successfully uploaded ${successful_uploads} file${successful_uploads !== 1 ? 's' : ''}`,
          { variant: 'success', autoHideDuration: 3000 }
        )
      }

      if (skipped_duplicates > 0) {
        enqueueSnackbar(
          `Skipped ${skipped_duplicates} duplicate file${skipped_duplicates !== 1 ? 's' : ''}`,
          { variant: 'info', autoHideDuration: 4000 }
        )
      }

      if (failed_uploads > 0) {
        // Show detailed error information
        const errorDetails = result.errors?.map((err: any) =>
          `${err.filename}: ${err.error}`
        ).join('\n') || 'Unknown errors'

        console.error('Upload failures:', result.errors)

        enqueueSnackbar(
          `Failed to upload ${failed_uploads} file${failed_uploads !== 1 ? 's' : ''}. Review details below and use Retry button.`,
          { variant: 'error', autoHideDuration: 8000 }
        )

        // Log detailed errors to console for debugging
        console.error('❌ Upload Failures:\n', errorDetails)
      }

      // Show success message with link to documents
      if (successful_uploads > 0) {
        enqueueSnackbar(
          `✅ ${successful_uploads} file${successful_uploads !== 1 ? 's' : ''} uploaded successfully. Click Documents to view them.`,
          {
            variant: 'success',
            autoHideDuration: 10000,
            action: (key) => (
              <Button size="small" color="inherit" onClick={() => navigate('/documents')}>
                View Documents
              </Button>
            )
          }
        )
      }

    } catch (error: any) {
      console.error('❌ Bulk upload error:', error)

      // Mark all as failed
      setFiles((prev) =>
        prev.map((f) =>
          pendingFiles.find(pf => pf.id === f.id)
            ? { ...f, status: 'error', progress: 0, error: error.message || 'Bulk upload failed' }
            : f
        )
      )

      enqueueSnackbar(`Bulk upload failed: ${error.message}`, {
        variant: 'error',
        autoHideDuration: 6000
      })
    }
  }

  const handleSingleFileUpload = async (pendingFiles: UploadFile[]) => {
    for (const uploadFile of pendingFiles) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: 'uploading', progress: 50 }
            : f
        )
      )

      const formData = new FormData()
      formData.append('file', uploadFile.file)
      if (metadata.title) formData.append('title', metadata.title)
      if (metadata.description) formData.append('description', metadata.description)
      if (metadata.tags) formData.append('tags', metadata.tags)
      if (metadata.documentSetId) formData.append('document_set_id', metadata.documentSetId)
      if (uploadFile.relativePath) formData.append('folder_path', uploadFile.relativePath)

      try {
        console.log('🚀 Starting upload for:', uploadFile.file.name)

        // Use Vite proxy for consistent CORS handling
        const token = localStorage.getItem('token')
        const directResponse = await fetch('/api/v1/files/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json'
          },
          body: formData
        })

        if (!directResponse.ok) {
          const errorText = await directResponse.text()
          console.error('❌ Single upload error:', errorText)
          throw new Error(`Upload failed: ${directResponse.statusText} - ${errorText}`)
        }

        const response = await directResponse.json()
        console.log('✅ Upload response:', response)

        // Handle duplicate file response explicitly
        if (response?.error === 'Duplicate file' && response?.existing_document) {
          const existing = response.existing_document

          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id
                ? {
                  ...f,
                  status: 'error',
                  progress: 0,
                  error: `Duplicate: already exists as "${existing.filename}" (${new Date(existing.uploaded_at).toLocaleString()})`,
                }
                : f
            )
          )

          enqueueSnackbar(`Duplicate file: opening existing document`, {
            variant: 'warning',
            autoHideDuration: 4000,
          })

          // Navigate directly to the existing document viewer
          navigate(`/document/${existing.uuid}`)
          continue
        }

        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: 'success' as const,
                  progress: 100,
                  response,
                  processingSteps: {
                    upload: { status: 'completed', progress: 100, message: 'Upload complete' },
                    virusScan: { status: 'processing', progress: 0, message: 'Scanning for viruses...' },
                    extraction: { status: 'pending', progress: 0 },
                    elasticsearch: { status: 'pending', progress: 0 },
                    qdrant: { status: 'pending', progress: 0 },
                  }
                }
              : f
          )
        )

        // Add document to processing pipeline visualization
        if (response.uuid) {
          addDocumentToProcessing(
            response.uuid,
            uploadFile.file.name,
            uploadFile.file.type || 'unknown',
            uploadFile.file.size
          )
        }

        enqueueSnackbar(`${uploadFile.file.name} uploaded successfully - processing started`, {
          variant: 'success',
          autoHideDuration: 3000
        })

        // Modal already opened at start of upload
        console.log('✅ Upload complete, backend processing will update via WebSocket')
      } catch (error: any) {
        console.error('❌ Upload error:', error)
        // Extract detailed error information from backend
        const errorData = error.data || {}
        const errorMessage = errorData.message || errorData.detail || 'Upload failed'
        const errorDetails = errorData.details || ''
        const fullError = errorDetails ? `${errorMessage}: ${errorDetails}` : errorMessage

        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? {
                ...f,
                status: 'error',
                progress: 0,
                error: fullError,
              }
              : f
          )
        )

        enqueueSnackbar(`Failed to upload ${uploadFile.file.name}: ${errorMessage}`, {
          variant: 'error',
          autoHideDuration: 6000,
          ...(errorDetails && {
            title: 'Error Details',
            description: errorDetails
          })
        })
      }
    }
  }

  const handleRemoveFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const handleViewResult = (result: any) => {
    setSelectedResult(result)
    setShowResultModal(true)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <SuccessIcon color="success" />
      case 'duplicate':
        return <DuplicateIcon color="warning" />
      case 'error':
        return <ErrorIcon color="error" />
      case 'uploading':
        return <FileIcon color="primary" />
      default:
        return <FileIcon />
    }
  }

  const getStatusChip = (uploadFile: UploadFile) => {
    if (uploadFile.status === 'success') {
      return <Chip label="Uploaded" color="success" size="small" sx={{ fontWeight: 600 }} />
    } else if (uploadFile.status === 'duplicate') {
      return <Chip label="Duplicate" color="warning" size="small" sx={{ fontWeight: 600 }} />
    } else if (uploadFile.status === 'error') {
      return <Chip label="Failed" color="error" size="small" sx={{ fontWeight: 600 }} />
    } else if (uploadFile.status === 'uploading') {
      return <Chip label="Processing..." color="primary" size="small" sx={{ fontWeight: 600 }} />
    }
    return <Chip label="Pending" variant="outlined" size="small" />
  }

  const handleRetryFile = async (fileId: string) => {
    const fileToRetry = files.find(f => f.id === fileId)
    if (!fileToRetry) return

    // Reset status to pending
    setFiles(prev => prev.map(f =>
      f.id === fileId ? { ...f, status: 'pending', error: undefined, response: undefined } : f
    ))

    enqueueSnackbar(`Retrying ${fileToRetry.file.name}...`, { variant: 'info' })
  }

  const hasFiles = files.length > 0
  const hasPendingFiles = files.some((f) => f.status === 'pending')
  const isUploading = files.some((f) => f.status === 'uploading')

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Upload Documents
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Box
              {...getRootProps()}
              sx={{
                border: '2px dashed',
                borderColor: isDragActive ? 'primary.main' : 'grey.300',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
                cursor: 'pointer',
                bgcolor: isDragActive ? 'action.hover' : 'background.paper',
                transition: 'all 0.3s',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
              }}
            >
              <input {...getInputProps()} />
              <UploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 3 }} />
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
                {isDragActive ? 'Drop your files here!' : 'Upload Documents'}
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 3, maxWidth: 500, mx: 'auto', lineHeight: 1.6 }}>
                {isDragActive
                  ? 'Release to upload your files and folders'
                  : 'Drag & drop files or folders here, or choose what to upload below'
                }
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3, mb: 3 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={(e) => {
                    e.stopPropagation();
                    openFileDialog();
                  }}
                  sx={{
                    borderRadius: 3,
                    textTransform: 'none',
                    px: 4,
                    py: 1.5,
                    fontWeight: 600
                  }}
                >
                  Choose Files
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleFolderSelect();
                  }}
                  sx={{
                    borderRadius: 3,
                    textTransform: 'none',
                    px: 4,
                    py: 1.5,
                    fontWeight: 600
                  }}
                >
                  Choose Folder
                </Button>
              </Box>

              <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 2, mt: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Supported: PDF, DOCX, XLSX, PPTX, TXT, HTML, XML, JSON, EML, Images
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Maximum: 100MB per file • Folders preserve structure automatically
                </Typography>
              </Box>
            </Box>

            {hasFiles && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Files to Upload
                </Typography>

                {/* Show Processing Progress for successfully uploaded files */}
                {files
                  .filter(f => {
                    const shouldShow = f.status === 'success' && f.processingSteps;
                    if (shouldShow) {
                      console.log('📊 Showing processing progress for:', f.file.name);
                    }
                    return shouldShow;
                  })
                  .map(uploadFile => (
                    <Box key={uploadFile.id} sx={{ mb: 2 }}>
                      <DocumentProcessingProgress
                        filename={uploadFile.file.name}
                        steps={uploadFile.processingSteps || {}}
                        overallProgress={uploadFile.progress}
                      />
                    </Box>
                  ))
                }

                <List>
                  {files.map((uploadFile) => (
                    <ListItem
                      key={uploadFile.id}
                      sx={{
                        border: '1px solid',
                        borderColor: uploadFile.status === 'error' ? 'error.main' :
                          uploadFile.status === 'duplicate' ? 'warning.main' :
                            uploadFile.status === 'success' ? 'success.main' : 'divider',
                        borderRadius: 2,
                        mb: 1,
                        bgcolor: uploadFile.status === 'error' ? 'error.light' :
                          uploadFile.status === 'duplicate' ? 'warning.light' :
                            'background.paper',
                        opacity: uploadFile.status === 'duplicate' ? 0.7 : 1
                      }}
                      secondaryAction={
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          {getStatusChip(uploadFile)}
                          {uploadFile.status === 'pending' && (
                            <IconButton
                              edge="end"
                              onClick={() => handleRemoveFile(uploadFile.id)}
                              size="small"
                            >
                              <DeleteIcon />
                            </IconButton>
                          )}
                          {uploadFile.status === 'error' && (
                            <IconButton
                              edge="end"
                              onClick={() => handleRetryFile(uploadFile.id)}
                              size="small"
                              color="primary"
                              title="Retry upload"
                            >
                              <RetryIcon />
                            </IconButton>
                          )}
                          {(uploadFile.status === 'success' || uploadFile.status === 'duplicate') && uploadFile.response && (
                            <IconButton
                              edge="end"
                              onClick={() => handleViewResult(uploadFile.response)}
                              size="small"
                              title="View details"
                            >
                              <InfoIcon />
                            </IconButton>
                          )}
                        </Box>
                      }
                    >
                      <ListItemIcon>{getStatusIcon(uploadFile.status)}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {uploadFile.relativePath || uploadFile.file.name}
                            </Typography>
                          </Box>
                        }
                        secondaryTypographyProps={{ component: 'div' }}
                        secondary={
                          uploadFile.status === 'uploading' ? (
                            <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LinearProgress variant="determinate" value={uploadFile.progress} sx={{ flex: 1 }} />
                              <Typography variant="caption">{Math.round(uploadFile.progress)}%</Typography>
                            </Box>
                          ) : uploadFile.error ? (
                            <Box sx={{ mt: 0.5 }}>
                              <Typography color="error" variant="caption" sx={{ fontWeight: 500 }}>
                                {uploadFile.error}
                              </Typography>
                              {uploadFile.response?.error_details && (
                                <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }}>
                                  {uploadFile.response.error_details}
                                </Typography>
                              )}
                            </Box>
                          ) : uploadFile.status === 'duplicate' ? (
                            <Typography variant="caption" sx={{ color: 'warning.dark', fontWeight: 500 }}>
                              Already in system
                            </Typography>
                          ) : (
                            <Typography variant="caption" color="text.secondary">
                              {`${(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB`}
                            </Typography>
                          )
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Document Metadata
            </Typography>
            <TextField
              fullWidth
              label="Title"
              value={metadata.title}
              onChange={(e) => setMetadata({ ...metadata, title: e.target.value })}
              margin="normal"
              helperText="Optional: Custom title for the document"
            />
            <TextField
              fullWidth
              label="Description"
              value={metadata.description}
              onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
              margin="normal"
              multiline
              rows={3}
              helperText="Optional: Brief description"
            />
            <TextField
              fullWidth
              label="Tags"
              value={metadata.tags}
              onChange={(e) => setMetadata({ ...metadata, tags: e.target.value })}
              margin="normal"
              helperText="Comma-separated tags"
            />
            {metadata.tags && (
              <Box sx={{ mt: 1 }}>
                {metadata.tags.split(',').map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag.trim()}
                    size="small"
                    sx={{ mr: 0.5, mb: 0.5 }}
                  />
                ))}
              </Box>
            )}
            <TextField
              fullWidth
              label="Document Set ID (Optional)"
              value={metadata.documentSetId}
              onChange={(e) => setMetadata({ ...metadata, documentSetId: e.target.value })}
              margin="normal"
              helperText="Group related documents together (e.g., 'ZX10R-2024' or 'project-alpha')"
              placeholder="my-document-set"
            />
          </Paper>

          {hasFiles && (
            <Box sx={{ mt: 3 }}>
              <Button
                variant="contained"
                fullWidth
                size="large"
                onClick={handleUpload}
                disabled={isUploading}
                startIcon={<UploadIcon />}
                sx={{
                  borderRadius: 3,
                  py: 2,
                  fontWeight: 600,
                  textTransform: 'none',
                  fontSize: '1.1rem'
                }}
              >
                {isUploading ? 'Uploading...' : `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`}
              </Button>
            </Box>
          )}

          <Alert severity="info" sx={{ mt: 3 }}>
            <Typography variant="body2">
              All uploaded documents will be:
            </Typography>
            <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
              <li>Scanned for viruses</li>
              <li>Processed for text extraction</li>
              <li>Indexed for search</li>
              <li>Encrypted if containing sensitive data</li>
            </ul>
          </Alert>
        </Grid>
      </Grid>


      {/* Result Modal */}
      <Dialog
        open={showResultModal}
        onClose={() => setShowResultModal(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Upload Successful
          <IconButton
            onClick={() => setShowResultModal(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedResult && (
            <Box>
              <Typography variant="body1" gutterBottom>
                <strong>Document ID:</strong> {selectedResult.uuid}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="body1" component="span">
                  <strong>Status:</strong>
                </Typography>
                <Chip
                  label={selectedResult.status}
                  color={selectedResult.status === 'pending' ? 'warning' : 'success'}
                  size="small"
                />
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="body1" component="span">
                  <strong>Virus Scan:</strong>
                </Typography>
                <Chip
                  label={selectedResult.virus_scan_status}
                  color={selectedResult.virus_scan_status === 'clean' ? 'success' : 'error'}
                  size="small"
                />
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowResultModal(false)}>Close</Button>
          <Button
            variant="outlined"
            onClick={() => {
              setShowProcessingModal(true)
            }}
          >
            View Processing
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              if (selectedResult) {
                navigate(`/document/${selectedResult.uuid}`)
              }
            }}
          >
            View Document
          </Button>
        </DialogActions>
      </Dialog>

      {/* Processing Pipeline Modal */}
      <Dialog
        open={showProcessingModal}
        onClose={() => setShowProcessingModal(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: {
            minHeight: '70vh',
            maxHeight: '85vh',
          }
        }}
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            📊 Document Processing Pipeline
          </Typography>
          <IconButton onClick={() => setShowProcessingModal(false)} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ minHeight: '400px' }}>
            {files.filter(f => f.status !== 'error' && f.status !== 'duplicate').length > 0 ? (
              files
                .filter(f => f.status !== 'error' && f.status !== 'duplicate')
                .map((file) => (
                  <Box key={file.id} sx={{ mb: 3 }}>
                    <DocumentProcessingProgress
                      filename={file.file.name}
                      steps={file.processingSteps || {
                        upload: { status: 'completed', progress: 100 },
                        virusScan: { status: 'pending', progress: 0 },
                        extraction: { status: 'pending', progress: 0 },
                        elasticsearch: { status: 'pending', progress: 0 },
                        qdrant: { status: 'pending', progress: 0 },
                      }}
                      overallProgress={file.progress}
                    />
                  </Box>
                ))
            ) : (
              <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '400px',
                textAlign: 'center'
              }}>
                <InfoIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No Active Processing
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Upload some files to see the real-time processing pipeline
                </Typography>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowProcessingModal(false)}>Close</Button>
          <Button
            variant="outlined"
            onClick={() => {
              setShowProcessingModal(false)
              navigate('/document-processing')
            }}
          >
            Go to Full Pipeline View
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default UploadPage