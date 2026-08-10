import React from 'react'
import { Box, Tooltip, Typography } from '@mui/material'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'

interface HelpTipProps {
  title: React.ReactNode
  children?: React.ReactNode
  /** Show a small info icon next to children (default true when children provided) */
  showIcon?: boolean
  placement?: 'top' | 'bottom' | 'left' | 'right'
  /** When true, children get a dashed underline + help cursor */
  underline?: boolean
}

/**
 * Hover help wrapper. Use around labels, gauges, and controls that need
 * plain-language explanation without cluttering the layout.
 */
export const HelpTip: React.FC<HelpTipProps> = ({
  title,
  children,
  showIcon,
  placement = 'top',
  underline = true,
}) => {
  const withIcon = showIcon ?? Boolean(children)
  return (
    <Tooltip
      title={
        typeof title === 'string' ? (
          <Typography variant="body2" sx={{ maxWidth: 280, lineHeight: 1.45, p: 0.25 }}>
            {title}
          </Typography>
        ) : (
          title
        )
      }
      arrow
      placement={placement}
      enterDelay={200}
    >
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.4,
          cursor: 'help',
          verticalAlign: 'middle',
          ...(underline && children
            ? {
                borderBottom: '1px dashed',
                borderColor: 'divider',
              }
            : null),
        }}
      >
        {children}
        {withIcon && (
          <InfoOutlinedIcon
            sx={{ fontSize: 14, color: 'text.disabled', flexShrink: 0 }}
            aria-hidden
          />
        )}
      </Box>
    </Tooltip>
  )
}

export default HelpTip
