"""
Audit log endpoints
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.audit import AuditLog

router = APIRouter()


@router.get("/logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get audit logs with optional filters"""
    
    # Only admins can view audit logs
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs"
        )
    
    # Build query
    query = select(AuditLog)
    
    # Apply filters
    filters = []
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if start_date:
        filters.append(AuditLog.created_at >= start_date)
    if end_date:
        filters.append(AuditLog.created_at <= end_date)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by created_at descending
    query = query.order_by(desc(AuditLog.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Format response
    return {
        "total": len(logs),
        "skip": skip,
        "limit": limit,
        "logs": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "user_email": log.user_email,
                "user_role": log.user_role,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


@router.get("/logs/summary")
async def get_audit_summary(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get audit log summary for the specified number of days"""
    
    # Only admins can view audit logs
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view audit logs"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get logs for the period
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.created_at >= start_date
        )
    )
    logs = result.scalars().all()
    
    # Calculate summary statistics
    action_counts = {}
    resource_counts = {}
    user_counts = {}
    
    for log in logs:
        # Count by action
        action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        # Count by resource type
        resource_counts[log.resource_type] = resource_counts.get(log.resource_type, 0) + 1
        
        # Count by user
        user_key = f"{log.user_email} ({log.user_role})"
        user_counts[user_key] = user_counts.get(user_key, 0) + 1
    
    return {
        "period_days": days,
        "total_events": len(logs),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "actions": action_counts,
        "resources": resource_counts,
        "top_users": dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    }


@router.post("/logs/export")
async def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Export audit logs in specified format"""
    
    # Only admins can export audit logs
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can export audit logs"
        )
    
    # This is a placeholder - actual implementation would generate and return a file
    return {
        "status": "success",
        "message": f"Audit logs export in {format} format initiated",
        "job_id": "export_12345"
    }