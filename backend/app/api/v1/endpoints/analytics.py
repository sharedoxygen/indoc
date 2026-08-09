"""
Analytics endpoints
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, literal_column

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit import AuditLog


router = APIRouter()


def _require_admin(user: User) -> None:
    role_value = getattr(user.role, "value", user.role)
    if role_value != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access analytics"
        )


@router.get("/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Return high-level analytics summary for the admin dashboard."""
    _require_admin(current_user)

    # Totals
    total_docs_result = await db.execute(select(func.count()).select_from(Document))
    total_documents = total_docs_result.scalar() or 0

    total_storage_result = await db.execute(select(func.coalesce(func.sum(Document.file_size), 0)))
    total_storage_bytes = total_storage_result.scalar() or 0

    # Documents by type
    by_type_result = await db.execute(
        select(Document.file_type, func.count(), func.coalesce(func.sum(Document.file_size), 0))
        .group_by(Document.file_type)
    )
    documents_by_type: List[Dict[str, Any]] = [
        {"file_type": ft or "unknown", "count": c or 0, "total_size": s or 0}
        for ft, c, s in by_type_result.all()
    ]

    # Top uploaders
    top_uploaders_result = await db.execute(
        select(AuditLog.user_email, func.count())
        .where(AuditLog.action == "upload")
        .group_by(AuditLog.user_email)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_uploaders = [
        {"user_email": email, "uploads": count} for email, count in top_uploaders_result.all()
    ]

    # Activity last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    activity_result = await db.execute(
        select(
            func.date_trunc("day", AuditLog.created_at).label("day"),
            func.count().label("events")
        )
        .where(AuditLog.created_at >= start_date)
        .group_by(literal_column("day"))
        .order_by(literal_column("day"))
    )
    activity = [
        {"day": d.isoformat(), "events": e} for d, e in activity_result.all() if d is not None
    ]

    # Event counts
    def _count_action(action: str) -> Any:
        return select(func.count()).select_from(AuditLog).where(AuditLog.action == action)

    search_count = (await db.execute(_count_action("search"))).scalar() or 0
    view_count = (await db.execute(_count_action("view"))).scalar() or 0
    download_count = (await db.execute(_count_action("download"))).scalar() or 0
    upload_count = (await db.execute(_count_action("upload"))).scalar() or 0

    return {
        "totals": {
            "documents": total_documents,
            "storage_bytes": int(total_storage_bytes),
            "events": {
                "searches": search_count,
                "views": view_count,
                "downloads": download_count,
                "uploads": upload_count,
            },
        },
        "documents_by_type": documents_by_type,
        "top_uploaders": top_uploaders,
        "activity_last_30_days": activity,
    }


@router.get("/storage")
async def get_storage_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Return storage usage breakdown by file type and access level."""
    _require_admin(current_user)

    by_type_result = await db.execute(
        select(Document.file_type, func.coalesce(func.sum(Document.file_size), 0))
        .group_by(Document.file_type)
    )
    by_type = [
        {"file_type": ft or "unknown", "bytes": int(size or 0)} for ft, size in by_type_result.all()
    ]

    by_access_result = await db.execute(
        select(Document.access_level, func.coalesce(func.sum(Document.file_size), 0))
        .group_by(Document.access_level)
    )
    by_access = [
        {"access_level": level or "unknown", "bytes": int(size or 0)} for level, size in by_access_result.all()
    ]

    return {"by_type": by_type, "by_access_level": by_access}


@router.get("/timeseries")
async def get_analytics_timeseries(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Return time series for key metrics over the last N days."""
    _require_admin(current_user)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Documents created per day
    docs_result = await db.execute(
        select(
            func.date_trunc("day", Document.created_at).label("day"),
            func.count().label("count")
        )
        .where(Document.created_at >= start_date)
        .group_by(literal_column("day"))
        .order_by(literal_column("day"))
    )
    documents_created = [
        {"day": d.isoformat(), "count": c} for d, c in docs_result.all() if d is not None
    ]

    # Audit actions per day
    def _action_timeseries(action: str) -> List[Dict[str, Any]]:
        return [
            {"day": d.isoformat(), "count": c}
            for d, c in (
                db.sync_session.execute(  # type: ignore
                    select(
                        func.date_trunc("day", AuditLog.created_at).label("day"),
                        func.count().label("count"),
                    )
                    .where(AuditLog.created_at >= start_date)
                    .where(AuditLog.action == action)
                    .group_by(literal_column("day"))
                    .order_by(literal_column("day"))
                ).all()
            ) if d is not None
        ]

    # Async version for actions
    async def _action_timeseries_async(action: str) -> List[Dict[str, Any]]:
        res = await db.execute(
            select(
                func.date_trunc("day", AuditLog.created_at).label("day"),
                func.count().label("count"),
            )
            .where(AuditLog.created_at >= start_date)
            .where(AuditLog.action == action)
            .group_by(literal_column("day"))
            .order_by(literal_column("day"))
        )
        return [
            {"day": d.isoformat(), "count": c} for d, c in res.all() if d is not None
        ]

    uploads = await _action_timeseries_async("upload")
    views = await _action_timeseries_async("view")
    searches = await _action_timeseries_async("search")

    return {
        "documents_created": documents_created,
        "uploads": uploads,
        "views": views,
        "searches": searches,
        "period_days": days,
    }


@router.get("/processing")
async def get_processing_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Return processing queue and performance metrics."""
    _require_admin(current_user)

    # Status counts
    status_counts_result = await db.execute(
        select(Document.status, func.count())
        .group_by(Document.status)
    )
    status_counts = {status: count for status, count in status_counts_result.all()}

    # Processing time by file type (for completed docs)
    processing_time_result = await db.execute(
        select(
            Document.file_type,
            func.avg(
                func.extract('epoch', Document.updated_at) - 
                func.extract('epoch', Document.created_at)
            ).label('avg_seconds')
        )
        .where(Document.status == 'indexed')
        .group_by(Document.file_type)
    )
    avg_time_by_type = [
        {"file_type": ft or "unknown", "avg_seconds": float(avg_secs or 0)}
        for ft, avg_secs in processing_time_result.all()
    ]

    # Total processed count
    processed_total_result = await db.execute(
        select(func.count()).where(Document.status == 'indexed')
    )
    processed_total = processed_total_result.scalar() or 0

    # Recent processing activity (last 7 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    recent_processing_result = await db.execute(
        select(
            func.date_trunc("day", Document.updated_at).label("day"),
            func.count().label("processed_count")
        )
        .where(Document.status == 'indexed')
        .where(Document.updated_at >= start_date)
        .group_by(literal_column("day"))
        .order_by(literal_column("day"))
    )
    recent_processing = [
        {"day": d.isoformat(), "processed": c} 
        for d, c in recent_processing_result.all() if d is not None
    ]

    # Error rate
    total_docs_result = await db.execute(select(func.count()).select_from(Document))
    total_docs = total_docs_result.scalar() or 0
    failed_docs_result = await db.execute(
        select(func.count()).where(Document.status == 'failed')
    )
    failed_docs = failed_docs_result.scalar() or 0
    error_rate = (failed_docs / total_docs * 100) if total_docs > 0 else 0

    return {
        "status_counts": status_counts,
        "avg_time_to_process_by_type": avg_time_by_type,
        "processed_total": processed_total,
        "recent_processing_7d": recent_processing,
        "error_rate_percent": round(error_rate, 2),
        "total_documents": total_docs,
        "failed_documents": failed_docs
    }


