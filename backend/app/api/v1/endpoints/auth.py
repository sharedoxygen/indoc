"""
Authentication endpoints
"""
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    verify_password,
    create_access_token,
    get_password_hash,
    get_current_user
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserResponse
from app.models.audit import AuditLog

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new user"""
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role or "Viewer",
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Log registration
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        user_role=getattr(user.role, "value", user.role),
        action="register",
        resource_type="user",
        resource_id=str(user.id)
    )
    db.add(audit_log)
    await db.commit()
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=getattr(user.role, "value", user.role),
        is_active=user.is_active,
        is_verified=user.is_verified
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Login and get access token"""
    # Get user by email or username
    result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | 
            (User.username == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": getattr(user.role, "value", user.role)},
        expires_delta=access_token_expires
    )
    
    # Log login
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        user_role=getattr(user.role, "value", user.role),
        action="login",
        resource_type="auth",
        resource_id=str(user.id)
    )
    db.add(audit_log)
    await db.commit()
    
    return Token(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=getattr(current_user.role, "value", current_user.role),
        is_active=current_user.is_active,
        is_verified=current_user.is_verified
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Logout current user"""
    # Log logout
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="logout",
        resource_type="auth",
        resource_id=str(current_user.id)
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "Successfully logged out"}