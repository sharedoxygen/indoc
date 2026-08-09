import React from 'react'
import { useMemo } from 'react'
import { Box, Paper, Typography, Button, Chip, Stack, TextField, Divider, Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress } from '@mui/material'
import { ArrowBack, Delete } from '@mui/icons-material'
import { useNavigate, useParams } from 'react-router-dom'
import { useGetDocumentQuery, useUpdateDocumentMutation, useDeleteDocumentMutation, useScanVirusDocumentMutation } from '../store/api'
import { useSnackbar } from 'notistack'

const DocumentViewer: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams()
  const { enqueueSnackbar } = useSnackbar()

  const { data: doc, refetch } = useGetDocumentQuery(id as string, { skip: !id })
  const [updateDocument, { isLoading: isSaving }] = useUpdateDocumentMutation()
  const [deleteDocument, { isLoading: isDeleting }] = useDeleteDocumentMutation()
  const [scanVirus, { isLoading: isScanning }] = useScanVirusDocumentMutation()

  const [title, setTitle] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [tags, setTags] = React.useState('')
  const [confirmOpen, setConfirmOpen] = React.useState(false)
  const [imageDataUrl, setImageDataUrl] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (doc) {
      setTitle(doc.title || '')
      setDescription(doc.description || '')
      setTags((doc.tags || []).join(', '))
    }
  }, [doc])

  // Load image with authentication for preview
  React.useEffect(() => {
    const loadImage = async () => {
      if (!id || !doc) return
      
      // Only load if it's an image file
      const isImage = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(doc.file_type?.toLowerCase())
      if (!isImage) {
        setImageDataUrl(null)
        return
      }

      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`/api/v1/files/preview/${id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          console.error('Failed to load image:', response.statusText)
          return
        }

        const blob = await response.blob()
        const dataUrl = URL.createObjectURL(blob)
        setImageDataUrl(dataUrl)

        // Cleanup function to revoke object URL
        return () => {
          if (dataUrl) {
            URL.revokeObjectURL(dataUrl)
          }
        }
      } catch (error) {
        console.error('Error loading image:', error)
      }
    }

    loadImage()
  }, [id, doc])

  const handleSave = async () => {
    if (!id) return
    try {
      await updateDocument({ id, title, description, tags: tags.split(',').map((t) => t.trim()).filter(Boolean) }).unwrap()
      await refetch()
      enqueueSnackbar('Document updated successfully', { variant: 'success' })
    } catch (error: any) {
      console.error('Save failed:', error)
      enqueueSnackbar(error?.data?.detail || 'Failed to save document', { variant: 'error' })
    }
  }

  const handleDelete = async () => {
    if (!id) return
    await deleteDocument(id).unwrap()
    navigate('/search')
  }

  const handleVirusScan = async () => {
    if (!id) return
    try {
      await scanVirus(id).unwrap()
      await refetch()
    } catch (error) {
      console.error('Virus scan failed:', error)
    }
  }

  // Determine uniform preview height by file type
  const previewHeight = useMemo(() => {
    if (!doc) return 300
    if (doc.file_type === 'pdf') return 600
    if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(doc.file_type?.toLowerCase())) return 600
    return 300
  }, [doc])

  // Check if this is an image file
  const isImageFile = useMemo(() => {
    return ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(doc?.file_type?.toLowerCase())
  }, [doc?.file_type])
  // Show loading spinner while document is being fetched
  if (!doc) {
    return (
      <Box sx={{ textAlign: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }
  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/documents')}
        >
          Back
        </Button>
        <Button
          color="error"
          startIcon={<Delete />}
          onClick={() => setConfirmOpen(true)}
          disabled={isDeleting}
        >
          Delete
        </Button>
      </Stack>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {doc?.filename || 'Document'}
        </Typography>

        <Stack spacing={2} sx={{ mb: 2 }}>
          <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} fullWidth />
          <TextField label="Description" value={description} onChange={(e) => setDescription(e.target.value)} fullWidth multiline minRows={3} />
          <TextField label="Tags" value={tags} onChange={(e) => setTags(e.target.value)} helperText="Comma-separated" fullWidth />
          <Button variant="contained" onClick={handleSave} disabled={isSaving}>Save</Button>
        </Stack>

        <Divider sx={{ my: 2 }} />

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          <Chip label={`Type: ${doc?.file_type || '-'}`} size="small" />
          <Chip label={`Size: ${doc ? (doc.file_size / 1024).toFixed(1) + ' KB' : '-'}`} size="small" />
          <Chip label={`Status: ${doc?.status || '-'}`} size="small" color={doc?.status === 'failed' ? 'error' : 'default'} />
          <Chip
            label={`Virus: ${doc?.virus_scan_status || '-'}`}
            size="small"
            color={doc?.virus_scan_status === 'clean' ? 'success' : 'warning'}
          />
          {doc?.virus_scan_status === 'pending' && (
            <Button
              size="small"
              variant="outlined"
              onClick={handleVirusScan}
              disabled={isScanning}
              sx={{ fontSize: '0.75rem', py: 0.25 }}
            >
              {isScanning ? 'Scanning...' : 'Scan Now'}
            </Button>
          )}
        </Stack>

        <Box sx={{ mt: 2, p: 3, bgcolor: 'background.default', borderRadius: 1 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Preview</Typography>
          {/* File-type-specific preview */}
          {doc?.file_type === 'pdf' && (
            <Box sx={{ mb: 2, textAlign: 'center' }}>
              <object
                data={`/api/v1/files/download/${id}`}
                type="application/pdf"
                width="100%"
                height={`${previewHeight}px`}
              >
                <Typography variant="body2">PDF preview unavailable.</Typography>
              </object>
            </Box>
          )}
          {isImageFile && imageDataUrl && (
            <Box sx={{ mb: 2, textAlign: 'center' }}>
              <img
                src={imageDataUrl}
                alt="Preview"
                style={{ width: 'auto', maxWidth: '100%', height: `${previewHeight}px`, objectFit: 'contain', borderRadius: 4 }}
                onError={(e) => {
                  console.error('Image failed to load:', e);
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </Box>
          )}
          {isImageFile && !imageDataUrl && (
            <Box sx={{ mb: 2, textAlign: 'center', p: 4 }}>
              <CircularProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Loading image preview...
              </Typography>
            </Box>
          )}
          {/* Show preview based on file type and status */}
          {doc?.status === 'processing' ? (
            <Box sx={{ textAlign: 'center', p: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
              <CircularProgress size={20} />
              <Typography variant="body2">Processing preview...</Typography>
            </Box>
          ) : doc?.status === 'failed' ? (
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="body2" color="error">Preview unavailable (processing failed).</Typography>
              <Typography variant="body2" color="error" sx={{ mt: 1, fontSize: '0.75rem' }}>
                {doc.error_message || 'Unknown error'}
              </Typography>
            </Box>
          ) : doc?.status !== 'indexed' ? (
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="body2">Preview will be available once processing is complete.</Typography>
            </Box>
          ) : isImageFile ? (
            // For images, show a note since the image is displayed above in the file-type section
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="body2" color="success.main" sx={{ fontWeight: 500 }}>
                ✅ Image successfully processed and indexed
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontSize: '0.75rem' }}>
                Image preview shown above • No text content to extract
              </Typography>
            </Box>
          ) : doc.full_text ? (
            <Box sx={{ maxHeight: `${previewHeight}px`, overflow: 'auto', p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
              <Typography
                variant="body1"
                color="text.secondary"
                sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: 1.7, fontSize: '1rem' }}
              >
                {doc.full_text.length > 1000 ? `${doc.full_text.slice(0, 1000)}...` : doc.full_text}
              </Typography>
            </Box>
          ) : (
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2">No text content available for this file type.</Typography>
              <Button size="small" component="a" href={`/api/v1/files/download/${id}`} sx={{ mt: 1 }}>
                Download file
              </Button>
            </Box>
          )}
        </Box>
      </Paper>

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>Delete Document</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this document?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button color="error" onClick={handleDelete} disabled={isDeleting}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DocumentViewer