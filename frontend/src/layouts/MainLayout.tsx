import React, { useEffect, useMemo, useState } from 'react'
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
  Collapse,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Description as DocumentIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  History as HistoryIcon,
  Notifications as NotificationsIcon,
  Logout as LogoutIcon,
  LightMode as LightModeIcon,
  DarkMode as DarkModeIcon,
  Timeline as TimelineIcon,
  Security as SecurityIcon,
  Terminal as TerminalIcon,
  Search as SearchInspectorIcon,
  ExpandLess,
  ExpandMore,
  Hub as WorkspaceIcon,
  Policy as GovernanceIcon,
  Dns as SystemIcon,
  AutoAwesome as InsightIcon,
} from '@mui/icons-material'
import { useAppSelector, useAppDispatch } from '../hooks/redux'
import { logout } from '../store/slices/authSlice'
import { useThemeMode } from '../contexts/ThemeContext'
import Logo from '../components/Logo'
import { TokenExpiryIndicator } from '../components/TokenExpiryIndicator'

const drawerWidth = 248

type NavItem = {
  text: string
  icon: React.ReactNode
  path: string
  roles: string[]
}

type NavCategory = {
  id: string
  label: string
  icon: React.ReactNode
  items: NavItem[]
}

const NAV_STORAGE_KEY = 'indoc.nav.collapsed'

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useAppDispatch()
  const { user } = useAppSelector((state) => state.auth)
  const { mode, toggleColorMode } = useThemeMode()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(NAV_STORAGE_KEY)
      if (!raw) return {}
      const parsed = JSON.parse(raw)
      return parsed && typeof parsed === 'object' ? parsed : {}
    } catch {
      return {}
    }
  })

  useEffect(() => {
    localStorage.setItem(NAV_STORAGE_KEY, JSON.stringify(collapsed))
  }, [collapsed])

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen)
  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget)
  const handleProfileMenuClose = () => setAnchorEl(null)

  const handleLogout = async () => {
    try {
      await dispatch(logout()).unwrap()
    } catch {
      /* proceed */
    }
    navigate('/login')
  }

  const categories: NavCategory[] = useMemo(
    () => [
      {
        id: 'workspace',
        label: 'Workspace',
        icon: <WorkspaceIcon fontSize="small" />,
        items: [
          { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard', roles: ['all'] },
          { text: 'Research Desk', icon: <InsightIcon />, path: '/chat', roles: ['all'] },
          { text: 'Documents', icon: <DocumentIcon />, path: '/documents', roles: ['all'] },
        ],
      },
      {
        id: 'governance',
        label: 'Governance',
        icon: <GovernanceIcon fontSize="small" />,
        items: [
          { text: 'Identity', icon: <SecurityIcon />, path: '/identity', roles: ['Admin', 'Manager'] },
          { text: 'Team', icon: <PeopleIcon />, path: '/team', roles: ['Manager'] },
          { text: 'Audit Trail', icon: <HistoryIcon />, path: '/audit', roles: ['Admin', 'Manager', 'Compliance'] },
        ],
      },
      {
        id: 'system',
        label: 'System',
        icon: <SystemIcon fontSize="small" />,
        items: [
          { text: 'Search Inspector', icon: <SearchInspectorIcon />, path: '/search-inspector', roles: ['Admin', 'Manager'] },
          { text: 'System Logs', icon: <TerminalIcon />, path: '/logs', roles: ['Admin'] },
          { text: 'Monitoring', icon: <TimelineIcon />, path: '/monitoring', roles: ['Admin', 'Manager'] },
          { text: 'Settings', icon: <SettingsIcon />, path: '/settings', roles: ['Admin'] },
        ],
      },
    ],
    []
  )

  const roleOk = (roles: string[]) => roles.includes('all') || (user && roles.includes(user.role))

  const visibleCategories = categories
    .map((cat) => ({ ...cat, items: cat.items.filter((item) => roleOk(item.roles)) }))
    .filter((cat) => cat.items.length > 0)

  const activeTitle =
    visibleCategories.flatMap((c) => c.items).find((item) => location.pathname === item.path)?.text || 'Dashboard'

  // Auto-expand category containing the active route
  useEffect(() => {
    const activeCat = visibleCategories.find((c) => c.items.some((i) => i.path === location.pathname))
    if (activeCat && collapsed[activeCat.id]) {
      setCollapsed((prev) => ({ ...prev, [activeCat.id]: false }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  const toggleCategory = (id: string) => {
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const drawer = (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background:
          mode === 'dark'
            ? 'linear-gradient(180deg, #0c1016 0%, #0a0d12 55%, #080a0e 100%)'
            : 'linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%)',
      }}
    >
      <Toolbar sx={{ px: 2, minHeight: 64 }}>
        <Logo size="medium" />
      </Toolbar>
      <Divider sx={{ opacity: 0.5 }} />

      <Box sx={{ flexGrow: 1, overflow: 'auto', px: 1, py: 1.25 }}>
        {visibleCategories.map((cat) => {
          const isOpen = !collapsed[cat.id]
          const hasActive = cat.items.some((i) => location.pathname === i.path)
          return (
            <Box key={cat.id} sx={{ mb: 0.75 }}>
              <ListItemButton
                onClick={() => toggleCategory(cat.id)}
                sx={{
                  borderRadius: 1.5,
                  py: 0.7,
                  px: 1,
                  color: hasActive ? 'primary.main' : 'text.secondary',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 30, color: 'inherit' }}>{cat.icon}</ListItemIcon>
                <ListItemText
                  primary={cat.label}
                  primaryTypographyProps={{
                    fontSize: '0.68rem',
                    fontWeight: 750,
                    letterSpacing: 1.2,
                    textTransform: 'uppercase',
                  }}
                />
                {isOpen ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
              </ListItemButton>

              <Collapse in={isOpen} timeout="auto" unmountOnExit>
                <List dense disablePadding sx={{ mt: 0.25 }}>
                  {cat.items.map((item) => {
                    const selected = location.pathname === item.path
                    return (
                      <ListItem key={item.path} disablePadding>
                        <ListItemButton
                          selected={selected}
                          onClick={() => {
                            navigate(item.path)
                            setMobileOpen(false)
                          }}
                          sx={{
                            borderRadius: 1.5,
                            mb: 0.25,
                            ml: 0.5,
                            py: 0.85,
                            '&.Mui-selected': {
                              background:
                                mode === 'dark'
                                  ? 'linear-gradient(90deg, rgba(25,118,210,0.22) 0%, rgba(25,118,210,0.06) 100%)'
                                  : 'linear-gradient(90deg, rgba(25,118,210,0.12) 0%, rgba(25,118,210,0.04) 100%)',
                              border: '1px solid',
                              borderColor: 'primary.main',
                              borderLeftWidth: 3,
                              '& .MuiListItemIcon-root': { color: 'primary.main' },
                            },
                          }}
                        >
                          <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                          <ListItemText
                            primary={item.text}
                            primaryTypographyProps={{
                              fontWeight: selected ? 650 : 500,
                              fontSize: '0.84rem',
                            }}
                          />
                        </ListItemButton>
                      </ListItem>
                    )
                  })}
                </List>
              </Collapse>
            </Box>
          )
        })}
      </Box>

      <Box sx={{ p: 1.75, borderTop: 1, borderColor: 'divider' }}>
        <FormControlLabel
          control={<Switch checked={mode === 'dark'} onChange={toggleColorMode} size="small" />}
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {mode === 'dark' ? <DarkModeIcon fontSize="small" /> : <LightModeIcon fontSize="small" />}
              <Typography variant="body2">{mode === 'dark' ? 'Dark' : 'Light'} Mode</Typography>
            </Box>
          }
          sx={{ margin: 0 }}
        />
      </Box>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', width: '100%' }}>
      <TokenExpiryIndicator />

      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: mode === 'dark' ? 'rgba(10,13,18,0.85)' : 'rgba(255,255,255,0.82)',
          backdropFilter: 'blur(14px)',
          color: 'text.primary',
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
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 650, letterSpacing: '-0.02em' }}>
            {activeTitle}
          </Typography>

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

          <IconButton onClick={handleProfileMenuOpen} color="inherit" sx={{ ml: 1.5 }}>
            <Avatar sx={{ width: 32, height: 32, fontSize: 13, fontWeight: 700 }}>
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
            </Avatar>
          </IconButton>

          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleProfileMenuClose}>
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

      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
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
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, borderRight: '1px solid', borderColor: 'divider' },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, borderRight: '1px solid', borderColor: 'divider' },
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
          p: { xs: 2, md: 3 },
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
          minHeight: '100vh',
          background:
            mode === 'dark'
              ? 'radial-gradient(1200px 600px at 10% -10%, rgba(25,118,210,0.12), transparent 55%), radial-gradient(900px 500px at 90% 0%, rgba(0,188,212,0.08), transparent 50%), #07090d'
              : 'radial-gradient(1200px 600px at 10% -10%, rgba(25,118,210,0.08), transparent 55%), #f4f6f9',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}

export default MainLayout
