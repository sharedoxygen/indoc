"""
RBAC Models: Role, Permission, and junction tables
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime, Text, func, UniqueConstraint, Table
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, Base


class Role(BaseModel):
    """
    Role model for RBAC
    
    Roles define groups of permissions that can be assigned to users.
    System roles (admin, manager, analyst) are immutable.
    """
    __tablename__ = "roles"
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles can't be deleted
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Role(name='{self.name}', system={self.is_system})>"


class Permission(BaseModel):
    """
    Permission model for RBAC
    
    Permissions define specific actions that can be performed on resources.
    Format: {resource}.{action} (e.g., documents.read, users.create)
    """
    __tablename__ = "permissions"
    
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., 'documents.read'
    resource = Column(String(50), nullable=False, index=True)  # documents, users, roles, etc.
    action = Column(String(20), nullable=False)  # create, read, update, delete, list
    description = Column(Text, nullable=True)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Permission(name='{self.name}', resource='{self.resource}', action='{self.action}')>"


class UserRole(BaseModel):
    """
    User-Role junction table (Many-to-Many)
    
    Links users to roles. A user can have multiple roles.
    """
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    # Unique constraint: user can't have same role twice
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )
    
    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class RolePermission(BaseModel):
    """
    Role-Permission junction table (Many-to-Many)
    
    Links roles to permissions. A role can have multiple permissions.
    """
    __tablename__ = "role_permissions"
    
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    granter = relationship("User", foreign_keys=[granted_by])
    
    # Unique constraint: role can't have same permission twice
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
    
    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"

