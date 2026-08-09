import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  Badge,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Description as DocumentIcon,
  CloudUpload as UploadIcon,
  Chat as ChatIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  History as HistoryIcon,
  Notifications as NotificationsIcon,
  Logout as LogoutIcon,
  LightMode as LightModeIcon,
  DarkMode as DarkModeIcon,
  HourglassTop as HourglassTopIcon,
  Timeline as TimelineIcon,
  AccountTree as OwnershipIcon,
  Security as SecurityIcon,
  Share as ShareIcon,
  Terminal as TerminalIcon,
  Search as SearchInspectorIcon,
} from '@mui/icons-material'
import { useAppSelector, useAppDispatch } from '../hooks/redux'
import { logout } from '../store/slices/authSlice'
import { useThemeMode } from '../contexts/ThemeContext'
import Logo from '../components/Logo'
import { TokenExpiryIndicator } from '../components/TokenExpiryIndicator'

const drawerWidth = 240

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useAppDispatch()
  const { user } = useAppSelector((state) => state.auth)
  const { mode, toggleColorMode } = useThemeMode()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleProfileMenuClose = () => {
    setAnchorEl(null)
  }

  const handleLogout = async () => {
    try {
      // Wait for logout to complete
      await dispatch(logout()).unwrap()
    } catch {
      // ignore errors and proceed to login
    }
    navigate('/login')
  }

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard', roles: ['all'] },
    { text: 'Chat', icon: <ChatIcon />, path: '/chat', roles: ['all'] },
    { text: 'Documents', icon: <DocumentIcon />, path: '/documents', roles: ['all'] },
    // Consolidated identity hub
    { text: 'Identity (Users & RBAC)', icon: <SecurityIcon />, path: '/identity', roles: ['Admin', 'Manager'] },
    { text: 'Team', icon: <PeopleIcon />, path: '/team', roles: ['Manager'] },
    { text: 'Audit Trail', icon: <HistoryIcon />, path: '/audit', roles: ['Admin', 'Manager', 'Compliance'] },
    { text: 'System Logs', icon: <TerminalIcon />, path: '/logs', roles: ['Admin'] },
    { text: 'Search Inspector', icon: <SearchInspectorIcon />, path: '/search-inspector', roles: ['Admin', 'Manager'] },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings', roles: ['Admin'] },
    // External monitoring links (Grafana)
    { text: 'Monitoring', icon: <TimelineIcon />, path: 'EXTERNAL:grafana', roles: ['Admin', 'Manager'] },
  ]

  const filteredMenuItems = menuItems.filter(
    (item) => item.roles.includes('all') || (user && item.roles.includes(user.role))
  )

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ px: 2 }}>
        <Logo size="medium" />
      </Toolbar>
      <Divider />
      <List sx={{ flexGrow: 1, px: 1 }}>
        {filteredMenuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => {
                if (item.path === 'EXTERNAL:grafana') {
                  window.open('http://localhost:3030', '_blank', 'noopener,noreferrer')
                } else {
                  navigate(item.path)
                }
              }}
              sx={{
                borderRadius: 2,
                mb: 0.5,
                '&.Mui-selected': {
                  backgroundColor: 'primary.50',
                  color: 'primary.600',
                  '& .MuiListItemIcon-root': {
                    color: 'primary.600',
                  },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText
                primary={item.text}
                primaryTypographyProps={{
                  fontWeight: location.pathname === item.path ? 600 : 500,
                  fontSize: '0.875rem'
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      {/* Dark mode toggle in sidebar */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <FormControlLabel
          control={
            <Switch
              checked={mode === 'dark'}
              onChange={toggleColorMode}
              size="small"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {mode === 'dark' ? <DarkModeIcon fontSize="small" /> : <LightModeIcon fontSize="small" />}
              <Typography variant="body2">
                {mode === 'dark' ? 'Dark' : 'Light'} Mode
              </Typography>
            </Box>
          }
          sx={{ margin: 0 }}
        />
      </Box>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      {/* Token Expiry Warning */}
      <TokenExpiryIndicator />
      
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
            {filteredMenuItems.find((item) => item.path === location.pathname)?.text || 'Dashboard'}
          </Typography>

          {/* Dark mode toggle in header (for desktop) */}
          <Tooltip title={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}>
            <IconButton onClick={toggleColorMode} color="inherit" sx={{ mr: 1 }}>
              {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>

          <Tooltip title="Notifications">
            <IconButton color="inherit">
              <Badge badgeContent={0} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          <IconButton
            onClick={handleProfileMenuOpen}
            color="inherit"
            sx={{ ml: 2 }}
          >
            <Avatar sx={{ width: 32, height: 32 }}>
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
            </Avatar>
          </IconButton>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleProfileMenuClose}
          >
            <MenuItem disabled>
              <Typography variant="body2">{user?.email}</Typography>
            </MenuItem>
            <MenuItem disabled>
              <Typography variant="caption" color="text.secondary">
                Role: {user?.role}
              </Typography>
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
            disableAutoFocus: true,
            disableEnforceFocus: true,
            disableRestoreFocus: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
        }}
      >
        <Outlet />
      </Box>


    </Box>
  )
}

export default MainLayout