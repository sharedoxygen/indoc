"""
Data Integrity API Endpoints

Endpoints for monitoring and managing data consistency across
PostgreSQL, Elasticsearch, and Qdrant.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.api.deps import require_admin
from app.tasks.integrity import check_data_integrity, auto_repair_integrity

router = APIRouter()


@router.get("/check")
async def run_integrity_check(
    current_user: User = Depends(require_admin)
) -> Any:
    """
    Manually trigger a data integrity check (Admin only).
    
    Verifies consistency across:
    - PostgreSQL (source of truth)
    - Elasticsearch (keyword search)
    - Qdrant (vector search)
    
    Returns:
        Integrity report with counts, issues, and warnings
    """
    # Run synchronously and return results
    result = check_data_integrity()
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity check failed: {result.get('error')}"
        )
    
    return result


@router.post("/repair")
async def run_integrity_repair(
    current_user: User = Depends(require_admin)
) -> Any:
    """
    Manually trigger automatic integrity repair (Admin only).
    
    Repair actions:
    - Re-queue documents marked 'indexed' but missing search IDs
    - Mark documents as 'failed' if stuck in processing >1 hour
    
    Returns:
        Report of actions taken
    """
    # Run repair synchronously
    result = auto_repair_integrity()
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-repair failed: {result.get('error')}"
        )
    
    return result


@router.get("/status")
async def get_integrity_status(
    current_user: User = Depends(require_admin)
) -> Any:
    """
    Get a quick overview of data integrity status (Admin only).
    
    Returns:
        Quick status summary without detailed checks
    """
    from sqlalchemy import select, func
    from app.db.session import AsyncSessionLocal
    from app.models.document import Document
    from app.services.search.elasticsearch_service import get_elasticsearch_service
    from app.services.search.qdrant_service import get_qdrant_service

    async with AsyncSessionLocal() as db:
        # PostgreSQL counts
        pg_total = (await db.execute(select(func.count(Document.uuid)))).scalar()
        pg_indexed = (await db.execute(
            select(func.count(Document.uuid)).where(Document.status == 'indexed')
        )).scalar()
        pg_stored = (await db.execute(
            select(func.count(Document.uuid)).where(Document.status == 'stored')
        )).scalar()
        
        # Elasticsearch count
        es = get_elasticsearch_service()
        es_total = await es.count_documents()

        # Qdrant count
        qdrant = get_qdrant_service()
        qdrant_info = qdrant.collection_info()
        qdrant_total = qdrant_info.get('vectors_count', 0)
        
        # Simple status determination
        expected_es = pg_indexed + pg_stored
        is_healthy = (es_total == expected_es) and (qdrant_total == pg_indexed)
        
        return {
            "status": "healthy" if is_healthy else "warning",
            "postgresql": {
                "total": pg_total,
                "indexed": pg_indexed,
                "stored": pg_stored
            },
            "elasticsearch": {
                "total": es_total,
                "expected": expected_es,
                "aligned": es_total == expected_es
            },
            "qdrant": {
                "vectors": qdrant_total,
                "expected": pg_indexed,
                "aligned": qdrant_total == pg_indexed
            }
        }

