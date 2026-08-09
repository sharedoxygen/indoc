import { createTheme, ThemeOptions } from '@mui/material/styles';

type PaletteMode = 'light' | 'dark';

// Modern business color palette
const brandColors = {
  primary: {
    50: '#e8f4fd',
    100: '#d1e9fb',
    200: '#a3d2f7',
    300: '#74bcf3',
    400: '#46a5ef',
    500: '#1976d2', // Main brand color - professional blue
    600: '#1565c0',
    700: '#0d47a1',
    800: '#0a3d91',
    900: '#063281',
  },
  secondary: {
    50: '#fff3e0',
    100: '#ffe7c1',
    200: '#ffcc82',
    300: '#ffb74d',
    400: '#ffa726',
    500: '#ff9800', // Accent color - warm orange
    600: '#f57c00',
    700: '#ef6c00',
    800: '#e65100',
    900: '#bf360c',
  },
  success: {
    50: '#e8f5e8',
    100: '#c8e6c9',
    200: '#a5d6a7',
    300: '#81c784',
    400: '#66bb6a',
    500: '#4caf50',
    600: '#43a047',
    700: '#388e3c',
    800: '#2e7d32',
    900: '#1b5e20',
  },
  error: {
    50: '#ffebee',
    100: '#ffcdd2',
    200: '#ef9a9a',
    300: '#e57373',
    400: '#ef5350',
    500: '#f44336',
    600: '#e53935',
    700: '#d32f2f',
    800: '#c62828',
    900: '#b71c1c',
  },
  warning: {
    50: '#fff8e1',
    100: '#ffecb3',
    200: '#ffe082',
    300: '#ffd54f',
    400: '#ffca28',
    500: '#ffc107',
    600: '#ffb300',
    700: '#ffa000',
    800: '#ff8f00',
    900: '#ff6f00',
  },
  neutral: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#eeeeee',
    300: '#e0e0e0',
    400: '#bdbdbd',
    500: '#9e9e9e',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121',
  }
};

