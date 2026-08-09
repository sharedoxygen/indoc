import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { Box } from '@mui/material'

import { useAppDispatch, useAppSelector } from './hooks/redux'
import { checkAuth, logout } from './store/slices/authSlice'
import { useTokenRefresh } from './hooks/useTokenRefresh'
import { TokenManager, setupAxiosInterceptor } from './services/tokenManager'

// Layouts
import MainLayout from './layouts/MainLayout'
import AuthLayout from './layouts/AuthLayout'

// Pages
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import UploadPage from './pages/UploadPage'
import DocumentViewer from './pages/DocumentViewer'
import AuditTrailPage from './pages/AuditTrailPage'
import RoleManagementPage from './pages/RoleManagementPage'
import SettingsPage from './pages/SettingsPage'
import DashboardPage from './pages/DashboardPage'
// import AnalyticsPage from './pages/AnalyticsPage'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import DocumentProcessingPage from './pages/DocumentProcessingPage'
import TeamPage from './pages/TeamPage'
import UsersPage from './pages/UsersPage'
import DocumentOwnership from './pages/DocumentOwnership'
import RoleManagement from './pages/RoleManagement'
import DocumentsHubPage from './pages/DocumentsHubPage'
import IdentityHubPage from './pages/IdentityHubPage'
import LogViewerPage from './pages/LogViewerPage'
import SearchInspectorPage from './pages/SearchInspectorPage'

// Components
import PrivateRoute from './components/PrivateRoute'
import LoadingScreen from './components/LoadingScreen'

function App() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { isLoading, isAuthenticated } = useAppSelector((state) => state.auth)
  const [isValidatingToken, setIsValidatingToken] = useState(true)

  // Auto-refresh tokens before they expire
  useTokenRefresh()

  // Setup 401 interceptor on mount
  useEffect(() => {
    setupAxiosInterceptor(() => {
      console.log('🔐 401 detected - Logging out and redirecting to login')
      dispatch(logout())
      navigate('/login')
    })
  }, [dispatch, navigate])

  // Validate token on startup
  useEffect(() => {
    const validateAndInit = async () => {
      setIsValidatingToken(true)

      // First validate token client-side
      const isTokenValid = await TokenManager.validateTokenOnStartup()

      if (!isTokenValid) {
        console.log('⚠️  Invalid/expired token on startup - clearing auth state')
        // Token is invalid - clear everything and don't call checkAuth
        await dispatch(logout()).unwrap().catch(() => {
          // Ignore logout errors
        })
        setIsValidatingToken(false)
        return
      }

      // Token looks valid - proceed with normal auth check
      console.log('✅ Token valid on startup - checking auth')
      await dispatch(checkAuth()).unwrap().catch(() => {
        // If checkAuth fails, also clear and show login
        console.log('⚠️  checkAuth failed - clearing state')
        setIsValidatingToken(false)
      })
      setIsValidatingToken(false)
    }

    validateAndInit()
  }, [dispatch])

  if (isLoading || isValidatingToken) {
    return <LoadingScreen />
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Routes>
        {/* Auth Routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={
            isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />
          } />
          <Route path="/register" element={
            isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterPage />
          } />
        </Route>

        {/* Protected Routes */}
        <Route element={<PrivateRoute />}>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/documents" element={<DocumentsHubPage />} />

            <Route path="/chat" element={<ChatPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/document/:id" element={<DocumentViewer />} />
            <Route path="/audit" element={<AuditTrailPage />} />
            <Route path="/team" element={<TeamPage />} />
            <Route element={<PrivateRoute requiredRoles={['Admin', 'Manager']} />}>
              <Route path="/identity" element={<IdentityHubPage />} />
            </Route>
            <Route element={<PrivateRoute requiredRoles={['Admin']} />}>
              <Route path="/logs" element={<LogViewerPage />} />
            </Route>
            <Route path="/search-inspector" element={<SearchInspectorPage />} />
            {/* Backward-compatible routes redirect to hubs */}
            <Route path="/ownership" element={<Navigate to="/documents?tab=ownership" />} />
            <Route path="/upload" element={<Navigate to="/documents?tab=work" />} />
            <Route path="/document-processing" element={<Navigate to="/documents?tab=work" />} />
            <Route path="/users" element={<Navigate to="/identity?tab=users" />} />
            <Route path="/roles" element={<Navigate to="/identity?tab=roles" />} />
            <Route path="/rbac" element={<Navigate to="/identity?tab=permissions" />} />

            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/document-processing" element={<DocumentProcessingPage />} />
            {/* Legacy redirects */}
            <Route path="/processing-queue" element={<Navigate to="/document-processing" />} />
            <Route path="/processing-pipeline" element={<Navigate to="/document-processing" />} />
          </Route>
        </Route>

        {/* 404 */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Box>
  )
}

export default App