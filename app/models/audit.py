"""
Audit log model for compliance tracking
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_manager', 'manager_id'),  # For hierarchical audit queries
    )
    
    # User info
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_email = Column(String(255), nullable=False)  # Denormalized for audit integrity
    user_role = Column(String(50), nullable=False)  # Denormalized for audit integrity
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For hierarchical audit queries
    
    # Action details
    action = Column(String(100), nullable=False)  # create, read, update, delete, search, export
    resource_type = Column(String(100), nullable=False)  # document, user, settings, etc.
    resource_id = Column(String(100))
    
    # Request info
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(String(500))
    request_method = Column(String(10))
    request_path = Column(String(500))
    request_params = Column(JSON)
    
    # Response info
    response_status = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Additional context
    details = Column(JSON)  # Flexible field for additional audit data
    error_message = Column(Text)
    
    # Compliance fields
    data_classification = Column(String(50))  # public, internal, confidential, restricted
    compliance_tags = Column(JSON, default=list)  # GDPR, HIPAA, PCI-DSS flags
    
    # Relationships
    # Relationships
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    manager = relationship("User", foreign_keys=[manager_id])