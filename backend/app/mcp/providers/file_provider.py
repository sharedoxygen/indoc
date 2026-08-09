"""
File Provider for MCP - Handles file operations
"""
from typing import Dict, Any, List, Optional
import os
import hashlib
from pathlib import Path
import aiofiles
import magic

from app.models.document import Document
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.services.document_processor import DocumentProcessor
from sqlalchemy import select


class FileProvider:
    """Provider for file-related tools"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
    
    async def read_file(
        self,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Read the content of a document
        
        Args:
            document_id: Document ID
            context: Optional context
        
        Returns:
            Document content
        """
        async with AsyncSessionLocal() as session:
            # Get document
            result = await session.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Read file content
            file_path = Path(document.storage_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {document.storage_path}")
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Get MIME type
            mime_type = magic.from_buffer(content, mime=True)
            
            return {
                "document_id": str(document.uuid),
                "filename": document.filename,
                "file_type": document.file_type,
                "mime_type": mime_type,
                "size": len(content),
                "content": content.decode('utf-8', errors='ignore') if mime_type.startswith('text/') else None,
                "binary": not mime_type.startswith('text/')
            }
    
    async def extract_text(
        self,
        document_id: str,
        page_range: Optional[List[int]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract text from a document
        
        Args:
            document_id: Document ID
            page_range: Optional page range [start, end]
            context: Optional context
        
        Returns:
            Extracted text
        """
        async with AsyncSessionLocal() as session:
            # Get document
            result = await session.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Extract text based on file type
            file_path = Path(document.storage_path)
            extracted = await self.document_processor.extract_text(
                file_path,
                file_type=document.file_type,
                page_range=page_range
            )
            
            return {
                "document_id": str(document.uuid),
                "text": extracted["text"],
                "pages": extracted.get("pages", []),
                "metadata": extracted.get("metadata", {}),
                "tables": extracted.get("tables", []),
                "images": extracted.get("images", [])
            }
    
    async def save_file(
        self,
        filename: str,
        content: bytes,
        file_type: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a new file
        
        Args:
            filename: File name
            content: File content
            file_type: File type/extension
            user_id: User ID
            context: Optional context
        
        Returns:
            Saved file information
        """
        # Generate file hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Create storage path
        storage_dir = settings.STORAGE_PATH / file_hash[:2] / file_hash[2:4]
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / f"{file_hash}.{file_type}"
        
        # Save file
        async with aiofiles.open(storage_path, 'wb') as f:
            await f.write(content)
        
        # Create database entry
        async with AsyncSessionLocal() as session:
            document = Document(
                filename=filename,
                file_type=file_type,
                file_size=len(content),
                file_hash=file_hash,
                storage_path=str(storage_path),
                status="pending",
                uploaded_by=user_id
            )
            
            session.add(document)
            await session.commit()
            
            return {
                "document_id": str(document.uuid),
                "filename": filename,
                "file_type": file_type,
                "file_size": len(content),
                "file_hash": file_hash,
                "status": "saved"
            }
    
    async def delete_file(
        self,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            document_id: Document ID
            context: Optional context
        
        Returns:
            Deletion status
        """
        async with AsyncSessionLocal() as session:
            # Get document
            result = await session.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Delete physical file
            file_path = Path(document.storage_path)
            if file_path.exists():
                file_path.unlink()
            
            # Delete from database
            await session.delete(document)
            await session.commit()
            
            return {
                "document_id": document_id,
                "status": "deleted"
            }
    
    async def get_file_info(
        self,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get file information without reading content
        
        Args:
            document_id: Document ID
            context: Optional context
        
        Returns:
            File information
        """
        async with AsyncSessionLocal() as session:
            # Get document
            result = await session.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Get file stats
            file_path = Path(document.storage_path)
            if file_path.exists():
                stats = file_path.stat()
                exists = True
            else:
                stats = None
                exists = False
            
            return {
                "document_id": str(document.uuid),
                "filename": document.filename,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "file_hash": document.file_hash,
                "exists": exists,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "status": document.status,
                "storage_path": document.storage_path if context and context.get("show_path") else None
            }