import React from 'react'
import { Outlet } from 'react-router-dom'
import { Box, Container, Paper } from '@mui/material'
import { useThemeMode } from '../contexts/ThemeContext' // Import useThemeMode

const AuthLayout: React.FC = () => {
  const { mode } = useThemeMode(); // Get the current theme mode

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background:
          mode === 'dark'
            ? 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)' // Dark gradient
            : 'linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%)', // Light gradient
      }}
    >
      <Container maxWidth="xs">
        <Paper
          elevation={12}
          sx={{
            p: { xs: 3, sm: 5 },
            borderRadius: 4,
            backdropFilter: 'blur(10px)',
            backgroundColor: 'rgba(255, 255, 255, 0.7)',
            ...(mode === 'dark' && {
              backgroundColor: 'rgba(30, 41, 59, 0.7)',
            }),
          }}
        >
          <Outlet />
        </Paper>
      </Container>
    </Box>
  )
}

export default AuthLayout