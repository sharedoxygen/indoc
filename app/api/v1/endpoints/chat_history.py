"""
Chat history management endpoints with storage quotas
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.chat_history_service import chat_history_service, StorageQuotaExceeded
from app.schemas.conversation import ConversationResponse, ConversationListResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/history", response_model=ConversationListResponse)
async def get_chat_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's chat history with pagination
    """
    try:
        conversations, total = await chat_history_service.get_user_conversations(
            db, current_user, limit, offset, include_archived
        )
        
        return ConversationListResponse(
            conversations=[
                ConversationResponse.from_orm(conv) 
                for conv in conversations
            ],
            total=total,
            page=offset // limit + 1,
            page_size=limit
        )
    except Exception as e:
        import traceback
        logger.error(f"Error fetching chat history: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}"
        )


@router.get("/storage-usage")
async def get_storage_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current storage usage and limits
    """
    try:
        usage = await chat_history_service.get_storage_usage(db, current_user)
        return usage
    except Exception as e:
        logger.error(f"Error fetching storage usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch storage usage"
        )


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    compress: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Archive a conversation to free up storage
    """
    try:
        retention = await chat_history_service.archive_conversation(
            db, current_user, conversation_id, compress
        )
        return {
            "message": "Conversation archived successfully",
            "archived_at": retention.archived_at.isoformat(),
            "compressed": retention.is_compressed,
            "space_saved": retention.original_size - (retention.compressed_size or 0)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive conversation"
        )


@router.post("/conversations/{conversation_id}/restore")
async def restore_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Restore an archived conversation
    """
    try:
        conversation = await chat_history_service.restore_conversation(
            db, current_user, conversation_id
        )
        return {
            "message": "Conversation restored successfully",
            "conversation": ConversationResponse.from_orm(conversation)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except StorageQuotaExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error restoring conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore conversation"
        )


@router.delete("/cleanup")
async def cleanup_old_conversations(
    days_old: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete old conversations based on retention policy
    """
    try:
        deleted_count = await chat_history_service.delete_old_conversations(
            db, current_user, days_old
        )
        return {
            "message": f"Deleted {deleted_count} old conversations",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error cleaning up conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup conversations"
        )


@router.post("/upgrade-tier")
async def upgrade_storage_tier(
    tier: str = Query(..., regex="^(free|basic|pro|enterprise)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upgrade storage tier (would integrate with payment system)
    """
    try:
        quota = await chat_history_service.upgrade_storage_tier(
            db, current_user, tier
        )
        return {
            "message": f"Successfully upgraded to {tier} tier",
            "tier": tier,
            "conversation_storage_limit": quota.conversation_storage_limit,
            "document_storage_limit": quota.document_storage_limit,
            "retention_days": quota.conversation_retention_days,
            "monthly_fee": quota.monthly_fee
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error upgrading tier: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade tier"
        )


@router.post("/conversations/{conversation_id}/pin")
async def pin_conversation(
    conversation_id: str,
    pinned: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pin/unpin a conversation to prevent auto-deletion
    """
    try:
        from app.models.user_storage import ConversationRetention
        from sqlalchemy import select, and_
        
        # Get or create retention record
        result = await db.execute(
            select(ConversationRetention).where(
                and_(
                    ConversationRetention.conversation_id == conversation_id,
                    ConversationRetention.user_id == current_user.id
                )
            )
        )
        retention = result.scalar_one_or_none()
        
        if not retention:
            # Verify conversation exists and belongs to user
            from app.models.conversation import Conversation
            conv_result = await db.execute(
                select(Conversation).where(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.user_id == current_user.id
                    )
                )
            )
            conversation = conv_result.scalar_one_or_none()
            
            if not conversation:
                raise ValueError("Conversation not found")
            
            retention = ConversationRetention(
                conversation_id=conversation_id,
                user_id=current_user.id,
                original_size=0,
                is_pinned=pinned
            )
            db.add(retention)
        else:
            retention.is_pinned = pinned
        
        # Will be committed by get_db dependency
        
        return {
            "message": f"Conversation {'pinned' if pinned else 'unpinned'} successfully",
            "conversation_id": conversation_id,
            "is_pinned": pinned
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error pinning conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pin conversation"
        )
