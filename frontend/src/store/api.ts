import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { RootState } from './index'

const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.token
    console.log('🔑 API request token:', token ? 'present' : 'missing')
    if (token) {
      headers.set('authorization', `Bearer ${token}`)
    }
    return headers
  },
})

export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Document', 'Audit', 'Settings'],
  keepUnusedDataFor: 300, // Keep cached data for 5 minutes
  endpoints: (builder) => ({
    // Auth endpoints
    login: builder.mutation({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: new URLSearchParams(credentials),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }),
    }),
    register: builder.mutation({
      query: (userData) => ({
        url: '/auth/register',
        method: 'POST',
        body: userData,
      }),
    }),
    getCurrentUser: builder.query({
      query: () => '/auth/me',
      providesTags: ['User'],
    }),

    // Document endpoints
    getDocuments: builder.query<any, { skip?: number; limit?: number; search?: string; file_type?: string; sort_by?: string; sort_order?: string; status?: string } | void>({
      query: ({ skip = 0, limit = 10, search, file_type, sort_by, sort_order, status } = {}) => {
        const params = new URLSearchParams({
          skip: skip.toString(),
          limit: limit.toString(),
        });
        if (search) params.append('search', search);
        if (file_type && file_type !== 'all') params.append('file_type', file_type);
        if (sort_by) params.append('sort_by', sort_by);
        if (sort_order) params.append('sort_order', sort_order);
        if (status) params.append('status', status);
        return `/files/list?${params.toString()}`;
      },
      providesTags: (result, error, arg) => [
        { type: 'Document', id: 'LIST' },
        ...(result?.documents || []).map((doc: any) => ({ type: 'Document' as const, id: doc.id }))
      ],
      keepUnusedDataFor: 0, // Don't cache - always fetch fresh
    }),
    getDocument: builder.query({
      query: (id) => `/files/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Document', id }],
    }),
    uploadDocument: builder.mutation({
      query: (formData) => ({
        url: '/files/upload',
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: ['Document'],
    }),

    // Analytics endpoints
    getAnalyticsSummary: builder.query<any, void>({
      query: () => `/analytics/summary`,
    }),
    getAnalyticsStorage: builder.query<any, void>({
      query: () => `/analytics/storage`,
    }),
    getAnalyticsTimeseries: builder.query<any, { days?: number }>({
      query: ({ days = 30 } = {}) => `/analytics/timeseries?days=${days}`,
    }),
    getProcessingAnalytics: builder.query<any, void>({
      query: () => `/analytics/processing`,
    }),
    updateDocument: builder.mutation({
      query: ({ id, ...data }) => ({
        url: `/files/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [{ type: 'Document', id }],
    }),
    deleteDocument: builder.mutation({
      query: (id) => ({
        url: `/files/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Document'],
    }),

    // Processing queue actions
    retryDocument: builder.mutation<{ ok: boolean }, string>({
      query: (id) => ({
        url: `/files/retry/${id}`,
        method: 'POST',
      }),
      invalidatesTags: ['Document'],
    }),
    cancelDocument: builder.mutation<{ ok: boolean }, string>({
      query: (id) => ({
        url: `/files/cancel/${id}`,
        method: 'POST',
      }),
      invalidatesTags: ['Document'],
    }),
    scanVirusDocument: builder.mutation<{ ok: boolean; scan_result: any; virus_status: string }, string>({
      query: (id) => ({
        url: `/files/scan_virus/${id}`,
        method: 'POST',
      }),
      invalidatesTags: ['Document'],
    }),

    // Search endpoints
    searchDocuments: builder.mutation({
      query: (searchQuery) => ({
        url: '/search/query',
        method: 'POST',
        body: searchQuery,
      }),
    }),
    findSimilarDocuments: builder.query({
      query: ({ id, limit = 5 }) => `/search/documents/${id}/similar?limit=${limit}`,
    }),



    // User management endpoints
    getUsers: builder.query({
      query: ({ skip = 0, limit = 100 }) => `/users?skip=${skip}&limit=${limit}`,
      providesTags: ['User'],
    }),
    updateUser: builder.mutation({
      query: ({ id, ...data }) => ({
        url: `/users/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: ['User'],
    }),
    deleteUser: builder.mutation({
      query: (id) => ({
        url: `/users/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['User'],
    }),

    // Audit endpoints
    getAuditLogs: builder.query({
      query: (params) => ({
        url: '/audit/logs',
        params,
      }),
      providesTags: ['Audit'],
    }),
    exportAuditLogs: builder.mutation({
      query: (params) => ({
        url: '/audit/logs/export',
        method: 'POST',
        params,
      }),
    }),

    // Settings endpoints (align with backend)
    getSettings: builder.query({
      query: () => `/settings`,
      providesTags: () => [{ type: 'Settings', id: 'base' }],
    }),
    getAdminSettings: builder.query({
      query: () => `/settings/admin`,
      providesTags: () => [{ type: 'Settings', id: 'admin' }],
    }),
    updateAdminSettings: builder.mutation({
      query: (settingsUpdate) => ({
        url: `/settings/admin`,
        method: 'PUT',
        body: settingsUpdate,
      }),
      invalidatesTags: () => [{ type: 'Settings', id: 'admin' }],
    }),
    getFeatureFlags: builder.query({
      query: () => `/settings/features`,
    }),
    getDependenciesHealth: builder.query({
      query: () => `/settings/health/dependencies`,
    }),

    // MCP endpoints (align with backend)
    executeTool: builder.mutation({
      query: (command) => ({
        url: '/mcp/execute',
        method: 'POST',
        body: command,
      }),
    }),
    getMcpStatus: builder.query({
      query: () => '/mcp/status',
    }),
  }),
})

export const {
  useLoginMutation,
  useRegisterMutation,
  useGetCurrentUserQuery,
  useGetDocumentsQuery,
  useGetDocumentQuery,
  useUploadDocumentMutation,
  useUpdateDocumentMutation,
  useDeleteDocumentMutation,
  useSearchDocumentsMutation,
  useFindSimilarDocumentsQuery,
  useGetUsersQuery,
  useUpdateUserMutation,
  useDeleteUserMutation,
  useGetAuditLogsQuery,
  useExportAuditLogsMutation,
  useGetSettingsQuery,
  useGetAdminSettingsQuery,
  useUpdateAdminSettingsMutation,
  useGetFeatureFlagsQuery,
  useGetDependenciesHealthQuery,
  useExecuteToolMutation,
  useGetMcpStatusQuery,
  useGetAnalyticsSummaryQuery,
  useGetAnalyticsStorageQuery,
  useGetAnalyticsTimeseriesQuery,
  useGetProcessingAnalyticsQuery,
  useRetryDocumentMutation,
  useCancelDocumentMutation,
  useScanVirusDocumentMutation,
} = api