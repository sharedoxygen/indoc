"""
MFA schemas for TOTP-based multi-factor authentication
"""
from pydantic import BaseModel, Field
from typing import List


class MFAEnrollRequest(BaseModel):
    """Request to enroll in MFA"""
    pass


class MFAEnrollResponse(BaseModel):
    """Response with MFA enrollment details"""
    secret: str = Field(..., description="Base32 encoded TOTP secret")
    qr_code_url: str = Field(..., description="otpauth:// URL for QR code generation")
    backup_codes: List[str] = Field(..., description="One-time backup codes")


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA token"""
    token: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class MFAVerifyResponse(BaseModel):
    """Response after MFA verification"""
    verified: bool


class MFADisableRequest(BaseModel):
    """Request to disable MFA (requires current password)"""
    password: str = Field(..., min_length=1)


class MFAStatusResponse(BaseModel):
    """Current MFA status for user"""
    mfa_enabled: bool
    mfa_required: bool = Field(..., description="Whether MFA is required for this role")