const getDesignTokens = (mode: PaletteMode): ThemeOptions => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          // Light mode
          primary: {
            main: brandColors.primary[500],
            light: brandColors.primary[300],
            dark: brandColors.primary[700],
            contrastText: '#ffffff',
          },
          secondary: {
            main: brandColors.secondary[500],
            light: brandColors.secondary[300],
            dark: brandColors.secondary[700],
            contrastText: '#ffffff',
          },
          success: {
            main: brandColors.success[500],
            light: brandColors.success[300],
            dark: brandColors.success[700],
          },
          error: {
            main: brandColors.error[500],
            light: brandColors.error[300],
            dark: brandColors.error[700],
          },
          warning: {
            main: brandColors.warning[500],
            light: brandColors.warning[300],
            dark: brandColors.warning[700],
          },
          background: {
            default: '#f4f6f8',
            paper: '#ffffff',
          },
          text: {
            primary: brandColors.neutral[900],
            secondary: brandColors.neutral[600],
          },
          divider: brandColors.neutral[200],
        }
      : {
          // Dark mode
          primary: {
            main: brandColors.primary[400],
            light: brandColors.primary[300],
            dark: brandColors.primary[600],
            contrastText: '#ffffff',
          },
          secondary: {
            main: brandColors.secondary[400],
            light: brandColors.secondary[300],
            dark: brandColors.secondary[600],
            contrastText: '#ffffff',
          },
          success: {
            main: brandColors.success[400],
            light: brandColors.success[300],
            dark: brandColors.success[600],
          },
          error: {
            main: brandColors.error[400],
            light: brandColors.error[300],
            dark: brandColors.error[600],
          },
          warning: {
            main: brandColors.warning[400],
            light: brandColors.warning[300],
            dark: brandColors.warning[600],
          },
          background: {
            default: '#10141f',
            paper: '#1a1f31',
          },
          text: {
            primary: '#ffffff',
            secondary: brandColors.neutral[400],
          },
          divider: brandColors.neutral[700],
        }),
  },
  typography: {
    fontFamily: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: {
      fontSize: '1.875rem',
      fontWeight: 600,
      lineHeight: 1.2,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.3,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontSize: '1.25rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h4: {
      fontSize: '1.125rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h6: {
      fontSize: '0.9375rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    body1: {
      fontSize: '0.9375rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.8125rem',
      lineHeight: 1.5,
    },
    button: {
      fontWeight: 500,
      textTransform: 'none',
      letterSpacing: '0.02em',
    },
  },
  shape: {
    borderRadius: 6,
  },
  shadows: (mode === 'light' ? [
    'none',
    '0px 1px 2px rgba(0, 0, 0, 0.05)',
    '0px 1px 3px rgba(0, 0, 0, 0.1), 0px 1px 2px rgba(0, 0, 0, 0.06)',
    '0px 4px 6px -1px rgba(0, 0, 0, 0.1), 0px 2px 4px -1px rgba(0, 0, 0, 0.06)',
    '0px 10px 15px -3px rgba(0, 0, 0, 0.1), 0px 4px 6px -2px rgba(0, 0, 0, 0.05)',
    '0px 20px 25px -5px rgba(0, 0, 0, 0.1), 0px 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.25)',
  ] : [
    'none',
    '0px 1px 2px rgba(0, 0, 0, 0.3)',
    '0px 1px 3px rgba(0, 0, 0, 0.4), 0px 1px 2px rgba(0, 0, 0, 0.24)',
    '0px 4px 6px -1px rgba(0, 0, 0, 0.4), 0px 2px 4px -1px rgba(0, 0, 0, 0.24)',
    '0px 10px 15px -3px rgba(0, 0, 0, 0.4), 0px 4px 6px -2px rgba(0, 0, 0, 0.2)',
    '0px 20px 25px -5px rgba(0, 0, 0, 0.4), 0px 10px 10px -5px rgba(0, 0, 0, 0.16)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
    '0px 25px 50px -12px rgba(0, 0, 0, 0.6)',
  ]).slice(0, 25) as any,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: 4,
          padding: '8px 16px',
          fontSize: '0.8125rem',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.08)',
          },
        },
        contained: {
          '&:hover': {
            boxShadow: '0px 6px 16px rgba(0, 0, 0, 0.12)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: mode === 'dark' ? '1px solid rgba(255, 255, 255, 0.12)' : '1px solid rgba(0, 0, 0, 0.08)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: mode === 'light' 
            ? '0px 1px 3px rgba(0, 0, 0, 0.1), 0px 1px 2px rgba(0, 0, 0, 0.06)'
            : '0px 1px 3px rgba(0, 0, 0, 0.12), 0px 1px 2px rgba(0, 0, 0, 0.24)',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            transform: 'none',
            boxShadow: mode === 'light'
              ? '0px 2px 4px rgba(0, 0, 0, 0.08), 0px 1px 2px rgba(0, 0, 0, 0.06)'
              : '0px 2px 4px rgba(0, 0, 0, 0.2), 0px 1px 2px rgba(0, 0, 0, 0.12)',
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: mode === 'light' ? '#ffffff' : '#1a1d29',
          color: mode === 'light' ? brandColors.neutral[900] : '#ffffff',
          boxShadow: mode === 'light' 
            ? '0px 1px 3px rgba(0, 0, 0, 0.1), 0px 1px 2px rgba(0, 0, 0, 0.06)'
            : '0px 1px 3px rgba(0, 0, 0, 0.4), 0px 1px 2px rgba(0, 0, 0, 0.24)',
          backdropFilter: 'blur(8px)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: mode === 'light' ? '#ffffff' : '#1a1d29',
          borderRight: mode === 'light' ? '1px solid rgba(0, 0, 0, 0.08)' : '1px solid rgba(255, 255, 255, 0.12)',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          margin: '2px 6px',
          '&.Mui-selected': {
            backgroundColor: mode === 'light' ? brandColors.primary[50] : 'rgba(25, 118, 210, 0.12)',
            color: brandColors.primary[600],
            '&:hover': {
              backgroundColor: mode === 'light' ? brandColors.primary[100] : 'rgba(25, 118, 210, 0.16)',
            },
          },
          '&:hover': {
            backgroundColor: mode === 'light' ? brandColors.neutral[50] : 'rgba(255, 255, 255, 0.04)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          fontWeight: 500,
          fontSize: '0.75rem',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'filled',
      },
      styleOverrides: {
        root: {
          '--TextField-brandBorderColor': mode === 'dark' ? brandColors.primary[400] : brandColors.primary[500],
          '--TextField-brandBorderHoverColor': mode === 'dark' ? brandColors.primary[300] : brandColors.primary[600],
          '--TextField-brandBorderFocusedColor': mode === 'dark' ? brandColors.primary[300] : brandColors.primary[700],
          '& .MuiFilledInput-root': {
            borderRadius: 8,
            backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.09)' : 'rgba(0, 0, 0, 0.06)',
            '&:hover': {
              backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.13)' : 'rgba(0, 0, 0, 0.09)',
            },
            '&.Mui-focused': {
              backgroundColor: mode === 'dark' ? 'rgba(255, 255, 255, 0.13)' : 'rgba(0, 0, 0, 0.09)',
            },
            '&::before, &::after': {
              borderBottom: '2px solid var(--TextField-brandBorderColor)',
              transform: 'scaleX(0)',
              transition: 'transform 0.3s ease',
            },
            '&:hover::before, &:hover::after': {
              transform: 'scaleX(1)',
            },
            '&.Mui-focused::before, &.Mui-focused::after': {
              transform: 'scaleX(1)',
              borderColor: 'var(--TextField-brandBorderFocusedColor)',
            },
          },
          '& .MuiInputBase-input': {
            color: mode === 'dark' ? '#ffffff' : brandColors.neutral[900],
          },
          '& .MuiInputLabel-root': {
            color: mode === 'dark' ? brandColors.neutral[400] : brandColors.neutral[600],
          },
          '& .MuiInputLabel-root.Mui-focused': {
            color: mode === 'dark' ? brandColors.primary[300] : brandColors.primary[600],
          },
        },
      },
    },
  },
});

export const createAppTheme = (mode: PaletteMode) => createTheme(getDesignTokens(mode));

// Default light theme for backward compatibility
export const theme = createAppTheme('light');