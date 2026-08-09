"""
Token revocation model for JWT blacklist
"""
from sqlalchemy import Column, String, Index, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class RevokedToken(BaseModel):
    """
    Track revoked JWT tokens (for logout, password change, role change)
    """
    __tablename__ = "revoked_tokens"
    __table_args__ = (
        Index('idx_revoked_token_jti', 'jti', unique=True),
        Index('idx_revoked_token_user', 'user_id'),
        Index('idx_revoked_token_expires', 'expires_at'),
    )
    
    jti = Column(String(36), nullable=False, unique=True, index=True)  # JWT ID (unique token identifier)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_type = Column(String(20), nullable=False)  # "access" or "refresh"
    reason = Column(String(100), nullable=True)  # "logout", "password_change", "role_change", "manual_revoke"
    expires_at = Column(String(50), nullable=False)  # ISO timestamp when token naturally expires
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


