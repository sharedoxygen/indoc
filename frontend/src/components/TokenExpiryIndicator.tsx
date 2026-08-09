/**
 * Token Expiry Indicator
 * 
 * Shows a warning banner when the user's token is expiring soon
 */

import { useState, useEffect } from 'react'
import { Alert, AlertTitle, Button, Snackbar, Box } from '@mui/material'
import { Warning as WarningIcon, Refresh as RefreshIcon } from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '../hooks/redux'
import { refreshAccessToken } from '../store/slices/authSlice'
import { TokenManager } from '../services/tokenManager'

export const TokenExpiryIndicator = () => {
  const dispatch = useAppDispatch()
  const { isAuthenticated } = useAppSelector(state => state.auth)
  const [showWarning, setShowWarning] = useState(false)
  const [timeUntilExpiry, setTimeUntilExpiry] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      setShowWarning(false)
      return
    }

    const checkTokenStatus = () => {
      const status = TokenManager.checkTokenStatus()
      const timeLeft = TokenManager.getTimeUntilExpiry()
      
      setTimeUntilExpiry(timeLeft)

      if (status === 'expiring' || status === 'expired') {
        setShowWarning(true)
      } else {
        setShowWarning(false)
      }
    }

    // Check immediately
    checkTokenStatus()

    // Then check every minute
    const interval = setInterval(checkTokenStatus, 60 * 1000)

    return () => clearInterval(interval)
  }, [isAuthenticated])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await dispatch(refreshAccessToken()).unwrap()
      setShowWarning(false)
      console.log('✅ Token refreshed manually')
    } catch (error) {
      console.error('❌ Failed to refresh token:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  if (!showWarning || !isAuthenticated) {
    return null
  }

  return (
    <Snackbar
      open={showWarning}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      sx={{ mt: 8 }}
    >
      <Alert
        severity="warning"
        icon={<WarningIcon />}
        action={
          <Button
            color="inherit"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
          </Button>
        }
        sx={{
          minWidth: 400,
          '& .MuiAlert-message': {
            width: '100%'
          }
        }}
      >
        <AlertTitle>Session Expiring Soon</AlertTitle>
        <Box>
          Your session will expire in <strong>{timeUntilExpiry}</strong>.
          {' '}Refresh your session to continue working.
        </Box>
      </Alert>
    </Snackbar>
  )
}

