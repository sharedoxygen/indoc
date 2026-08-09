"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional
import re
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False  # Indicates if MFA verification is pending
    refresh_token: Optional[str] = None  # Long-lived token for refreshing access tokens


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # Allow .local domains for development
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$|^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.local$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v


class UserCreate(UserBase):
    password: str
    role: Optional[str] = "Uploader"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    is_active: bool
    is_verified: bool
    # Timestamp of user creation
    created_at: datetime


class RefreshTokenRequest(BaseModel):
    refresh_token: str