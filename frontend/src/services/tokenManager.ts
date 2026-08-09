/**
 * Token Management Service
 * 
 * Handles:
 * - Token validation on startup
 * - Automatic 401 handling and logout
 * - Token expiry detection
 * - Invalid token cleanup
 */

import { jwtDecode } from 'jwt-decode'
import axios from 'axios'

interface DecodedToken {
  sub: string
  role: string
  exp: number
  jti: string
  type: string
}

export class TokenManager {
  private static TOKEN_KEY = 'token'
  private static REFRESH_TOKEN_KEY = 'refresh_token'

  /**
   * Validate token on app startup
   * Returns true if token is valid, false if invalid/expired
   */
  static async validateTokenOnStartup(): Promise<boolean> {
    const token = this.getToken()
    
    if (!token) {
      console.log('🔐 No token found on startup')
      return false
    }

    try {
      // First check if token is expired based on JWT claims
      const decoded = this.decodeToken(token)
      
      if (!decoded) {
        console.warn('⚠️  Failed to decode token')
        this.clearTokens()
        return false
      }

      const now = Math.floor(Date.now() / 1000)
      const expiresIn = decoded.exp - now

      if (expiresIn <= 0) {
        console.warn('⚠️  Token expired:', new Date(decoded.exp * 1000).toISOString())
        this.clearTokens()
        return false
      }

      console.log(`✅ Token valid for ${Math.floor(expiresIn / 60)} more minutes`)

      // Then verify with backend
      try {
        const response = await axios.get('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 5000
        })
        
        if (response.status === 200) {
          console.log('✅ Token validated with backend')
          return true
        }
      } catch (error: any) {
        if (error.response?.status === 401) {
          console.warn('⚠️  Token rejected by backend (401)')
          this.clearTokens()
          return false
        }
        // Network error - allow app to start (will retry later)
        console.warn('⚠️  Backend validation failed (network error), allowing startup')
        return true
      }

      return true

    } catch (error) {
      console.error('❌ Token validation error:', error)
      this.clearTokens()
      return false
    }
  }

  /**
   * Decode JWT token without verifying signature
   * Used for client-side expiry checks
   */
  static decodeToken(token: string): DecodedToken | null {
    try {
      return jwtDecode<DecodedToken>(token)
    } catch (error) {
      console.error('Failed to decode token:', error)
      return null
    }
  }

  /**
   * Check if token is expired or expiring soon
   * Returns:
   *  - 'expired' if token is expired
   *  - 'expiring' if token expires in < 5 minutes
   *  - 'valid' if token is valid for > 5 minutes
   *  - 'invalid' if token is malformed
   */
  static checkTokenStatus(): 'expired' | 'expiring' | 'valid' | 'invalid' {
    const token = this.getToken()
    
    if (!token) {
      return 'invalid'
    }

    const decoded = this.decodeToken(token)
    
    if (!decoded) {
      return 'invalid'
    }

    const now = Math.floor(Date.now() / 1000)
    const expiresIn = decoded.exp - now

    if (expiresIn <= 0) {
      return 'expired'
    }

    if (expiresIn < 5 * 60) { // < 5 minutes
      return 'expiring'
    }

    return 'valid'
  }

  /**
   * Get token from localStorage
   */
  static getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY)
  }

  /**
   * Get refresh token from localStorage
   */
  static getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }

  /**
   * Clear all tokens from localStorage
   */
  static clearTokens(): void {
    localStorage.removeItem(this.TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
    console.log('🗑️  Tokens cleared from localStorage')
  }

  /**
   * Get token expiration time as milliseconds since epoch
   */
  static getTokenExpiryTime(): number | null {
    const token = this.getToken()
    
    if (!token) {
      return null
    }

    const decoded = this.decodeToken(token)
    
    if (!decoded) {
      return null
    }

    return decoded.exp * 1000 // Convert to milliseconds
  }

  /**
   * Get human-readable time until token expires
   */
  static getTimeUntilExpiry(): string | null {
    const expiryTime = this.getTokenExpiryTime()
    
    if (!expiryTime) {
      return null
    }

    const now = Date.now()
    const diff = expiryTime - now

    if (diff <= 0) {
      return 'Expired'
    }

    const minutes = Math.floor(diff / (60 * 1000))
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) {
      return `${days} day${days > 1 ? 's' : ''}`
    }

    if (hours > 0) {
      return `${hours} hour${hours > 1 ? 's' : ''}`
    }

    return `${minutes} minute${minutes !== 1 ? 's' : ''}`
  }
}

/**
 * Setup axios interceptor to handle 401 responses
 */
export function setupAxiosInterceptor(onUnauthorized: () => void) {
  axios.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        console.error('❌ 401 Unauthorized - Logging out')
        
        // Clear tokens
        TokenManager.clearTokens()
        
        // Trigger logout callback
        onUnauthorized()
      }
      
      return Promise.reject(error)
    }
  )
}

