import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  MenuItem,
  InputAdornment,
  IconButton,
} from '@mui/material'
import {
  Email as EmailIcon,
  Person as PersonIcon,
  Badge as BadgeIcon,
  Lock as LockIcon,
  LockReset as LockResetIcon,
  Work as WorkIcon,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '../hooks/redux'
import { register } from '../store/slices/authSlice'
import Logo from '../components/Logo'

const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { isLoading, error } = useAppSelector((state) => state.auth)

  const [formData, setFormData] = useState({
    email: '',
    username: '',
    full_name: '',
    password: '',
    confirmPassword: '',
    role: 'Viewer',
  })
  const [validationError, setValidationError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    setValidationError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (formData.password !== formData.confirmPassword) {
      setValidationError('Passwords do not match')
      return
    }

    if (formData.password.length < 8) {
      setValidationError('Password must be at least 8 characters')
      return
    }

    const result = await dispatch(register({
      email: formData.email,
      username: formData.username,
      full_name: formData.full_name,
      password: formData.password,
      role: formData.role,
    }))

    if (register.fulfilled.match(result)) {
      navigate('/login')
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
        <Logo size="large" />
      </Box>

      <Typography variant="h4" gutterBottom align="center" sx={{ fontWeight: 700, mb: 1 }}>
        Create Account
      </Typography>
      <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 4, fontSize: '1.1rem' }}>
        Join inDoc to manage your documents
      </Typography>

      {(error || validationError) && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error || validationError}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            fullWidth
            name="email"
            label="Email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <EmailIcon color="action" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            name="username"
            label="Username"
            value={formData.username}
            onChange={handleChange}
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <PersonIcon color="action" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            name="full_name"
            label="Full Name"
            value={formData.full_name}
            onChange={handleChange}
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <BadgeIcon color="action" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            name="password"
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={formData.password}
            onChange={handleChange}
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LockIcon color="action" />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            name="confirmPassword"
            label="Confirm Password"
            type="password"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LockResetIcon color="action" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            select
            name="role"
            label="Role"
            value={formData.role}
            onChange={handleChange}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <WorkIcon color="action" />
                </InputAdornment>
              ),
            }}
          >
            <MenuItem value="Viewer">Viewer</MenuItem>
            <MenuItem value="Uploader">Uploader</MenuItem>
          </TextField>
        </Box>

        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          sx={{
            mt: 4,
            mb: 3,
            py: 1.5,
            fontSize: '1rem',
            fontWeight: 600,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
            '&:hover': {
              background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)',
              transform: 'translateY(-1px)',
              boxShadow: 4,
            },
          }}
          disabled={isLoading}
        >
          {isLoading ? 'Creating Account...' : 'Sign Up'}
        </Button>

        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="body2">
            Already have an account?{' '}
            <Link
              to="/login"
              style={{
                textDecoration: 'none',
                color: '#1976d2',
                fontWeight: 600,
              }}
            >
              Sign in
            </Link>
          </Typography>
        </Box>
      </form>
    </Box>
  )
}

export default RegisterPage