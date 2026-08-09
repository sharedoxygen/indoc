import React from 'react';
import { Box, Typography, useTheme } from '@mui/material';
import { SvgIcon } from '@mui/material';

interface LogoProps {
    size?: 'small' | 'medium' | 'large';
    showText?: boolean;
    variant?: 'full' | 'icon' | 'text';
}

// Custom inDoc logo icon
const InDocIcon: React.FC<{ size?: number }> = ({ size = 24 }) => {
    const theme = useTheme();

    return (
        <SvgIcon
            viewBox="0 0 32 32"
            sx={{
                width: size,
                height: size,
                color: theme.palette.primary.main
            }}
        >
            {/* Document stack with modern geometric design */}
            <defs>
                <linearGradient id="docGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor={theme.palette.primary.main} />
                    <stop offset="100%" stopColor={theme.palette.primary.dark} />
                </linearGradient>
                <linearGradient id="accentGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor={theme.palette.secondary.main} />
                    <stop offset="100%" stopColor={theme.palette.secondary.dark} />
                </linearGradient>
            </defs>

            {/* Background document */}
            <rect x="4" y="6" width="20" height="24" rx="2" fill="url(#docGradient)" opacity="0.3" />

            {/* Middle document */}
            <rect x="6" y="4" width="20" height="24" rx="2" fill="url(#docGradient)" opacity="0.6" />

            {/* Front document */}
            <rect x="8" y="2" width="20" height="24" rx="2" fill="url(#docGradient)" />

            {/* Document lines */}
            <rect x="11" y="7" width="10" height="1.5" rx="0.75" fill="white" opacity="0.9" />
            <rect x="11" y="10" width="14" height="1.5" rx="0.75" fill="white" opacity="0.7" />
            <rect x="11" y="13" width="12" height="1.5" rx="0.75" fill="white" opacity="0.7" />
            <rect x="11" y="16" width="8" height="1.5" rx="0.75" fill="white" opacity="0.5" />

            {/* Accent dot (representing intelligence/AI) */}
            <circle cx="24" cy="8" r="3" fill="url(#accentGradient)" />
            <circle cx="24" cy="8" r="1.5" fill="white" />
        </SvgIcon>
    );
};

const Logo: React.FC<LogoProps> = ({
    size = 'medium',
    showText = true,
    variant = 'full'
}) => {
    const theme = useTheme();

    const sizeMap = {
        small: { icon: 24, text: '1.25rem' },
        medium: { icon: 32, text: '1.5rem' },
        large: { icon: 48, text: '2rem' },
    };

    const currentSize = sizeMap[size];

    if (variant === 'icon') {
        return <InDocIcon size={currentSize.icon} />;
    }

    if (variant === 'text') {
        return (
            <Typography
                variant="h6"
                sx={{
                    fontWeight: 700,
                    fontSize: currentSize.text,
                    background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    letterSpacing: '-0.02em',
                }}
            >
                inDoc
            </Typography>
        );
    }

    return (
        <Box
            sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
            }}
        >
            <InDocIcon size={currentSize.icon} />
            {showText && (
                <Typography
                    variant="h6"
                    sx={{
                        fontWeight: 700,
                        fontSize: currentSize.text,
                        background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                        backgroundClip: 'text',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        letterSpacing: '-0.02em',
                    }}
                >
                    inDoc
                </Typography>
            )}
        </Box>
    );
};

export default Logo;
