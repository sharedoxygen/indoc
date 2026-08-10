export type InstrumentStatus = 'idle' | 'ok' | 'warn' | 'error' | 'active'

export interface InstrumentBaseProps {
  value: number
  max?: number
  min?: number
  label?: string
  unit?: string
  precision?: number
  size?: number
  status?: InstrumentStatus
  animate?: boolean
  color?: string
}
