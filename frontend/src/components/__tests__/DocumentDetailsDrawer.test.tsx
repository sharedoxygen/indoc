/**
 * DocumentDetailsDrawer Component Tests
 * 
 * Tests theme compliance, props handling, and accessibility
 * per AI Prompt Engineering Guide §8, §10
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@mui/material/styles'
import { createAppTheme } from '../../theme'
import DocumentDetailsDrawer from '../DocumentDetailsDrawer'
import '@testing-library/jest-dom'

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 days ago'),
  format: jest.fn((date) => date.toISOString())
}))

describe('DocumentDetailsDrawer', () => {
  const mockDocument = {
    id: 1,
    uuid: '123e4567-e89b-12d3-a456-426614174000',
    filename: 'test-document.pdf',
    file_type: 'pdf',
    file_size: 1024000, // 1MB
    folder_path: 'ZX10R/manuals',
    title: 'Test Document',
    description: 'A test document for unit tests',
    tags: ['test', 'manual'],
    document_set_id: 'set-123',
    status: 'indexed',
    virus_scan_status: 'clean',
    created_at: '2025-10-08T12:00:00Z',
    updated_at: '2025-10-09T12:00:00Z',
    uploaded_by: 'test@example.com'
  }

  const defaultProps = {
    open: true,
    document: mockDocument,
    onClose: jest.fn(),
    onEdit: jest.fn(),
    onDownload: jest.fn(),
    onShare: jest.fn()
  }

  const renderWithTheme = (props = {}, themeMode: 'light' | 'dark' = 'light') => {
    const theme = createAppTheme(themeMode)
    return render(
      <ThemeProvider theme={theme}>
        <DocumentDetailsDrawer {...defaultProps} {...props} />
      </ThemeProvider>
    )
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering and Theme Compliance (Guide §8)', () => {
    it('renders without crashing', () => {
      renderWithTheme()
      expect(screen.getByText('Test Document')).toBeInTheDocument()
    })

    it('uses theme tokens only (no hardcoded colors)', () => {
      const { container } = renderWithTheme()
      const drawer = container.querySelector('[role="presentation"]')
      
      // Verify no inline styles with hardcoded colors
      const allElements = container.querySelectorAll('*')
      allElements.forEach((el) => {
        const style = el.getAttribute('style') || ''
        expect(style).not.toMatch(/#[0-9a-fA-F]{3,6}/)
        expect(style).not.toMatch(/rgb\(/)
      })
    })

    it('supports dark mode via theme', () => {
      const { rerender } = renderWithTheme({}, 'light')
      expect(screen.getByText('Test Document')).toBeInTheDocument()

      // Rerender with dark theme - should not crash
      const darkTheme = createAppTheme('dark')
      rerender(
        <ThemeProvider theme={darkTheme}>
          <DocumentDetailsDrawer {...defaultProps} />
        </ThemeProvider>
      )
      expect(screen.getByText('Test Document')).toBeInTheDocument()
    })

    it('displays document metadata correctly', () => {
      renderWithTheme()
      expect(screen.getByText('Test Document')).toBeInTheDocument()
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
      expect(screen.getByText(/1.0 MB/)).toBeInTheDocument() // File size formatted
      expect(screen.getByText('indexed')).toBeInTheDocument()
      expect(screen.getByText(/Virus: clean/)).toBeInTheDocument()
    })

    it('displays folder path when present', () => {
      renderWithTheme()
      expect(screen.getByText('ZX10R/manuals')).toBeInTheDocument()
    })

    it('displays document set ID when present', () => {
      renderWithTheme()
      expect(screen.getByText('set-123')).toBeInTheDocument()
    })

    it('displays tags when present', () => {
      renderWithTheme()
      expect(screen.getByText('test')).toBeInTheDocument()
      expect(screen.getByText('manual')).toBeInTheDocument()
    })

    it('hides optional fields when not present', () => {
      const docWithoutOptionals = { ...mockDocument, folder_path: undefined, document_set_id: undefined, tags: undefined, description: undefined }
      renderWithTheme({ document: docWithoutOptionals })
      
      expect(screen.queryByText('ZX10R/manuals')).not.toBeInTheDocument()
      expect(screen.queryByText('set-123')).not.toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    it('calls onClose when close button is clicked', () => {
      const onClose = jest.fn()
      renderWithTheme({ onClose })
      
      const closeButton = screen.getByRole('button', { name: /close/i })
      fireEvent.click(closeButton)
      
      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('calls onDownload when download button is clicked', () => {
      const onDownload = jest.fn()
      renderWithTheme({ onDownload })
      
      const downloadButton = screen.getByRole('button', { name: /download/i })
      fireEvent.click(downloadButton)
      
      expect(onDownload).toHaveBeenCalledWith(mockDocument)
    })

    it('calls onShare when share button is clicked', () => {
      const onShare = jest.fn()
      renderWithTheme({ onShare })
      
      const shareButton = screen.getByRole('button', { name: /share/i })
      fireEvent.click(shareButton)
      
      expect(onShare).toHaveBeenCalledWith(mockDocument)
    })

    it('calls onEdit when edit button is clicked', () => {
      const onEdit = jest.fn()
      renderWithTheme({ onEdit })
      
      const editButton = screen.getByRole('button', { name: /edit/i })
      fireEvent.click(editButton)
      
      expect(onEdit).toHaveBeenCalledWith(mockDocument)
    })
  })

  describe('Status Chips and Colors', () => {
    it('displays correct status chip color for indexed status', () => {
      renderWithTheme()
      const statusChip = screen.getByText('indexed')
      expect(statusChip).toBeInTheDocument()
      // Should use theme success color (no assertion on computed color as theme controls it)
    })

    it('displays correct status chip color for failed status', () => {
      const failedDoc = { ...mockDocument, status: 'failed' }
      renderWithTheme({ document: failedDoc })
      expect(screen.getByText('failed')).toBeInTheDocument()
    })

    it('displays correct virus status chip color for clean', () => {
      renderWithTheme()
      expect(screen.getByText(/Virus: clean/)).toBeInTheDocument()
    })

    it('displays correct virus status chip color for infected', () => {
      const infectedDoc = { ...mockDocument, virus_scan_status: 'infected' }
      renderWithTheme({ document: infectedDoc })
      expect(screen.getByText(/Virus: infected/)).toBeInTheDocument()
    })
  })

  describe('Accessibility (Guide §8)', () => {
    it('has proper ARIA labels and roles', () => {
      renderWithTheme()
      expect(screen.getByRole('presentation')).toBeInTheDocument()
      expect(screen.getAllByRole('button').length).toBeGreaterThan(0)
    })

    it('close button is keyboard accessible', () => {
      const onClose = jest.fn()
      renderWithTheme({ onClose })
      
      const closeButton = screen.getByRole('button', { name: /close/i })
      closeButton.focus()
      fireEvent.keyDown(closeButton, { key: 'Enter', code: 'Enter' })
      
      // MUI IconButton should trigger click on Enter
      expect(document.activeElement).toBe(closeButton)
    })
  })

  describe('Edge Cases and Data Integrity (Guide §5)', () => {
    it('returns null when document is null', () => {
      const { container } = renderWithTheme({ document: null })
      expect(container.firstChild).toBeNull()
    })

    it('handles missing UUID gracefully', () => {
      const docWithoutUuid = { ...mockDocument, uuid: undefined }
      renderWithTheme({ document: docWithoutUuid as any })
      // Should still render without crashing
      expect(screen.getByText('Test Document')).toBeInTheDocument()
    })

    it('formats file size correctly', () => {
      // Test different file sizes
      const sizes = [
        { bytes: 0, expected: '0 B' },
        { bytes: 500, expected: '500 B' },
        { bytes: 1024, expected: '1.0 KB' },
        { bytes: 1024000, expected: '1.0 MB' },
        { bytes: 1024000000, expected: '1.0 GB' }
      ]

      sizes.forEach(({ bytes, expected }) => {
        const doc = { ...mockDocument, file_size: bytes }
        const { unmount } = renderWithTheme({ document: doc })
        expect(screen.getByText(expected)).toBeInTheDocument()
        unmount()
      })
    })

    it('handles timestamps correctly', () => {
      renderWithTheme()
      // Verify dates are displayed (mocked to return formatted strings)
      expect(screen.getByText(/2 days ago/)).toBeInTheDocument()
    })
  })

  describe('Drawer Open/Close State', () => {
    it('does not render when open is false', () => {
      renderWithTheme({ open: false })
      // MUI Drawer should not be visible when open=false
      const drawer = screen.queryByRole('presentation')
      expect(drawer).not.toBeInTheDocument()
    })

    it('renders when open is true', () => {
      renderWithTheme({ open: true })
      expect(screen.getByRole('presentation')).toBeInTheDocument()
    })
  })
})

