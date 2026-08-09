import React from 'react'
import { Box, Paper, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Chip, Stack, Button, Menu, MenuItem } from '@mui/material'
import { useGetAuditLogsQuery, useExportAuditLogsMutation } from '../store/api'

const AuditTrailPage: React.FC = () => {
  const [page, setPage] = React.useState(0)
  const [rowsPerPage, setRowsPerPage] = React.useState(25)
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)

  const { data } = useGetAuditLogsQuery({ skip: page * rowsPerPage, limit: rowsPerPage })
  const rows = data?.logs || []
  const total = data?.total || 0

  const [exportAuditLogs] = useExportAuditLogsMutation()

  const handleExport = async (format: 'csv' | 'json') => {
    setAnchorEl(null)
    try {
      // Backend returns status json; we simulate a client-side download request by refetching logs and packaging here
      const payload = { format }
      await exportAuditLogs(payload).unwrap()
      // Quick client-side export using current page logs
      const blob = new Blob([
        format === 'json' ? JSON.stringify(rows, null, 2) : ['id,user_email,action,resource_type,resource_id,created_at', ...rows.map((r: any) => `${r.id},${r.user_email},${r.action},${r.resource_type},${r.resource_id || ''},${r.created_at || ''}`)].join('\n')
      ], { type: format === 'json' ? 'application/json' : 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_page${page + 1}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // noop for now
    }
  }

  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h4">Audit Trail</Typography>
        <div>
          <Button variant="outlined" onClick={(e) => setAnchorEl(e.currentTarget)}>Export</Button>
          <Menu anchorEl={anchorEl} open={open} onClose={() => setAnchorEl(null)}>
            <MenuItem onClick={() => handleExport('csv')}>CSV</MenuItem>
            <MenuItem onClick={() => handleExport('json')}>JSON</MenuItem>
          </Menu>
        </div>
      </Stack>
      <Paper sx={{ p: 2 }}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>User</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Resource</TableCell>
                <TableCell>Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((log: any) => (
                <TableRow key={log.id} hover>
                  <TableCell>{log.created_at}</TableCell>
                  <TableCell>{log.user_email}</TableCell>
                  <TableCell>
                    <Chip label={log.user_role} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip label={log.action} size="small" color={log.action === 'delete' ? 'error' : log.action === 'update' ? 'warning' : 'default'} />
                  </TableCell>
                  <TableCell>{`${log.resource_type}${log.resource_id ? `:${log.resource_id}` : ''}`}</TableCell>
                  <TableCell>{log.details ? JSON.stringify(log.details) : '-'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0) }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Paper>
    </Box>
  )
}

export default AuditTrailPage