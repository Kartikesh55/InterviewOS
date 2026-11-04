import axios, { AxiosError } from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import type { HealthResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000, // LLM generation can take up to 2 minutes on a local 3B model
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// Request interceptor — do NOT log request bodies (they may contain user input)
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor — surface errors consistently, without exposing internals
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError) => {
    // Only log status codes and URLs, never payloads
    if (error.response) {
      console.error(`[API ${error.response.status}] ${error.config?.method?.toUpperCase()} ${error.config?.url}`)
    } else {
      console.error(`[API Network Error] ${error.message}`)
    }
    return Promise.reject(error)
  }
)

// ─── System health ────────────────────────────────────────────────────────────

export const systemApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/api/health')
    return response.data
  },
  getAiHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/api/ai/health')
    return response.data
  },
}

export default apiClient
