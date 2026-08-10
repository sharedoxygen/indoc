import { useTheme } from '@mui/material'
import type { InstrumentStatus } from './types'

export function useInstrumentColor(status?: InstrumentStatus, override?: string) {
  const theme = useTheme()
  if (override) return override
  switch (status) {
    case 'ok':
      return theme.palette.success.main
    case 'warn':
      return theme.palette.warning.main
    case 'error':
      return theme.palette.error.main
    case 'active':
      return theme.palette.info.main
    default:
      return theme.palette.primary.main
  }
}

export function clampRatio(value: number, min = 0, max = 100) {
  if (!Number.isFinite(value)) return 0
  if (max === min) return 0
  return Math.min(1, Math.max(0, (value - min) / (max - min)))
}

export function formatInstrumentValue(value: number, precision = 1, unit = '') {
  const n = Number.isFinite(value) ? value : 0
  const formatted = n.toFixed(precision)
  return unit ? `${formatted}${unit}` : formatted
}
