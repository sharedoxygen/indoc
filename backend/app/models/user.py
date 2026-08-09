"""
User model with RBAC support
"""
from sqlalchemy import Column, String, Boolean, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM as PostgreSQLEnum
from sqlalchemy.orm import relationship
import enum
import uuid

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    REVIEWER = "Reviewer"
    UPLOADER = "Uploader"
    VIEWER = "Viewer"
    COMPLIANCE = "Compliance"


class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Relationships
    documents = relationship("Document", back_populates="uploaded_by_user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")