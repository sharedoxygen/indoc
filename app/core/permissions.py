"""
RBAC Permission Enforcement

Per Review C2.5: Ensure all endpoints check permissions
Per AI Guide: Enforce scope and minimum necessary access
"""
import logging
from typing import List, Optional, Callable
from fastapi import HTTPException, status, Depends
from functools import wraps

from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


class PermissionDeniedError(HTTPException):
    """Raised when user lacks required permission"""
    def __init__(self, permission: str, user_email: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: '{permission}' required. Contact your administrator for access."
        )
        logger.warning(f"🔒 Permission denied: {user_email} attempted '{permission}'")


def require_permission(permission_name: str):
    """
    Decorator to enforce permission check on endpoint
    
    Usage:
        @router.get("/admin/dashboard")
        @require_permission("analytics.view")
        async def view_dashboard(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            # Check if user has permission
            if not current_user.has_permission(permission_name):
                raise PermissionDeniedError(permission_name, current_user.email)
            
            # Permission granted, execute function
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(permission_names: List[str]):
    """
    Decorator to require ANY ONE of the listed permissions
    
    Usage:
        @router.post("/documents/share")
        @require_any_permission(["documents.share", "system.admin"])
        async def share_document(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            # Check if user has any of the permissions
            has_permission = any(
                current_user.has_permission(perm) 
                for perm in permission_names
            )
            
            if not has_permission:
                raise PermissionDeniedError(
                    f"any of: {', '.join(permission_names)}",
                    current_user.email
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_all_permissions(permission_names: List[str]):
    """
    Decorator to require ALL listed permissions
    
    Usage:
        @router.delete("/documents/permanent-delete")
        @require_all_permissions(["documents.delete", "documents.admin"])
        async def permanent_delete(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            # Check if user has all permissions
            missing_permissions = [
                perm for perm in permission_names
                if not current_user.has_permission(perm)
            ]
            
            if missing_permissions:
                raise PermissionDeniedError(
                    f"missing: {', '.join(missing_permissions)}",
                    current_user.email
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_role(role_name: str):
    """
    Decorator to require specific role
    
    Usage:
        @router.get("/admin/users")
        @require_role("Admin")
        async def list_all_users(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not current_user.has_role(role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role_name}' required. Current role: {current_user.role}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


async def check_document_permission(
    document_id: int,
    user: User,
    permission: str,
    db
) -> bool:
    """
    Check if user has permission to access specific document
    
    Considers:
    - Document ownership
    - User role
    - Document classification level
    - Explicit grants
    
    Returns:
        True if permitted, False otherwise
    """
    from app.models.document import Document
    from app.models.classification import DocumentClassification
    from sqlalchemy import select
    
    # Admin has access to everything
    if user.has_permission("system.admin"):
        return True
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        return False
    
    # Owner always has access to own documents
    if document.uploaded_by == user.id:
        return True
    
    # Check classification level vs user clearance
    # (Simplified - full implementation would check user classification level)
    if document.classification == DocumentClassification.PUBLIC:
        return True
    
    # For other classifications, check specific permission
    required_permission = f"documents.{permission}"
    return user.has_permission(required_permission)


# Audit helper
def log_permission_check(
    user_email: str,
    permission: str,
    resource_id: Optional[str],
    granted: bool
):
    """Log permission checks for audit trail"""
    status_emoji = "✅" if granted else "❌"
    resource_info = f" on {resource_id}" if resource_id else ""
    logger.info(f"{status_emoji} Permission '{permission}'{resource_info}: {'GRANTED' if granted else 'DENIED'} for {user_email}")

