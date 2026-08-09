import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

interface User {
  id: number
  email: string
  username: string
  full_name: string
  role: string
  is_active: boolean
  is_verified: boolean
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  tokenExpiresAt: number | null
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('token'),
  refreshToken: localStorage.getItem('refresh_token'),
  isAuthenticated: false,
  isLoading: true,
  error: null,
  tokenExpiresAt: null,
}

// Debug initial auth state
console.log('🔐 Initial auth state:', {
  token: localStorage.getItem('token') ? 'present' : 'missing',
  isAuthenticated: false,
  isLoading: true
})

export const checkAuth = createAsyncThunk(
  'auth/checkAuth',
  async (_, { rejectWithValue }) => {
    const token = localStorage.getItem('token')
    if (!token) {
      return rejectWithValue('No token found')
    }

    try {
      const response = await axios.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      return response.data
    } catch (error) {
      localStorage.removeItem('token')
      return rejectWithValue('Invalid token')
    }
  }
)

export const refreshAccessToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { rejectWithValue }) => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      return rejectWithValue('No refresh token found')
    }

    try {
      const response = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken
      })

      const { access_token } = response.data
      localStorage.setItem('token', access_token)

      // Calculate expiration (24 hours from now)
      const expiresAt = Date.now() + (24 * 60 * 60 * 1000)

      return {
        token: access_token,
        expiresAt,
      }
    } catch (error: any) {
      // Refresh token expired or invalid - clear everything
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      return rejectWithValue('Session expired. Please login again.')
    }
  }
)

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }, { rejectWithValue }) => {
    try {
      const formData = new URLSearchParams()
      formData.append('username', credentials.username)
      formData.append('password', credentials.password)

      const response = await axios.post('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const { access_token, refresh_token } = response.data
      localStorage.setItem('token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      // Calculate expiration (24 hours from now)
      const expiresAt = Date.now() + (24 * 60 * 60 * 1000)

      // Get user info
      const userResponse = await axios.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      })

      return {
        token: access_token,
        refreshToken: refresh_token,
        user: userResponse.data,
        expiresAt,
      }
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Login failed')
    }
  }
)

export const register = createAsyncThunk(
  'auth/register',
  async (userData: any, { rejectWithValue }) => {
    try {
      const response = await axios.post('/api/v1/auth/register', userData)
      return response.data
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Registration failed')
    }
  }
)

export const logout = createAsyncThunk('auth/logout', async () => {
  try {
    const token = localStorage.getItem('token')
    if (token) {
      await axios.post(
        '/api/v1/auth/logout',
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )
    }
  } finally {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  }
})

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    // Check Auth
    builder
      .addCase(checkAuth.pending, (state) => {
        state.isLoading = true
      })
      .addCase(checkAuth.fulfilled, (state, action) => {
        state.isLoading = false
        state.isAuthenticated = true
        state.user = action.payload
        state.token = localStorage.getItem('token') // Ensure token is synced
        state.error = null
      })
      .addCase(checkAuth.rejected, (state) => {
        state.isLoading = false
        state.isAuthenticated = false
        state.user = null
        state.token = null
      })

    // Refresh Token
    builder
      .addCase(refreshAccessToken.fulfilled, (state, action) => {
        state.token = action.payload.token
        state.tokenExpiresAt = action.payload.expiresAt
        state.error = null
      })
      .addCase(refreshAccessToken.rejected, (state, action) => {
        // Token refresh failed - logout user
        state.user = null
        state.token = null
        state.refreshToken = null
        state.isAuthenticated = false
        state.tokenExpiresAt = null
        state.error = action.payload as string
      })

    // Login
    builder
      .addCase(login.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false
        state.isAuthenticated = true
        state.token = action.payload.token
        state.refreshToken = action.payload.refreshToken
        state.user = action.payload.user
        state.tokenExpiresAt = action.payload.expiresAt
        state.error = null
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as string
      })

    // Register
    builder
      .addCase(register.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(register.fulfilled, (state) => {
        state.isLoading = false
        state.error = null
      })
      .addCase(register.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as string
      })

    // Logout
    builder
      .addCase(logout.fulfilled, (state) => {
        state.user = null
        state.token = null
        state.refreshToken = null
        state.isAuthenticated = false
        state.isLoading = false
        state.tokenExpiresAt = null
        state.error = null
      })
    .addCase(logout.rejected, (state) => {
      state.user = null
      state.token = null
      state.refreshToken = null
      state.isAuthenticated = false
      state.isLoading = false
      state.tokenExpiresAt = null
      state.error = null
    })
  },
})

export const { clearError } = authSlice.actions
export default authSlice.reducer