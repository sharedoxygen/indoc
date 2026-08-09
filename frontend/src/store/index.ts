import { configureStore } from '@reduxjs/toolkit'
import { setupListeners } from '@reduxjs/toolkit/query'

import authReducer from './slices/authSlice'
import documentReducer from './slices/documentSlice'
import searchReducer from './slices/searchSlice'
import uiReducer from './slices/uiSlice'
import { api } from './api'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    document: documentReducer,
    search: searchReducer,
    ui: uiReducer,
    [api.reducerPath]: api.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['document/uploadFile/fulfilled'],
      },
    }).concat(api.middleware),
})

setupListeners(store.dispatch)

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch