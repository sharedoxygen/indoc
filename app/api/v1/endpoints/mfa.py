"""
MFA (Multi-Factor Authentication) endpoints
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user, verify_password
from app.core.mfa import (
    generate_totp_secret,
    generate_backup_codes,
    encrypt_backup_codes,
    generate_provisioning_uri,
    verify_totp,
    verify_backup_code,
    is_mfa_required_for_role
)
from app.db.session import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.mfa import (
    MFAEnrollRequest,
    MFAEnrollResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    MFADisableRequest,
    MFAStatusResponse
)

router = APIRouter()


@router.get("/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current MFA status for the user"""
    role_str = getattr(current_user.role, "value", current_user.role)
    
    return MFAStatusResponse(
        mfa_enabled=current_user.mfa_enabled,
        mfa_required=settings.MFA_ENABLED and is_mfa_required_for_role(role_str)
    )


@router.post("/enroll", response_model=MFAEnrollResponse)
async def enroll_mfa(
    request: MFAEnrollRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Enroll user in MFA (TOTP)
    
    Returns a secret and QR code URL for setting up an authenticator app
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this user"
        )
    
    # Generate TOTP secret and backup codes
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes(count=10)
    
    # Encrypt backup codes using field encryption key
    encrypted_codes = encrypt_backup_codes(backup_codes, settings.FIELD_ENCRYPTION_KEY)
    
    # Store secret and encrypted backup codes (not yet enabled)
    current_user.mfa_secret = secret
    current_user.mfa_backup_codes = encrypted_codes
    # Don't enable MFA yet - user must verify a token first
    
    # Generate provisioning URI for QR code
    qr_url = generate_provisioning_uri(secret, current_user.email)
    
    # Log enrollment initiation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="mfa_enroll_initiated",
        resource_type="auth",
        resource_id=str(current_user.id)
    )
    db.add(audit_log)
    # Will be committed by get_db dependency
    
    return MFAEnrollResponse(
        secret=secret,
        qr_code_url=qr_url,
        backup_codes=backup_codes  # Show once, never again
    )


@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Verify MFA token and complete enrollment (or verify during login)
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not set up for this user. Call /mfa/enroll first."
        )
    
    # Try TOTP verification first
    is_valid = verify_totp(current_user.mfa_secret, request.token)
    
    # If TOTP fails, try backup code
    if not is_valid and current_user.mfa_backup_codes:
        is_valid, updated_codes = verify_backup_code(
            current_user.mfa_backup_codes,
            settings.FIELD_ENCRYPTION_KEY,
            request.token
        )
        if is_valid:
            # Update backup codes (one was consumed)
            current_user.mfa_backup_codes = updated_codes if updated_codes else None
    
    if not is_valid:
        # Log failed verification
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            action="mfa_verify_failed",
            resource_type="auth",
            resource_id=str(current_user.id)
        )
        db.add(audit_log)
        # Will be committed by get_db dependency when exception is raised
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA token or backup code"
        )
    
    # If not yet enabled, enable MFA now (completing enrollment)
    if not current_user.mfa_enabled:
        current_user.mfa_enabled = True
        
        # Log successful enrollment completion
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            action="mfa_enabled",
            resource_type="auth",
            resource_id=str(current_user.id)
        )
    else:
        # Log successful verification
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            action="mfa_verified",
            resource_type="auth",
            resource_id=str(current_user.id)
        )
    
    db.add(audit_log)
    # Will be committed by get_db dependency
    
    return MFAVerifyResponse(verified=True)


@router.post("/disable")
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Disable MFA for the current user (requires password confirmation)
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this user"
        )
    
    # Verify password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Check if MFA is required for this role
    role_str = getattr(current_user.role, "value", current_user.role)
    if settings.MFA_ENABLED and is_mfa_required_for_role(role_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"MFA is required for {role_str} role and cannot be disabled"
        )
    
    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_backup_codes = None
    
    # Log MFA disable
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="mfa_disabled",
        resource_type="auth",
        resource_id=str(current_user.id)
    )
    db.add(audit_log)
    # Will be committed by get_db dependency
    
    return {"message": "MFA disabled successfully"}


