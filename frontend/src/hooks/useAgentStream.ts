import { useCallback, useRef, useState } from 'react'
import { TokenManager } from '../services/tokenManager'

export interface AgentStep {
  step: number
  thought: string
  action: string
  action_input: Record<string, unknown>
  observation: string
}

export type AgentStreamStatus = 'idle' | 'connecting' | 'running' | 'completed' | 'error'
export type AgentPhase = 'idle' | 'connecting' | 'planning' | 'tool' | 'completed' | 'error'

export interface AgentStreamState {
  status: AgentStreamStatus
  phase: AgentPhase
  goal: string
  tools: string[]
  steps: AgentStep[]
  finalAnswer: string | null
  iterations: number
  stoppedReason: string | null
  error: string | null
  maxSteps: number
  holding: boolean
  activeAction: string | null
  activeThought: string | null
  planningStep: number
  startedAt: number | null
}

const initialState: AgentStreamState = {
  status: 'idle',
  phase: 'idle',
  goal: '',
  tools: [],
  steps: [],
  finalAnswer: null,
  iterations: 0,
  stoppedReason: null,
  error: null,
  maxSteps: 6,
  holding: false,
  activeAction: null,
  activeThought: null,
  planningStep: 0,
  startedAt: null,
}

export function useAgentStream() {
  const [state, setState] = useState<AgentStreamState>(initialState)
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setState(initialState)
  }, [])

  const run = useCallback(
    async (params: { goal: string; documentIds?: string[]; maxSteps?: number }) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      const maxSteps = params.maxSteps ?? 6
      setState({
        ...initialState,
        status: 'connecting',
        phase: 'connecting',
        goal: params.goal,
        maxSteps,
        holding: true,
        startedAt: Date.now(),
      })

      const token = TokenManager.getToken()
      try {
        const response = await fetch('/api/v1/agent/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            goal: params.goal,
            document_ids: params.documentIds?.length ? params.documentIds : null,
            max_steps: maxSteps,
          }),
          signal: controller.signal,
        })

        if (!response.ok || !response.body) {
          const text = await response.text().catch(() => '')
          throw new Error(text || `Agent stream failed (${response.status})`)
        }

        setState((prev) => ({ ...prev, status: 'running', phase: 'planning', holding: true }))

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const chunks = buffer.split('\n\n')
          buffer = chunks.pop() || ''

          for (const chunk of chunks) {
            const lines = chunk.split('\n')
            for (const line of lines) {
              if (!line.startsWith('data:')) continue
              const payload = line.slice(5).trim()
              if (!payload) continue
              let event: any
              try {
                event = JSON.parse(payload)
              } catch {
                continue
              }

              if (event.type === 'start') {
                setState((prev) => ({
                  ...prev,
                  status: 'running',
                  phase: 'planning',
                  tools: event.tools_available || [],
                  goal: event.goal || prev.goal,
                  holding: true,
                  planningStep: 1,
                }))
              } else if (event.type === 'planning') {
                setState((prev) => ({
                  ...prev,
                  status: 'running',
                  phase: 'planning',
                  holding: true,
                  planningStep: event.step || prev.planningStep + 1,
                  activeAction: null,
                  activeThought: null,
                }))
              } else if (event.type === 'tool_start') {
                setState((prev) => ({
                  ...prev,
                  status: 'running',
                  phase: 'tool',
                  holding: true,
                  planningStep: event.step || prev.planningStep,
                  activeAction: event.action || null,
                  activeThought: event.thought || null,
                }))
              } else if (event.type === 'step') {
                const step: AgentStep = {
                  step: event.step,
                  thought: event.thought || '',
                  action: event.action || '',
                  action_input: event.action_input || {},
                  observation: event.observation || '',
                }
                setState((prev) => ({
                  ...prev,
                  steps: [...prev.steps, step],
                  holding: true,
                  phase: 'planning',
                  activeAction: step.action,
                  activeThought: step.thought,
                }))
              } else if (event.type === 'final') {
                setState((prev) => ({
                  ...prev,
                  status: 'completed',
                  phase: 'completed',
                  finalAnswer: event.final_answer || '',
                  iterations: event.iterations || prev.steps.length,
                  stoppedReason: event.stopped_reason || 'completed',
                  holding: false,
                  activeAction: 'finish',
                }))
              } else if (event.type === 'error') {
                setState((prev) => ({
                  ...prev,
                  status: 'error',
                  phase: 'error',
                  error: event.message || 'Agent error',
                  holding: false,
                }))
              }
            }
          }
        }

        setState((prev) => {
          if (prev.status === 'running') {
            return {
              ...prev,
              status: 'completed',
              phase: 'completed',
              holding: false,
              stoppedReason: prev.stoppedReason || 'stream_ended',
            }
          }
          return { ...prev, holding: false }
        })
      } catch (err: any) {
        if (err?.name === 'AbortError') return
        setState((prev) => ({
          ...prev,
          status: 'error',
          phase: 'error',
          error: err?.message || 'Failed to run agent',
          holding: false,
        }))
      }
    },
    []
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setState((prev) => ({
      ...prev,
      status: prev.finalAnswer ? 'completed' : 'idle',
      phase: prev.finalAnswer ? 'completed' : 'idle',
      holding: false,
    }))
  }, [])

  return { ...state, run, reset, stop }
}
