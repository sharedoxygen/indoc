import React from 'react'
import { Tabs, Tab, Box, Grid, Card, CardHeader, CardContent, Chip, Stack } from '@mui/material'
import { useLocation, useNavigate } from 'react-router-dom'

// Reuse existing pages as tab contents
import DocumentsPage from './DocumentsPage'
import UploadPage from './UploadPage'
import DocumentProcessingPage from './DocumentProcessingPage'
import DocumentOwnership from './DocumentOwnership'
import FolderCopyIcon from '@mui/icons-material/FolderCopy'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import TimelineIcon from '@mui/icons-material/Timeline'
import AccountTreeIcon from '@mui/icons-material/AccountTree'

function useTabQuery(defaultTab: string) {
    const location = useLocation()
    const navigate = useNavigate()
    const params = new URLSearchParams(location.search)
    const current = params.get('tab') || defaultTab
    const setTab = (tab: string) => {
        const next = new URLSearchParams(location.search)
        next.set('tab', tab)
        navigate({ pathname: location.pathname, search: next.toString() }, { replace: true })
    }
    return { current, setTab }
}

const DocumentsHubPage: React.FC = () => {
    const { current, setTab } = useTabQuery('browse')

    // Treat legacy 'processing' as 'work' (combined)
    const normalized = current === 'processing' ? 'work' : current
    const tabIndex = ['browse', 'work', 'ownership'].indexOf(normalized)

    return (
        <Box sx={{ width: '100%' }}>
            {/* Page hero */}
            <Box
                sx={{
                    mb: 2,
                    px: 2,
                    py: 2,
                    borderRadius: 3,
                    background: (theme) =>
                        theme.palette.mode === 'light'
                            ? 'linear-gradient(135deg, #EEF2FF 0%, #F7FAFF 100%)'
                            : 'linear-gradient(135deg, #0B1020 0%, #0F172A 100%)',
                    border: (theme) => `1px solid ${theme.palette.divider}`,
                }}
            >
                <Stack direction="row" alignItems="center" spacing={1}>
                    <Chip label="Documents Hub" color="primary" variant="outlined" />
                </Stack>
            </Box>

            <Tabs
                value={tabIndex === -1 ? 0 : tabIndex}
                onChange={(_, idx) => setTab(['browse', 'work', 'ownership'][idx])}
                sx={{ mb: 3 }}
                variant="scrollable"
            >
                <Tab icon={<FolderCopyIcon />} iconPosition="start" label="Browse" />
                <Tab icon={<CloudUploadIcon />} iconPosition="start" label="Upload & Processing" />
                <Tab icon={<AccountTreeIcon />} iconPosition="start" label="Ownership" />
            </Tabs>

            <Box role="tabpanel" hidden={normalized !== 'browse'}>
                {normalized === 'browse' && <DocumentsPage />}
            </Box>
            <Box role="tabpanel" hidden={normalized !== 'work'}>
                {normalized === 'work' && (
                    <Grid container spacing={2} alignItems="flex-start">
                        {/* Upload */}
                        <Grid item xs={12}>
                            <Card elevation={2} sx={{ borderRadius: 3 }}>
                                <CardHeader
                                    title="Upload Documents"
                                    subheader="Drag and drop, or pick a folder. Files begin processing immediately."
                                    avatar={<CloudUploadIcon color="primary" />}
                                />
                                <CardContent>
                                    <UploadPage />
                                </CardContent>
                            </Card>
                        </Grid>

                    </Grid>
                )}
            </Box>
            <Box role="tabpanel" hidden={normalized !== 'ownership'}>
                {normalized === 'ownership' && <DocumentOwnership />}
            </Box>
        </Box>
    )
}

export default DocumentsHubPage


