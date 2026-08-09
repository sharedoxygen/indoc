import React from 'react'
import { SvgIconProps } from '@mui/material/SvgIcon'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import DescriptionIcon from '@mui/icons-material/Description'
import TableChartIcon from '@mui/icons-material/TableChart'
import SlideshowIcon from '@mui/icons-material/Slideshow'
import TextSnippetIcon from '@mui/icons-material/TextSnippet'
import ImageIcon from '@mui/icons-material/Image'
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile'

type Props = { fileType?: string; iconProps?: SvgIconProps }

const typeToIcon: Record<string, React.ElementType> = {
    pdf: PictureAsPdfIcon,
    doc: DescriptionIcon,
    docx: DescriptionIcon,
    xls: TableChartIcon,
    xlsx: TableChartIcon,
    ppt: SlideshowIcon,
    pptx: SlideshowIcon,
    txt: TextSnippetIcon,
    md: TextSnippetIcon,
    csv: TableChartIcon,
    png: ImageIcon,
    jpg: ImageIcon,
    jpeg: ImageIcon,
    gif: ImageIcon,
}

const typeToColor: Record<string, string> = {
    pdf: '#EF4444',
    doc: '#2563EB',
    docx: '#2563EB',
    xls: '#16A34A',
    xlsx: '#16A34A',
    ppt: '#F59E0B',
    pptx: '#F59E0B',
    txt: '#64748B',
    md: '#64748B',
    csv: '#22C55E',
    png: '#06B6D4',
    jpg: '#06B6D4',
    jpeg: '#06B6D4',
    gif: '#06B6D4',
}

export const getFileColor = (fileType?: string): string => {
    const key = (fileType || '').toLowerCase()
    return typeToColor[key] || '#8B5CF6'
}

const FileTypeIcon: React.FC<Props> = ({ fileType, iconProps }) => {
    const key = (fileType || '').toLowerCase()
    const Icon = typeToIcon[key] || InsertDriveFileIcon
    return <Icon {...iconProps} />
}

export default FileTypeIcon



