"""
Database Provider for MCP - Handles database operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.document import Document
from app.models.metadata import Metadata, Annotation
from app.models.audit import AuditLog
from app.db.session import AsyncSessionLocal
from app.core.security import field_encryption


class DatabaseProvider:
    """Provider for database-related tools"""
    
    async def get_metadata(
        self,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve metadata for a document
        
        Args:
            document_id: Document ID
            context: Optional context
        
        Returns:
            Document metadata
        """
        async with AsyncSessionLocal() as session:
            # Get document
            result = await session.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Get metadata entries
            metadata_result = await session.execute(
                select(Metadata).where(Metadata.document_id == document.id)
            )
            metadata_entries = metadata_result.scalars().all()
            
            # Format metadata
            metadata = {
                "document_id": str(document.uuid),
                "filename": document.filename,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "status": document.status,
                "title": document.title,
                "description": document.description,
                "tags": document.tags or [],
                "custom_metadata": document.custom_metadata or {},
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat()
            }
            
            # Add metadata entries
            for entry in metadata_entries:
                value = entry.value
                if entry.is_encrypted:
                    value = field_encryption.decrypt(value)
                metadata[entry.key] = value
            
            return metadata
    
    async def update_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update metadata for a document
        
        Args:
            document_id: Document ID
            metadata: Metadata to update
            context: Optional context
        
        Returns:
            Updated metadata
        """
        async with AsyncSessionLocal() as session:
            # Get document
            result = await session.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Update document fields
            update_fields = {}
            if "title" in metadata:
                update_fields["title"] = metadata["title"]
            if "description" in metadata:
                update_fields["description"] = metadata["description"]
            if "tags" in metadata:
                update_fields["tags"] = metadata["tags"]
            
            if update_fields:
                await session.execute(
                    update(Document)
                    .where(Document.id == document.id)
                    .values(**update_fields)
                )
            
            # Update custom metadata
            if "custom_metadata" in metadata:
                document.custom_metadata = {
                    **(document.custom_metadata or {}),
                    **metadata["custom_metadata"]
                }
            
            await session.commit()
            
            return {"status": "success", "document_id": document_id}