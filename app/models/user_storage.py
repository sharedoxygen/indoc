"""
User storage quota and usage tracking models
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.models.base import BaseModel
from app.core.types import GUID


class UserStorageQuota(BaseModel):
    """User storage quota and limits"""
    __tablename__ = "user_storage_quotas"
    
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Storage limits (in bytes)
    conversation_storage_limit = Column(BigInteger, default=10485760)  # 10MB default
    document_storage_limit = Column(BigInteger, default=104857600)  # 100MB default
    
    # Retention settings (in days)
    conversation_retention_days = Column(Integer, default=90)  # 90 days default
    document_retention_days = Column(Integer, default=365)  # 1 year default
    
    # Premium features
    is_premium = Column(Boolean, default=False)
    premium_tier = Column(String(50), default="free")  # free, basic, pro, enterprise
    premium_expires_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    current_conversation_storage = Column(BigInteger, default=0)
    current_document_storage = Column(BigInteger, default=0)
    conversation_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    
    # Billing
    monthly_fee = Column(Float, default=0.0)
    overage_charges = Column(Float, default=0.0)
    last_billed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    usage_history = relationship("StorageUsageHistory", back_populates="quota", cascade="all, delete-orphan")


class StorageUsageHistory(BaseModel):
    """Track storage usage over time for analytics and billing"""
    __tablename__ = "storage_usage_history"
    
    quota_id = Column(Integer, ForeignKey("user_storage_quotas.id"), nullable=False)
    
    # Snapshot data
    conversation_storage_used = Column(BigInteger, nullable=False)
    document_storage_used = Column(BigInteger, nullable=False)
    conversation_count = Column(Integer, nullable=False)
    message_count = Column(Integer, nullable=False)
    
    # Period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Billing
    storage_cost = Column(Float, default=0.0)
    overage_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Relationships
    quota = relationship("UserStorageQuota", back_populates="usage_history")


class ConversationRetention(BaseModel):
    """Track conversation retention and archival status"""
    __tablename__ = "conversation_retention"
    
    conversation_id = Column(GUID(), ForeignKey("conversations.id"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Retention status
    is_archived = Column(Boolean, default=False)
    is_compressed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # Timestamps
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    scheduled_deletion_at = Column(DateTime, nullable=True)
    
    # Storage
    original_size = Column(BigInteger, nullable=False)
    compressed_size = Column(BigInteger, nullable=True)
    storage_location = Column(String(500), nullable=True)  # cold storage path
    
    # User preferences
    is_pinned = Column(Boolean, default=False)  # Pinned conversations never auto-delete
    is_favorite = Column(Boolean, default=False)
    
    # Relationships
    conversation = relationship("Conversation", backref="retention_info")
    user = relationship("User", backref="conversation_retentions")


# Storage tiers configuration
STORAGE_TIERS = {
    "free": {
        "conversation_storage": 10 * 1024 * 1024,  # 10MB
        "document_storage": 100 * 1024 * 1024,  # 100MB
        "conversation_retention": 30,  # 30 days
        "max_conversations": 10,
        "max_messages_per_conversation": 100,
        "monthly_fee": 0.0
    },
    "basic": {
        "conversation_storage": 100 * 1024 * 1024,  # 100MB
        "document_storage": 1 * 1024 * 1024 * 1024,  # 1GB
        "conversation_retention": 90,  # 90 days
        "max_conversations": 100,
        "max_messages_per_conversation": 1000,
        "monthly_fee": 9.99
    },
    "pro": {
        "conversation_storage": 1 * 1024 * 1024 * 1024,  # 1GB
        "document_storage": 10 * 1024 * 1024 * 1024,  # 10GB
        "conversation_retention": 365,  # 1 year
        "max_conversations": 1000,
        "max_messages_per_conversation": 10000,
        "monthly_fee": 29.99
    },
    "enterprise": {
        "conversation_storage": 10 * 1024 * 1024 * 1024,  # 10GB
        "document_storage": 100 * 1024 * 1024 * 1024,  # 100GB
        "conversation_retention": -1,  # Unlimited
        "max_conversations": -1,  # Unlimited
        "max_messages_per_conversation": -1,  # Unlimited
        "monthly_fee": 99.99
    }
}
