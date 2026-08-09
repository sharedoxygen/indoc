"""
Reindexing endpoints for fixing broken document indexes

Critical for fixing documents marked 'indexed' but not actually in ES/Weaviate
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.document import Document
from app.core.security import require_admin

router = APIRouter()


@router.post("/document/{document_uuid}/reindex")
async def reindex_document(
    document_uuid: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reindex a single document in Elasticsearch and Weaviate"""
    from uuid import UUID
    from app.tasks.document import process_document
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.uuid == UUID(document_uuid))
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_uuid} not found"
        )
    
    # Trigger reindexing task
    task = process_document.delay(document_uuid)
    
    return {
        "message": f"Reindexing {document.filename}",
        "task_id": task.id,
        "document_uuid": document_uuid
    }


@router.post("/reindex-all-broken")
async def reindex_all_broken_documents(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Reindex all documents marked 'indexed' but missing elasticsearch_id or qdrant_id
    
    Fixes documents that were incorrectly marked as indexed
    """
    from app.tasks.document import process_document
    
    # Find broken documents
    result = await db.execute(
        select(Document).where(
            (Document.status == "indexed") &
            ((Document.elasticsearch_id.is_(None)) | (Document.qdrant_id.is_(None)))
        ).limit(100)
    )
    broken_docs = result.scalars().all()
    
    if not broken_docs:
        return {
            "message": "No broken documents found",
            "count": 0
        }
    
    # Queue reindexing tasks
    task_ids = []
    for doc in broken_docs:
        task = process_document.delay(str(doc.uuid))
        task_ids.append({
            "document_uuid": str(doc.uuid),
            "filename": doc.filename,
            "task_id": task.id
        })
    
    return {
        "message": f"Queued {len(task_ids)} documents for reindexing",
        "count": len(task_ids),
        "tasks": task_ids
    }

