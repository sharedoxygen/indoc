import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  InputAdornment,
  IconButton,
  Divider,
} from '@mui/material'
import {
  Visibility,
  VisibilityOff,
  Email as EmailIcon,
  Lock as LockIcon,
} from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '../hooks/redux'
import { login, clearError } from '../store/slices/authSlice'
import Logo from '../components/Logo'

const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { isLoading, error } = useAppSelector((state) => state.auth)

  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [showPassword, setShowPassword] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    if (error) {
      dispatch(clearError())
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    try {
      const success = await dispatch(login(formData)).unwrap()
      if (success) navigate('/dashboard')
    } catch (err) {
      // handled in slice
    }
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <Box sx={{ width: 380 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 2 }}>
          <Logo />
        </Box>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Welcome back</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Sign in to continue</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error)}</Alert>}
        <form onSubmit={handleSubmit}>
          <TextField fullWidth label="Email" name="username" value={formData.username} onChange={handleChange} margin="dense" InputProps={{ startAdornment: <InputAdornment position="start"><IconButton size="small"><EmailIcon /></IconButton></InputAdornment> }} />
          <TextField fullWidth label="Password" name="password" type={showPassword ? 'text' : 'password'} value={formData.password} onChange={handleChange} margin="dense" InputProps={{ startAdornment: <InputAdornment position="start"><IconButton size="small"><LockIcon /></IconButton></InputAdornment>, endAdornment: <InputAdornment position="end"><IconButton onClick={() => setShowPassword(!showPassword)} edge="end">{showPassword ? <VisibilityOff /> : <Visibility />}</IconButton></InputAdornment> }} />
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', my: 1 }}>
            <Box />
            <Link to="/register">Create account</Link>
          </Box>
          <Button type="submit" variant="contained" fullWidth disabled={isLoading}>Sign In</Button>
        </form>
        <Divider sx={{ my: 3 }} />
        <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
          By signing in you agree to our terms.
        </Typography>
        <Typography 
          variant="caption" 
          color="text.secondary" 
          sx={{ mt: 2, textAlign: 'center', display: 'block' }}
        >
          © 2025 Shared Oxygen, LLC. All rights reserved.
        </Typography>
      </Box>
    </Box>
  )
}

export default LoginPage