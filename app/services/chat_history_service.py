"""
Chat history management service with storage quotas and retention
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
import json
import gzip
import logging

from app.models.conversation import Conversation, Message
from app.models.user import User
from app.models.user_storage import (
    UserStorageQuota,
    StorageUsageHistory,
    ConversationRetention,
    STORAGE_TIERS
)
from app.core.cache import cache_service
from app.schemas.conversation import ConversationResponse, MessageResponse

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """Service for managing chat history with storage quotas and retention"""
    
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache
    
    async def get_user_conversations(
        self,
        db: AsyncSession,
        user: User,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> Tuple[List[Conversation], int]:
        """Get user's conversation history with pagination"""
        
        # Get user's storage quota
        quota = await self._get_or_create_quota(db, user)
        
        # Build query
        query = select(Conversation).where(
            Conversation.user_id == user.id
        )
        
        # Filter archived if needed
        if not include_archived:
            query = query.outerjoin(ConversationRetention).where(
                or_(
                    ConversationRetention.is_archived == False,
                    ConversationRetention.is_archived == None
                )
            )
        
        # Order by most recent
        query = query.order_by(desc(Conversation.updated_at))
        
        # Get total count
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute with eager loading
        query = query.options(
            selectinload(Conversation.messages)
        )
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        # Check and apply retention policies
        await self._apply_retention_policies(db, user, conversations)
        
        return conversations, total
    
    async def get_conversation_with_messages(
        self,
        db: AsyncSession,
        user: User,
        conversation_id: str,
        message_limit: int = 50
    ) -> Optional[Conversation]:
        """Get a specific conversation with its messages"""
        
        # Check cache first
        cache_key = f"conversation:{user.id}:{conversation_id}"
        cached = await cache_service.get(cache_key)
        if cached:
            return cached
        
        # Query conversation
        query = select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            )
        ).options(
            selectinload(Conversation.messages)
        )
        
        result = await db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if conversation:
            # Update last accessed
            await self._update_last_accessed(db, conversation_id)
            
            # Cache the result
            await cache_service.set(cache_key, conversation, ttl=self.cache_ttl)
        
        return conversation
    
    async def save_message(
        self,
        db: AsyncSession,
        user: User,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Message:
        """Save a message and update storage usage"""
        
        # Check storage quota
        quota = await self._get_or_create_quota(db, user)
        message_size = len(content.encode('utf-8'))
        
        if not await self._check_storage_available(quota, message_size):
            # Try to free up space
            await self._auto_archive_old_conversations(db, user, quota)
            
            # Check again
            if not await self._check_storage_available(quota, message_size):
                raise StorageQuotaExceeded(
                    f"Storage quota exceeded. Current: {quota.current_conversation_storage}, "
                    f"Limit: {quota.conversation_storage_limit}"
                )
        
        # Create message
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=metadata or {}
        )
        
        db.add(message)
        
        # Update storage usage
        quota.current_conversation_storage += message_size
        quota.message_count += 1
        
        await db.commit()
        await db.refresh(message)
        
        # Invalidate cache
        cache_key = f"conversation:{user.id}:{conversation_id}"
        await cache_service.delete(cache_key)
        
        return message
    
    async def archive_conversation(
        self,
        db: AsyncSession,
        user: User,
        conversation_id: str,
        compress: bool = True
    ) -> ConversationRetention:
        """Archive a conversation to free up active storage"""
        
        # Get conversation
        conversation = await self.get_conversation_with_messages(db, user, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        
        # Calculate size
        original_size = sum(
            len(msg.content.encode('utf-8')) 
            for msg in conversation.messages
        )
        
        # Get or create retention record
        retention = await db.execute(
            select(ConversationRetention).where(
                ConversationRetention.conversation_id == conversation_id
            )
        )
        retention = retention.scalar_one_or_none()
        
        if not retention:
            retention = ConversationRetention(
                conversation_id=conversation_id,
                user_id=user.id,
                original_size=original_size
            )
            db.add(retention)
        
        # Archive the conversation
        retention.is_archived = True
        retention.archived_at = datetime.utcnow()
        
        # Compress if requested
        if compress:
            compressed_data = await self._compress_conversation(conversation)
            retention.compressed_size = len(compressed_data)
            retention.is_compressed = True
            # Store compressed data (in production, this would go to cold storage)
            retention.storage_location = f"archive/{user.id}/{conversation_id}.gz"
        
        # Update quota
        quota = await self._get_or_create_quota(db, user)
        quota.current_conversation_storage -= original_size
        if compress:
            quota.current_conversation_storage += retention.compressed_size
        
        await db.commit()
        await db.refresh(retention)
        
        # Clear cache
        cache_key = f"conversation:{user.id}:{conversation_id}"
        await cache_service.delete(cache_key)
        
        return retention
    
    async def restore_conversation(
        self,
        db: AsyncSession,
        user: User,
        conversation_id: str
    ) -> Conversation:
        """Restore an archived conversation"""
        
        retention = await db.execute(
            select(ConversationRetention).where(
                and_(
                    ConversationRetention.conversation_id == conversation_id,
                    ConversationRetention.user_id == user.id
                )
            )
        )
        retention = retention.scalar_one_or_none()
        
        if not retention or not retention.is_archived:
            raise ValueError("Conversation not archived")
        
        # Check storage quota
        quota = await self._get_or_create_quota(db, user)
        size_difference = retention.original_size - (retention.compressed_size or 0)
        
        if not await self._check_storage_available(quota, size_difference):
            raise StorageQuotaExceeded("Insufficient storage to restore conversation")
        
        # Restore
        retention.is_archived = False
        retention.archived_at = None
        retention.last_accessed_at = datetime.utcnow()
        
        # Update quota
        quota.current_conversation_storage += size_difference
        
        await db.commit()
        
        # Get and return conversation
        return await self.get_conversation_with_messages(db, user, conversation_id)
    
    async def delete_old_conversations(
        self,
        db: AsyncSession,
        user: User,
        days_old: Optional[int] = None
    ) -> int:
        """Delete conversations older than specified days"""
        
        quota = await self._get_or_create_quota(db, user)
        retention_days = days_old or quota.conversation_retention_days
        
        if retention_days <= 0:  # Unlimited retention
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Find conversations to delete
        query = select(Conversation).where(
            and_(
                Conversation.user_id == user.id,
                Conversation.updated_at < cutoff_date
            )
        ).outerjoin(ConversationRetention).where(
            or_(
                ConversationRetention.is_pinned == False,
                ConversationRetention.is_pinned == None
            )
        )
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        deleted_count = 0
        freed_storage = 0
        
        for conversation in conversations:
            # Calculate storage to free
            messages_query = select(Message).where(
                Message.conversation_id == conversation.id
            )
            messages_result = await db.execute(messages_query)
            messages = messages_result.scalars().all()
            
            for message in messages:
                freed_storage += len(message.content.encode('utf-8'))
                await db.delete(message)
            
            await db.delete(conversation)
            deleted_count += 1
        
        # Update quota
        quota.current_conversation_storage -= freed_storage
        quota.conversation_count -= deleted_count
        
        await db.commit()
        
        logger.info(f"Deleted {deleted_count} old conversations for user {user.id}, freed {freed_storage} bytes")
        
        return deleted_count
    
    async def get_storage_usage(
        self,
        db: AsyncSession,
        user: User
    ) -> Dict[str, Any]:
        """Get current storage usage and limits"""
        
        quota = await self._get_or_create_quota(db, user)
        
        # Calculate percentages
        conversation_usage_pct = (
            (quota.current_conversation_storage / quota.conversation_storage_limit * 100)
            if quota.conversation_storage_limit > 0 else 0
        )
        
        document_usage_pct = (
            (quota.current_document_storage / quota.document_storage_limit * 100)
            if quota.document_storage_limit > 0 else 0
        )
        
        return {
            "tier": quota.premium_tier,
            "is_premium": quota.is_premium,
            "conversation_storage": {
                "used": quota.current_conversation_storage,
                "limit": quota.conversation_storage_limit,
                "percentage": round(conversation_usage_pct, 2),
                "used_formatted": self._format_bytes(quota.current_conversation_storage),
                "limit_formatted": self._format_bytes(quota.conversation_storage_limit)
            },
            "document_storage": {
                "used": quota.current_document_storage,
                "limit": quota.document_storage_limit,
                "percentage": round(document_usage_pct, 2),
                "used_formatted": self._format_bytes(quota.current_document_storage),
                "limit_formatted": self._format_bytes(quota.document_storage_limit)
            },
            "retention": {
                "conversation_days": quota.conversation_retention_days,
                "document_days": quota.document_retention_days
            },
            "counts": {
                "conversations": quota.conversation_count,
                "messages": quota.message_count
            },
            "billing": {
                "monthly_fee": quota.monthly_fee,
                "overage_charges": quota.overage_charges,
                "last_billed": quota.last_billed_at.isoformat() if quota.last_billed_at else None
            }
        }
    
    async def upgrade_storage_tier(
        self,
        db: AsyncSession,
        user: User,
        tier: str
    ) -> UserStorageQuota:
        """Upgrade user's storage tier"""
        
        if tier not in STORAGE_TIERS:
            raise ValueError(f"Invalid tier: {tier}")
        
        quota = await self._get_or_create_quota(db, user)
        tier_config = STORAGE_TIERS[tier]
        
        # Update quota limits
        quota.premium_tier = tier
        quota.is_premium = tier != "free"
        quota.conversation_storage_limit = tier_config["conversation_storage"]
        quota.document_storage_limit = tier_config["document_storage"]
        quota.conversation_retention_days = tier_config["conversation_retention"]
        quota.monthly_fee = tier_config["monthly_fee"]
        
        if tier != "free":
            quota.premium_expires_at = datetime.utcnow() + timedelta(days=30)
        
        await db.commit()
        await db.refresh(quota)
        
        logger.info(f"Upgraded user {user.id} to {tier} tier")
        
        return quota
    
    # Helper methods
    
    async def _get_or_create_quota(
        self,
        db: AsyncSession,
        user: User
    ) -> UserStorageQuota:
        """Get or create user storage quota"""
        
        result = await db.execute(
            select(UserStorageQuota).where(
                UserStorageQuota.user_id == user.id
            )
        )
        quota = result.scalar_one_or_none()
        
        if not quota:
            # Create default quota
            tier_config = STORAGE_TIERS["free"]
            quota = UserStorageQuota(
                user_id=user.id,
                conversation_storage_limit=tier_config["conversation_storage"],
                document_storage_limit=tier_config["document_storage"],
                conversation_retention_days=tier_config["conversation_retention"]
            )
            db.add(quota)
            await db.commit()
            await db.refresh(quota)
        
        return quota
    
    async def _check_storage_available(
        self,
        quota: UserStorageQuota,
        required_bytes: int
    ) -> bool:
        """Check if storage is available"""
        return (
            quota.current_conversation_storage + required_bytes <= 
            quota.conversation_storage_limit
        )
    
    async def _auto_archive_old_conversations(
        self,
        db: AsyncSession,
        user: User,
        quota: UserStorageQuota
    ) -> int:
        """Automatically archive old conversations to free space"""
        
        # Find oldest non-pinned conversations
        query = select(Conversation).where(
            Conversation.user_id == user.id
        ).outerjoin(ConversationRetention).where(
            and_(
                or_(
                    ConversationRetention.is_archived == False,
                    ConversationRetention.is_archived == None
                ),
                or_(
                    ConversationRetention.is_pinned == False,
                    ConversationRetention.is_pinned == None
                )
            )
        ).order_by(Conversation.updated_at).limit(5)
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        archived_count = 0
        for conversation in conversations:
            try:
                await self.archive_conversation(db, user, str(conversation.id))
                archived_count += 1
            except Exception as e:
                logger.error(f"Failed to auto-archive conversation {conversation.id}: {e}")
        
        return archived_count
    
    async def _update_last_accessed(
        self,
        db: AsyncSession,
        conversation_id: str
    ) -> None:
        """Update last accessed timestamp"""
        
        retention = await db.execute(
            select(ConversationRetention).where(
                ConversationRetention.conversation_id == conversation_id
            )
        )
        retention = retention.scalar_one_or_none()
        
        if retention:
            retention.last_accessed_at = datetime.utcnow()
            await db.commit()
    
    async def _apply_retention_policies(
        self,
        db: AsyncSession,
        user: User,
        conversations: List[Conversation]
    ) -> None:
        """Apply retention policies to conversations"""
        
        quota = await self._get_or_create_quota(db, user)
        
        if quota.conversation_retention_days <= 0:
            return  # Unlimited retention
        
        cutoff_date = datetime.utcnow() - timedelta(days=quota.conversation_retention_days)
        
        for conversation in conversations:
            if conversation.updated_at < cutoff_date:
                # Check if pinned
                retention = await db.execute(
                    select(ConversationRetention).where(
                        ConversationRetention.conversation_id == conversation.id
                    )
                )
                retention = retention.scalar_one_or_none()
                
                if not retention or not retention.is_pinned:
                    # Schedule for deletion
                    if not retention:
                        retention = ConversationRetention(
                            conversation_id=str(conversation.id),
                            user_id=user.id,
                            original_size=0
                        )
                        db.add(retention)
                    
                    retention.scheduled_deletion_at = datetime.utcnow() + timedelta(days=7)
                    await db.commit()
    
    async def _compress_conversation(
        self,
        conversation: Conversation
    ) -> bytes:
        """Compress conversation data"""
        
        data = {
            "id": str(conversation.id),
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "metadata": conversation.conversation_metadata,
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.message_metadata,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in conversation.messages
            ]
        }
        
        json_data = json.dumps(data)
        return gzip.compress(json_data.encode('utf-8'))
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


class StorageQuotaExceeded(Exception):
    """Exception raised when storage quota is exceeded"""
    pass


# Singleton instance
chat_history_service = ChatHistoryService()

