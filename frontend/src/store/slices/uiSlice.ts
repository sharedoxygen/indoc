import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface Notification {
  id: string
  message: string
  severity: 'success' | 'error' | 'warning' | 'info'
  timestamp: number
}

interface UIState {
  sidebarOpen: boolean
  notifications: Notification[]
  theme: 'light' | 'dark'
}

const initialState: UIState = {
  sidebarOpen: true,
  notifications: [],
  theme: 'light',
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload
    },
    showNotification: (state, action: PayloadAction<Omit<Notification, 'id' | 'timestamp'>>) => {
      const notification: Notification = {
        ...action.payload,
        id: Math.random().toString(36).substr(2, 9),
        timestamp: Date.now(),
      }
      state.notifications.push(notification)
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter((n) => n.id !== action.payload)
    },
    clearNotifications: (state) => {
      state.notifications = []
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload
    },
  },
})

export const {
  toggleSidebar,
  setSidebarOpen,
  showNotification,
  removeNotification,
  clearNotifications,
  setTheme,
} = uiSlice.actions
export default uiSlice.reducer