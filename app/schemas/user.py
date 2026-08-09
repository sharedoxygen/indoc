"""
User schemas for request/response validation
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


class UserRoleEnum(str, Enum):
    Admin = "Admin"
    Manager = "Manager"
    Analyst = "Analyst"
    Reviewer = "Reviewer"
    Uploader = "Uploader"
    Viewer = "Viewer"
    Compliance = "Compliance"


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRoleEnum = UserRoleEnum.Analyst
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    is_active: bool = True
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRoleEnum] = None
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    manager_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    manager_id: Optional[int] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    
    class Config:
        from_attributes = True
        from_attributes = True
        
    @validator('role', pre=True)
    def convert_role(cls, v):
        if hasattr(v, 'value'):
            return v.value
        return v


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int = 1
    per_page: int = 25
    
    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserLogin(BaseModel):
    username: str  # Can be email or username
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserMe(UserResponse):
    """Extended user response for current user"""
    permissions: Optional[List[str]] = []
    settings: Optional[dict] = {}
    
    class Config:
        from_attributes = True
