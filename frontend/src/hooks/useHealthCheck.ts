import { useState, useEffect, useCallback } from 'react'
import { systemApi } from '../services/api'
import type { HealthResponse } from '../types'

interface HealthCheckState {
  health: HealthResponse | null
  loading: boolean
  error: string | null
  latencyMs: number | null
}

export function useHealthCheck(pollIntervalMs?: number) {
  const [state, setState] = useState<HealthCheckState>({
    health: null,
    loading: true,
    error: null,
    latencyMs: null,
  })

  const fetchHealth = useCallback(async (): Promise<HealthCheckState> => {
    const startTime = performance.now()
    try {
      const data = await systemApi.getHealth()
      const latency = Math.round(performance.now() - startTime)
      return {
        health: data,
        loading: false,
        error: null,
        latencyMs: latency,
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Backend unreachable'
      return {
        health: null,
        loading: false,
        error: message,
        latencyMs: null,
      }
    }
  }, [])

  const refresh = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    void fetchHealth().then(setState)
  }, [fetchHealth])

  useEffect(() => {
    let active = true
    const check = async () => {
      const result = await fetchHealth()
      if (active) setState(result)
    }

    void check()
    const interval = pollIntervalMs ? setInterval(check, pollIntervalMs) : undefined

    return () => {
      active = false
      if (interval) clearInterval(interval)
    }
  }, [fetchHealth, pollIntervalMs])

  return { ...state, refresh }
}
