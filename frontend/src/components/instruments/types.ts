import type { InstrumentHelpProp } from './InstrumentHelp'

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
  /** Rich hover help (title/body/reading/details). Plain string also accepted. */
  help?: InstrumentHelpProp
}
