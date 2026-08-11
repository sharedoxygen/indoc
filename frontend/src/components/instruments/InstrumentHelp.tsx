import React from 'react'
import { Box, Divider, Stack, Tooltip, Typography } from '@mui/material'
import type { TooltipProps } from '@mui/material/Tooltip'

export type InstrumentHelpDetail = { label: string; value: string }

/** Structured hover content for meters, dials, and tickers. */
export type InstrumentHelpContent = {
  title: string
  body: string
  /** Live reading shown at top of the tip (e.g. "73% · active"). */
  reading?: string
  details?: InstrumentHelpDetail[]
  footer?: string
}

export type InstrumentHelpProp = string | InstrumentHelpContent

function normalizeHelp(help: InstrumentHelpProp): InstrumentHelpContent {
  if (typeof help === 'string') {
    return { title: 'Instrument', body: help }
  }
  return help
}

export function InstrumentHelpBody({ help }: { help: InstrumentHelpProp }) {
  const h = normalizeHelp(help)
  return (
    <Box sx={{ maxWidth: 320, p: 0.25 }}>
      <Typography
        sx={{
          fontWeight: 750,
          fontSize: 12,
          letterSpacing: 0.6,
          textTransform: 'uppercase',
          mb: 0.35,
        }}
      >
        {h.title}
      </Typography>
      {h.reading && (
        <Typography
          sx={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontVariantNumeric: 'tabular-nums',
            fontWeight: 650,
            fontSize: 13,
            mb: 0.75,
            color: 'primary.light',
          }}
        >
          {h.reading}
        </Typography>
      )}
      <Typography sx={{ fontSize: 12.5, lineHeight: 1.45, color: 'rgba(255,255,255,0.88)' }}>
        {h.body}
      </Typography>
      {h.details && h.details.length > 0 && (
        <>
          <Divider sx={{ my: 1, borderColor: 'rgba(255,255,255,0.12)' }} />
          <Stack spacing={0.45}>
            {h.details.map((d) => (
              <Box
                key={d.label}
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto',
                  gap: 1.5,
                  alignItems: 'baseline',
                }}
              >
                <Typography sx={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', fontWeight: 600 }}>
                  {d.label}
                </Typography>
                <Typography
                  sx={{
                    fontSize: 11.5,
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    fontVariantNumeric: 'tabular-nums',
                    color: 'rgba(255,255,255,0.92)',
                  }}
                >
                  {d.value}
                </Typography>
              </Box>
            ))}
          </Stack>
        </>
      )}
      {h.footer && (
        <Typography sx={{ mt: 1, fontSize: 11, color: 'rgba(255,255,255,0.5)', lineHeight: 1.4 }}>
          {h.footer}
        </Typography>
      )}
    </Box>
  )
}

type InstrumentTooltipProps = {
  help?: InstrumentHelpProp | null
  children: React.ReactElement
  placement?: TooltipProps['placement']
  enterDelay?: number
}

/** Wraps any instrument face with a rich hover tip. No-op when help is empty. */
export function InstrumentTooltip({
  help,
  children,
  placement = 'top',
  enterDelay = 280,
}: InstrumentTooltipProps) {
  if (!help) return children
  return (
    <Tooltip
      arrow
      placement={placement}
      enterDelay={enterDelay}
      enterNextDelay={120}
      describeChild
      title={<InstrumentHelpBody help={help} />}
      slotProps={{
        tooltip: {
          sx: {
            bgcolor: 'rgba(12, 16, 22, 0.96)',
            border: '1px solid rgba(255,255,255,0.12)',
            boxShadow: '0 10px 28px rgba(0,0,0,0.45)',
            maxWidth: 340,
            px: 1.25,
            py: 1,
          },
        },
        arrow: {
          sx: { color: 'rgba(12, 16, 22, 0.96)' },
        },
      }}
    >
      {children}
    </Tooltip>
  )
}
