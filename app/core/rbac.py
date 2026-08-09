"""
RBAC (Role-Based Access Control) utilities and decorators
"""
from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, status, Depends
from app.models.user import User
from app.core.security import get_current_user


def require_permission(permission: str):
    """
    Decorator to require a specific permission
    
    Usage:
        @router.get("/documents")
        @require_permission("documents.read")
        async def list_documents(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs (injected by Depends)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # Check permission
            if not current_user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: requires '{permission}'"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: str):
    """
    Decorator to require ANY of the specified permissions
    
    Usage:
        @require_any_permission("documents.read", "documents.list")
        async def view_document(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # Check if user has ANY of the permissions
            user_permissions = current_user.get_permissions()
            has_any = any(perm in user_permissions or current_user.has_role('admin') for perm in permissions)
            
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: requires one of {permissions}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permissions: str):
    """
    Decorator to require ALL of the specified permissions
    
    Usage:
        @require_all_permissions("documents.read", "documents.update")
        async def edit_document(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # Check if user has ALL permissions
            missing = [perm for perm in permissions if not current_user.has_permission(perm)]
            
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: missing permissions {missing}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role_name: str):
    """
    Decorator to require a specific role
    
    Usage:
        @require_role("admin")
        async def admin_only_endpoint(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            if not current_user.has_role(role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role_name}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*role_names: str):
    """
    Decorator to require ANY of the specified roles
    
    Usage:
        @require_any_role("admin", "manager")
        async def manager_or_admin(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            has_any = any(current_user.has_role(role) for role in role_names)
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: one of {role_names}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Dependency for FastAPI route protection
async def check_permission(permission: str, current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to check permission
    
    Usage:
        @router.get("/documents")
        async def list_documents(
            user: User = Depends(lambda: check_permission("documents.read"))
        ):
            ...
    """
    if not current_user.has_permission(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires '{permission}'"
        )
    return current_user


async def check_role(role_name: str, current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to check role
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            user: User = Depends(lambda: check_role("admin"))
        ):
            ...
    """
    if not current_user.has_role(role_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: {role_name}"
        )
    return current_user

