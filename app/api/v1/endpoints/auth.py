"""
Authentication endpoints
"""
from datetime import timedelta
from typing import Any
import time
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    get_current_user
)
from app.core.mfa import is_mfa_required_for_role
from app.core.auth_lockout import auth_lockout_manager
from app.db.session import get_db
from app.models.user import User
from app.models.token_revocation import RevokedToken
from app.schemas.auth import Token, UserCreate, UserResponse, RefreshTokenRequest
from app.models.audit import AuditLog

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new user with password policy enforcement"""
    
    # CRITICAL: Validate password complexity (Review C2.2)
    from app.core.password_policy import validate_password, PasswordValidationError, password_validator
    try:
        validate_password(user_data.password)
    except PasswordValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {str(e)}",
            headers={"X-Password-Requirements": password_validator.get_requirements_text()}
        )
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username exists
    username_check = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if username_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
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
    await db.flush()  # Flush to get the user.id for audit log
    
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
    # Both user and audit_log will be committed by get_db dependency
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=getattr(user.role, "value", user.role),
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Login and get access token"""
    # Create identifier for lockout tracking (username/email + IP)
    client_ip = request.client.host if request and request.client else "unknown"
    lockout_identifier = f"{form_data.username}:{client_ip}"
    
    # Check if account is locked
    is_locked, unlock_time = auth_lockout_manager.is_locked(lockout_identifier)
    if is_locked:
        remaining = int(unlock_time - time.time()) if unlock_time else 0
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked due to too many failed attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )
    
    # Get user by email or username
    result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | 
            (User.username == form_data.username)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Record failed attempt
        lockout_info = auth_lockout_manager.record_failed_attempt(lockout_identifier)
        
        # Log failed attempt (will be committed by get_db dependency)
        if user:
            audit_log = AuditLog(
                user_id=user.id,
                user_email=user.email,
                user_role=getattr(user.role, "value", user.role),
                action="login_failed",
                resource_type="auth",
                resource_id=str(user.id),
                metadata={"reason": "invalid_password", "client_ip": client_ip}
            )
            db.add(audit_log)
        
        # If locked, provide specific message
        if lockout_info.get("locked"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=lockout_info["message"],
                headers={"Retry-After": str(lockout_info["lockout_duration"])},
            )
        
        # Otherwise, generic auth error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect username or password. {lockout_info.get('attempts_remaining', 0)} attempts remaining.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if MFA is required and enabled for this user
    role_str = getattr(user.role, "value", user.role)
    mfa_required = settings.MFA_ENABLED and is_mfa_required_for_role(role_str)
    
    if mfa_required:
        if not user.mfa_enabled:
            # User must enroll in MFA before proceeding
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="MFA enrollment required for your role. Please enroll at /api/v1/mfa/enroll"
            )
        
        # Return a temporary token that indicates MFA verification is pending
        # In a full implementation, this would be a special "pre-auth" token
        # For now, we'll return a token but indicate MFA is required
        # The frontend should then prompt for MFA and call /mfa/verify
        access_token_expires = timedelta(minutes=5)  # Short-lived pre-auth token
        access_token = create_access_token(
            data={"sub": user.email, "role": role_str, "mfa_verified": False},
            expires_delta=access_token_expires
        )
        
        # Log MFA required (will be committed by get_db dependency)
        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            user_role=role_str,
            action="login_mfa_required",
            resource_type="auth",
            resource_id=str(user.id)
        )
        db.add(audit_log)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            mfa_required=True
        )
    
    # No MFA required or MFA not enabled globally - proceed with normal login
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": role_str},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(user.id, role_str)
    
    # Record successful login (reset lockout counters)
    auth_lockout_manager.record_successful_login(lockout_identifier)
    
    # Log login (will be committed by get_db dependency)
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        user_role=role_str,
        action="login",
        resource_type="auth",
        resource_id=str(user.id),
        metadata={"client_ip": client_ip}
    )
    db.add(audit_log)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        mfa_required=False,
        refresh_token=refresh_token
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
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh an access token using a refresh token
    """
    try:
        # Decode refresh token
        payload = decode_token(request.refresh_token)
        user_id = payload.get("sub")
        jti = payload.get("jti")
        token_type = payload.get("type")
        
        if not user_id or not jti or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token is revoked
        from app.core.security import is_token_revoked
        if await is_token_revoked(jti, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )
        
        # Get user
        from app.crud.user import get_user_by_id
        user = await get_user_by_id(db, int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        role_str = getattr(user.role, "value", user.role)
        access_token_expires = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.email, "role": role_str},
            expires_delta=access_token_expires
        )
        
        # Log token refresh (will be committed by get_db dependency)
        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            user_role=role_str,
            action="token_refresh",
            resource_type="auth",
            resource_id=str(user.id)
        )
        db.add(audit_log)
        
        return Token(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=request.refresh_token  # Return same refresh token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Logout current user and revoke their tokens
    """
    # Extract JTI from current token
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp_timestamp = payload.get("exp")
        
        if jti and exp_timestamp:
            # Add to revocation list
            from datetime import datetime
            expires_at = datetime.fromtimestamp(exp_timestamp).isoformat()
            
            revoked_token = RevokedToken(
                jti=jti,
                user_id=current_user.id,
                token_type="access",
                reason="logout",
                expires_at=expires_at
            )
            db.add(revoked_token)
    except Exception:
        pass  # If we can't revoke, still log the logout
    
    # Log logout (will be committed by get_db dependency)
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="logout",
        resource_type="auth",
        resource_id=str(current_user.id)
    )
    db.add(audit_log)
    
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Allow users to change their own password.
    Requires current password verification for security.
    """
    # Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Check password complexity
    import re
    if not re.search(r'[A-Z]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    if not re.search(r'[a-z]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    if not re.search(r'[0-9]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character"
        )
    
    # Don't allow same password
    if verify_password(new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    await db.flush()
    
    # Log password change
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="change_password",
        resource_type="auth",
        resource_id=str(current_user.id),
        details={"message": "User changed their password"}
    )
    db.add(audit_log)
    
    return {
        "message": "Password changed successfully",
        "recommendation": "Please log in again with your new password"
    }