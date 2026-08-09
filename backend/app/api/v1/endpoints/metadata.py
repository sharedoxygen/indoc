"""
Metadata management endpoints
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document

router = APIRouter()


@router.get("/document/{document_id}")
async def get_document_metadata(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get metadata for a specific document"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {
        "id": str(document.id),
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "metadata": document.metadata or {}
    }


@router.put("/document/{document_id}")
async def update_document_metadata(
    document_id: str,
    metadata: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update metadata for a document"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update metadata
    if not document.metadata:
        document.metadata = {}
    document.metadata.update(metadata)
    
    await db.commit()
    await db.refresh(document)
    
    return {
        "status": "success",
        "message": "Metadata updated successfully",
        "metadata": document.metadata
    }


@router.get("/tags")
async def get_all_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """Get all unique tags from documents"""
    # Simplified implementation - would need proper tag management
    return ["contract", "invoice", "report", "presentation", "email"]


@router.post("/document/{document_id}/tags")
async def add_document_tags(
    document_id: str,
    tags: List[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Add tags to a document"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Add tags to metadata
    if not document.metadata:
        document.metadata = {}
    
    existing_tags = document.metadata.get("tags", [])
    new_tags = list(set(existing_tags + tags))
    document.metadata["tags"] = new_tags
    
    await db.commit()
    
    return {
        "status": "success",
        "tags": new_tags
    }