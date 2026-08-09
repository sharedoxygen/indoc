import axios from 'axios'

// Create axios instance with default config + cache-busting
export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  },
})

// Add request interceptor to include auth token
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const path = error.config?.url || ''
    // Only force logout on true auth failures to auth-required endpoints.
    // Do NOT redirect for 403 (forbidden) or for RBAC endpoints where the user may lack a permission.
    if (status === 401 && !path.includes('/rbac')) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      return
    }
    return Promise.reject(error)
  }
)

// Fetch with timeout utility function (keep for backward compatibility)
export async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit & { timeoutMs?: number } = {}): Promise<Response> {
  const { timeoutMs = 15000, signal, ...rest } = init;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(input, { ...rest, signal: signal ?? controller.signal });
    return response;
  } finally {
    clearTimeout(id);
  }
}
