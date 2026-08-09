"""
Document permission model for fine-grained access control
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class DocumentPermission(Base):
    """
    Document-level permissions for fine-grained access control
    
    Extends RBAC with explicit user-document permissions:
    - read: Can view document
    - write: Can edit document metadata
    - share: Can grant access to others
    - delete: Can delete document
    """
    __tablename__ = "document_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_type = Column(String(20), nullable=False)  # read, write, share, delete
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    granted_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=True)
    
    # Relationships
    document = relationship("Document", backref="permissions")
    user = relationship("User", foreign_keys=[user_id], backref="document_permissions")
    granter = relationship("User", foreign_keys=[granted_by])
    
    __table_args__ = (
        {'extend_existing': True}
    )

