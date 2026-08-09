"""
User model with RBAC support
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer
from sqlalchemy.types import Enum as SQLAlchemyEnum
from app.core.types import GUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    ANALYST = "Analyst"
    # Legacy roles retained for backward-compatibility during migration
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
    role = Column(
        SQLAlchemyEnum(
            UserRole,
            values_callable=lambda x: [e.value for e in x],
            name='userrole',
            create_constraint=True,
            native_enum=True,
            validate_strings=True
        ),
        default=UserRole.ANALYST,
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    # Multi-tenancy (nullable for legacy records)
    tenant_id = Column(GUID(), nullable=True, index=True)
    # Hierarchical RBAC — Analysts are linked to their Manager (self-referencing FK)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Additional user fields
    department = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    location = Column(String(100), nullable=True)

    # MFA fields
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(32), nullable=True)  # Base32 encoded TOTP secret
    mfa_backup_codes = Column(String(512), nullable=True)  # Encrypted JSON array of backup codes

    # Relationships for hierarchy
    manager = relationship("User", remote_side="User.id", back_populates="analysts", uselist=False)
    analysts = relationship("User", back_populates="manager", cascade="all, delete-orphan")
    
    # RBAC Relationships
    user_roles = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user", cascade="all, delete-orphan")
    
    # Relationships
    documents = relationship("Document", back_populates="uploaded_by_user", cascade="all, delete-orphan")
    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="AuditLog.user_id",
    )
    annotations = relationship("Annotation", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    # storage_quota = relationship("UserStorageQuota", back_populates="user", uselist=False)  # TODO: Fix import
    
    # RBAC Helper Methods
    def get_roles(self):
        """Get all active roles for this user"""
        from datetime import datetime
        return [
            ur.role for ur in self.user_roles
            if ur.role.is_active and (ur.expires_at is None or ur.expires_at > datetime.now())
        ]
    
    def get_permissions(self):
        """Get all permissions from all user's roles"""
        permissions = set()
        for role in self.get_roles():
            for rp in role.role_permissions:
                permissions.add(rp.permission.name)
        return permissions
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        # Admin has wildcard access
        if any(role.name == 'admin' for role in self.get_roles()):
            return True
        return permission_name in self.get_permissions()
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.get_roles())