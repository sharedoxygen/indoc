"""
Business metrics endpoint for Grafana
Exposes business-relevant data in Prometheus format
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document
from app.core.monitoring import (
    documents_by_classification,
    documents_by_type,
    users_by_role,
    storage_usage_by_type
)

router = APIRouter()


@router.get("/update-business-metrics")
async def update_business_metrics(db: AsyncSession = Depends(get_db)):
    """Update business metrics gauges from database"""
    
    # Documents by classification  
    result = await db.execute(
        select(
            Document.classification,
            func.count(Document.id).label('count')
        ).group_by(Document.classification)
    )
    for row in result.all():
        classification_str = row.classification.value if hasattr(row.classification, 'value') else str(row.classification) if row.classification else 'Unclassified'
        documents_by_classification.labels(classification=classification_str).set(row.count)
    
    # Documents by type
    result = await db.execute(
        select(
            Document.file_type,
            func.count(Document.id).label('count')
        ).where(Document.file_type.isnot(None))
        .group_by(Document.file_type)
    )
    for row in result.all():
        documents_by_type.labels(file_type=row.file_type).set(row.count)
    
    # Users by role
    result = await db.execute(
        select(
            User.role,
            func.count(User.id).label('count')
        ).group_by(User.role)
    )
    for row in result.all():
        role_str = row.role.value if hasattr(row.role, 'value') else str(row.role)
        users_by_role.labels(role=role_str).set(row.count)
    
    # Storage by type
    result = await db.execute(
        select(
            Document.file_type,
            func.sum(Document.file_size).label('total_size')
        ).where(Document.file_type.isnot(None))
        .group_by(Document.file_type)
    )
    for row in result.all():
        if row.total_size:
            storage_usage_by_type.labels(file_type=row.file_type).set(row.total_size)
    
    return {"status": "updated", "message": "Business metrics refreshed"}

