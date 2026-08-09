import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  Avatar,
  Stack,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Alert
} from '@mui/material'
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  PersonAdd as PersonAddIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material'
import { useGetUsersQuery } from '../store/api'

interface User {
  id: number
  email: string
  username: string
  full_name: string
  role: string
  is_active: boolean
  is_verified: boolean
}

const RoleManagementPage: React.FC = () => {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)
  const [roleFilter, setRoleFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  // API hooks
  const { data, error, refetch } = useGetUsersQuery({
    skip: page * rowsPerPage,
    limit: rowsPerPage
  })

  const users = data || []

  // Filter users based on search and role
  const filteredUsers = users.filter((user: User) => {
    const matchesSearch = !searchTerm ||
      user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.username.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesRole = !roleFilter || user.role === roleFilter
    return matchesSearch && matchesRole
  })

  const handleChangePage = (_event: unknown, newPage: number) => { setPage(newPage) }
  const handleChangeRowsPerPage = (_event: React.ChangeEvent<HTMLInputElement>) => { setRowsPerPage(25); setPage(0) }

  const getRoleColor = (role: string) => {
    const colors: Record<string, "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning"> = {
      'Admin': 'error',
      'Reviewer': 'warning',
      'Uploader': 'info',
      'Viewer': 'default',
      'Compliance': 'secondary'
    }
    return colors[role] || 'default'
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant='h4' sx={{ fontWeight: 700 }}>Users</Typography>
        <Stack direction='row' spacing={1}>
          <Button variant='outlined' startIcon={<RefreshIcon />} onClick={() => refetch()}>Refresh</Button>
          <Button variant='contained' startIcon={<PersonAddIcon />}>Invite</Button>
        </Stack>
      </Box>

      {error && <Alert severity='error' sx={{ mb: 2 }}>Failed to load users</Alert>}

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <Box sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField size='small' placeholder='Search users...' value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          <FormControl size='small' sx={{ minWidth: 140 }}>
            <InputLabel>Role</InputLabel>
            <Select value={roleFilter} label='Role' onChange={(e) => setRoleFilter(e.target.value)}>
              <MenuItem value=''>All</MenuItem>
              <MenuItem value='Admin'>Admin</MenuItem>
              <MenuItem value='Reviewer'>Reviewer</MenuItem>
              <MenuItem value='Uploader'>Uploader</MenuItem>
              <MenuItem value='Viewer'>Viewer</MenuItem>
              <MenuItem value='Compliance'>Compliance</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <TableContainer>
          <Table size='small'>
            <TableHead>
              <TableRow>
                <TableCell>User</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell align='right'>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredUsers.map((user: User) => (
                <TableRow key={user.id} hover>
                  <TableCell>
                    <Stack direction='row' spacing={1} alignItems='center'>
                      <Avatar>{user.full_name?.[0] || user.username?.[0]}</Avatar>
                      <Box>
                        <Typography variant='body2' sx={{ fontWeight: 600 }}>{user.full_name || user.username}</Typography>
                        <Typography variant='caption' color='text.secondary'>#{user.id}</Typography>
                      </Box>
                    </Stack>
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell><Chip label={user.role} color={getRoleColor(user.role)} size='small' /></TableCell>
                  <TableCell align='right'>
                    <IconButton size='small'><EditIcon /></IconButton>
                    <IconButton size='small' color='error'><DeleteIcon /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component='div'
          count={filteredUsers.length}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
    </Box>
  )
}

export default RoleManagementPage