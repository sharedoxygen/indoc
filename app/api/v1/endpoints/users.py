"""
User management endpoints with full CRUD operations
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    PasswordReset,
    UserStatusUpdate
)
from app.core.security import get_password_hash
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user's information.
    Any authenticated user can access this endpoint.
    """
    return UserResponse.model_validate(current_user)


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all users with optional filtering.
    Only admins can access this endpoint.
    """
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view all users"
        )
    
    query = select(User)
    
    # Apply filters
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    
    if role:
        try:
            role_enum = UserRole[role]
            query = query.where(User.role == role_enum)
        except KeyError:
            # If role is already a string value, compare directly
            query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # Add ordering and pagination
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.model_validate(user) for user in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user.
    Only admins can create users.
    """
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users"
        )
    
    # Check if email or username already exists
    existing_user = await db.execute(
        select(User).where(
            or_(
                User.email == user_data.email,
                User.username == user_data.username
            )
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role if user_data.role else UserRole.ANALYST,
        is_active=user_data.is_active,
        department=user_data.department,
        phone=user_data.phone,
        location=user_data.location,
        tenant_id=current_user.tenant_id  # Same tenant as creator
    )
    
    db.add(new_user)
    await db.flush()  # Flush to get the user.id without committing yet
    # Will be committed by get_db dependency
    
    # Send welcome email if needed
    # await send_welcome_email(new_user.email, user_data.password)
    
    logger.info(f"User {new_user.email} created by {current_user.email}")
    
    return UserResponse.model_validate(new_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific user by ID.
    Admins can view any user, others can only view themselves.
    """
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a user.
    Admins can update any user, others can only update themselves (limited fields).
    """
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    
    # Non-admins can't change certain fields
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        restricted_fields = ['role', 'is_active', 'is_verified', 'email']
        for field in restricted_fields:
            update_data.pop(field, None)
    
    # Handle role update
    if 'role' in update_data and isinstance(update_data['role'], str):
        try:
            update_data['role'] = UserRole[update_data['role']]
        except KeyError:
            # If role is already a string value, keep it as is
            pass
    
    # Handle password update
    if 'password' in update_data:
        update_data['hashed_password'] = get_password_hash(update_data.pop('password'))
    
    # Apply updates
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    
    # Changes will be committed by get_db dependency
    
    logger.info(f"User {user.email} updated by {current_user.email}")
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user.
    Only admins can delete users.
    """
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete users"
        )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hard delete - permanently remove user from database
    # This will cascade delete related records if configured in models
    await db.delete(user)
    await db.flush()  # Flush the deletion immediately
    # Will be committed by get_db dependency
    
    logger.info(f"User {user.email} (ID: {user_id}) permanently deleted by {current_user.email}")


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate secure temporary password for user.
    Only admins can reset other users' passwords.
    Returns the temporary password for admin to share with user.
    """
    if getattr(current_user.role, "value", current_user.role) != "Admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reset other users' passwords"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate secure temporary password
    import secrets
    import string
    
    # Password requirements: 12 chars, uppercase, lowercase, numbers, special chars
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
    
    # Ensure password meets complexity requirements
    while not (any(c.isupper() for c in temp_password) and
               any(c.islower() for c in temp_password) and
               any(c.isdigit() for c in temp_password) and
               any(c in "!@#$%^&*" for c in temp_password)):
        temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
    
    # Update user's password
    user.hashed_password = get_password_hash(temp_password)
    await db.flush()
    
    logger.info(f"Password reset for {user.email} by {current_user.email}")
    
    # Return temporary password to admin
    return {
        "message": "Password reset successfully",
        "temporary_password": temp_password,
        "user_email": user.email,
        "instructions": "Share this temporary password securely with the user. User should change it immediately after login."
    }


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user active status.
    Only admins can change user status.
    """
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change user status"
        )
    
    if current_user.id == user_id and not status_update.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = status_update.is_active
    # Changes will be committed by get_db dependency
    
    logger.info(
        f"User {user.email} {'activated' if user.is_active else 'deactivated'} "
        f"by {current_user.email}"
    )
    
    return UserResponse.model_validate(user)


@router.get("/team/analysts", response_model=List[UserResponse])
async def get_team_analysts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analysts assigned to the current manager's team.
    Only managers can access this endpoint.
    """
    if getattr(current_user.role, "value", current_user.role) != "Manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can view their team"
        )
    
    # Get analysts assigned to this manager
    query = select(User).where(
        User.role == "Analyst",  # Use string comparison for database compatibility
        User.manager_id == current_user.id,
        User.tenant_id == current_user.tenant_id
    ).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    analysts = result.scalars().all()
    
    return [UserResponse.model_validate(analyst) for analyst in analysts]


@router.get("/statistics", response_model=dict)
async def get_user_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user statistics.
    Only admins can access this endpoint.
    """
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view user statistics"
        )
    
    # Get counts by role
    role_counts = await db.execute(
        select(User.role, func.count(User.id))
        .group_by(User.role)
    )
    
    # Get active/inactive counts
    active_count = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    
    inactive_count = await db.execute(
        select(func.count(User.id)).where(User.is_active == False)
    )
    
    # Get verified/unverified counts
    verified_count = await db.execute(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    
    return {
        "total_users": active_count.scalar() + inactive_count.scalar(),
        "active_users": active_count.scalar(),
        "inactive_users": inactive_count.scalar(),
        "verified_users": verified_count.scalar(),
        "roles": {
            role.value: count 
            for role, count in role_counts.all()
        },
        "recent_signups": await db.execute(
            select(func.count(User.id))
            .where(User.created_at >= func.now() - func.interval('7 days'))
        ).scalar()
    }