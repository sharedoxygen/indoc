import { useEffect, useRef } from 'react'
import { useAppDispatch, useAppSelector } from './redux'
import { refreshAccessToken, logout } from '../store/slices/authSlice'

/**
 * Automatic Token Refresh Hook
 * 
 * Automatically refreshes the access token before it expires
 * - Checks every 5 minutes
 * - Refreshes if token expires in < 15 minutes
 * - Logs out if refresh fails (refresh token expired)
 */
export const useTokenRefresh = () => {
  const dispatch = useAppDispatch()
  const { isAuthenticated, tokenExpiresAt, refreshToken } = useAppSelector(state => state.auth)
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const isRefreshing = useRef(false)

  useEffect(() => {
    if (!isAuthenticated || !refreshToken) {
      // Not logged in or no refresh token - clear interval
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
        refreshIntervalRef.current = null
      }
      return
    }

    const checkAndRefresh = async () => {
      // Prevent multiple simultaneous refresh attempts
      if (isRefreshing.current) {
        return
      }

      const now = Date.now()
      const fifteenMinutes = 15 * 60 * 1000

      // If we have an expiration time and it's within 15 minutes, refresh
      if (tokenExpiresAt && tokenExpiresAt - now < fifteenMinutes) {
        console.log('🔄 Token expiring soon, refreshing...')
        isRefreshing.current = true

        try {
          await dispatch(refreshAccessToken()).unwrap()
          console.log('✅ Token refreshed successfully')
        } catch (error) {
          console.error('❌ Token refresh failed:', error)
          // Refresh token expired - logout
          await dispatch(logout())
        } finally {
          isRefreshing.current = false
        }
      }
    }

    // Check immediately on mount
    checkAndRefresh()

    // Then check every 5 minutes
    refreshIntervalRef.current = setInterval(checkAndRefresh, 5 * 60 * 1000)

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
      }
    }
  }, [isAuthenticated, tokenExpiresAt, refreshToken, dispatch])
}

