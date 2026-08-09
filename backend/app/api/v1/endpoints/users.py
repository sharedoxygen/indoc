"""
User management endpoints
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.schemas.auth import UserResponse, UserCreate, UserUpdate
from app.crud.user import (
    get_users,
    get_user_by_id,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    activate_user,
    deactivate_user,
    update_user_password,
    get_user_count
)

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all users (Admin only)
    """
    user_role = UserRole(role) if role else None
    users = await get_users(db, skip=skip, limit=limit, role=user_role)
    
    # Log access
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="list",
        resource_type="users",
        details={"count": len(users), "role_filter": role}
    )
    db.add(audit_log)
    await db.commit()
    
    return users


@router.get("/stats")
async def get_user_statistics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user statistics (Admin only)
    """
    # Get counts by role
    stats = {}
    for role in UserRole:
        result = await db.execute(
            select(func.count()).select_from(User).where(User.role == role)
        )
        stats[role.value] = result.scalar()
    
    # Get total counts
    total_result = await db.execute(select(func.count()).select_from(User))
    active_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    verified_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_verified == True)
    )
    
    return {
        "total_users": total_result.scalar(),
        "active_users": active_result.scalar(),
        "verified_users": verified_result.scalar(),
        "users_by_role": stats
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user by ID
    Users can view their own profile, Admins can view any profile
    """
    # Check permissions
    if current_user.id != user_id and getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/", response_model=UserResponse)
async def create_new_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new user (Admin only)
    """
    # Check if user exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = await create_user(db, user_data)
    
    # Log creation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="create",
        resource_type="user",
        resource_id=str(user.id),
        details={"new_user_email": user.email, "new_user_role": getattr(user.role, "value", user.role)}
    )
    db.add(audit_log)
    await db.commit()
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_info(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update user information
    Users can update their own profile (except role), Admins can update any profile
    """
    # Check permissions
    if current_user.id != user_id and getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    # Non-admins cannot change roles
    if getattr(current_user.role, "value", current_user.role) != "Admin" and user_update.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles"
        )
    
    # Update user
    user = await update_user(db, user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log update
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="update",
        resource_type="user",
        resource_id=str(user_id),
        details={"updated_fields": list(user_update.dict(exclude_unset=True).keys())}
    )
    db.add(audit_log)
    await db.commit()
    
    return user


@router.post("/{user_id}/activate")
async def activate_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Activate a user account (Admin only)
    """
    success = await activate_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log activation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="activate",
        resource_type="user",
        resource_id=str(user_id)
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "User activated successfully"}


@router.post("/{user_id}/deactivate")
async def deactivate_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Deactivate a user account (Admin only)
    """
    # Prevent self-deactivation
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    success = await deactivate_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log deactivation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="deactivate",
        resource_type="user",
        resource_id=str(user_id)
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reset user password (Admin only)
    """
    success = await update_user_password(db, user_id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log password reset
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="reset_password",
        resource_type="user",
        resource_id=str(user_id)
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "Password reset successfully"}


@router.delete("/{user_id}")
async def delete_user_account(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a user account (Admin only)
    """
    # Prevent self-deletion
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Get user info before deletion for audit log
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Log deletion before removing
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="delete",
        resource_type="user",
        resource_id=str(user_id),
        details={"deleted_user_email": user.email}
    )
    db.add(audit_log)
    
    # Delete user
    success = await delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
    
    await db.commit()
    
    return {"message": "User deleted successfully"}