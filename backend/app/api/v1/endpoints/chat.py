"""
Chat API endpoints for document conversations

Enterprise-grade chat system with comprehensive error handling,
logging, monitoring, and diagnostic capabilities.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from jose import JWTError, jwt
from app.core.config import settings
import json
import asyncio
import logging
import time

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate, ConversationResponse, ConversationListResponse,
    ChatRequest, ChatResponse, MessageResponse
)
from app.services.async_conversation_service import AsyncConversationService
from app.services.chat_diagnostics import diagnose_chat_system
from app.core.websocket_manager import WebSocketManager

router = APIRouter()
manager = WebSocketManager()
logger = logging.getLogger(__name__)


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation"""
    service = AsyncConversationService(db)
    
    result = await service.create_conversation(
        user_id=current_user.id,
        tenant_id=getattr(current_user, 'tenant_id', None),
        document_ids=[conversation.document_id] if conversation.document_id else None,
        title=conversation.title
    )
    
    return ConversationResponse.from_orm(result)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's conversations"""
    # For now, return empty list until list_conversations is implemented in async service
    return ConversationListResponse(
        conversations=[],
        total=0,
        page=page,
        page_size=page_size
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific conversation with messages"""
    service = AsyncConversationService(db)
    
    conversation = await service.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        tenant_id=getattr(current_user, 'tenant_id', None)
    )
    
    # Load messages
    messages = await service.get_conversation_history(conversation_id)
    conversation.messages = messages
    
    return ConversationResponse.from_orm(conversation)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enterprise-grade chat endpoint with comprehensive error handling
    
    This endpoint processes chat messages with document context,
    maintains conversation history, and provides detailed error reporting.
    """
    # Start performance monitoring
    start_time = time.time()
    
    try:
        logger.info(f"Chat request from user {current_user.email}: {chat_request.message[:50]}...")
        
        # Ensure user has tenant_id (refresh from DB if needed)
        if not hasattr(current_user, 'tenant_id') or current_user.tenant_id is None:
            # Refresh user data from database
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.id == current_user.id)
            )
            current_user = result.scalar_one_or_none()
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User authentication failed"
                )
        
        # Initialize conversation service
        service = AsyncConversationService(db)
        
        # PRODUCTION-GRADE INTENT DETECTION AND SCOPE HANDLING
        normalized_msg = (chat_request.message or "").lower().strip()
        
        # Core analytics patterns - comprehensive detection
        analytics_patterns = [
            # Summarization patterns
            "summarize", "summary", "overview", "analyze", "breakdown", "categorize",
            # Grouping patterns  
            "by category", "by type", "by file type", "group by", "categorized", "grouped",
            # Analysis patterns
            "count", "how many", "number of", "total documents", "breakdown",
            # Scope patterns
            "all documents", "all files", "entire library", "complete collection"
        ]
        
        # Production-grade intent detection
        is_analytics_intent = any(pattern in normalized_msg for pattern in analytics_patterns)
        
        # Context-aware scope detection
        context_data = chat_request.context_data or {}
        has_selected_docs = context_data.get('selected_documents_count', 0) > 0
        is_all_accessible = context_data.get('scope') == 'all_accessible'
        
        # PRODUCTION RULE: If analytics intent detected, ALWAYS execute analytics
        # Never ask for clarification when scope is clear
        should_execute_analytics = is_analytics_intent
        
        # PRODUCTION MONITORING: Log analytics intent detection
        if is_analytics_intent:
            logger.info(f"Analytics intent detected for user {current_user.id}: '{chat_request.message}' -> execute: {should_execute_analytics}")
        
        # PRODUCTION-GRADE ANALYTICS EXECUTION
        if should_execute_analytics:
            from app.core.document_scope import get_effective_document_ids
            from app.models import Document
            from sqlalchemy import select, func
            
            # PRODUCTION-GRADE SCOPE RESOLUTION
            try:
                # Convert document_ids to set of ints if provided, otherwise None
                selected_ids = None
                if chat_request.document_ids is not None and len(chat_request.document_ids) > 0:
                    selected_ids = {int(doc_id) for doc_id in chat_request.document_ids}
                
                # Get effective document IDs with comprehensive error handling
                effective_ids = await get_effective_document_ids(db, current_user, selected_ids)
                
                # PRODUCTION RULE: Never return empty scope - always provide fallback
                if not effective_ids:
                    # Fallback: Get all accessible documents for user
                    logger.warning(f"No documents found for user {current_user.id}, attempting fallback")
                    effective_ids = await get_effective_document_ids(db, current_user, None)
                    
                if not effective_ids:
                    response_text = "I couldn't find any documents in your current scope. Please check your access permissions or contact your administrator."
                    logger.error(f"No accessible documents found for user {current_user.id}")
                else:
                    # Get comprehensive analytics data
                    total_docs = len(effective_ids)
                    
                    # PRODUCTION-GRADE ANALYTICS QUERIES with error handling
                    try:
                        # Get breakdown by file type
                        breakdown_result = await db.execute(
                            select(Document.file_type, func.count(Document.id), func.sum(Document.file_size))
                            .where(Document.id.in_(effective_ids))
                            .group_by(Document.file_type)
                            .order_by(func.count(Document.id).desc())
                        )
                        breakdown = breakdown_result.all()
                        
                        # Get breakdown by category (if available in metadata)
                        category_result = await db.execute(
                            select(
                                func.coalesce(Document.custom_metadata['category'], 'Uncategorized').label('category'),
                                func.count(Document.id),
                                func.sum(Document.file_size)
                            )
                            .where(Document.id.in_(effective_ids))
                            .group_by('category')
                            .order_by(func.count(Document.id).desc())
                        )
                        category_breakdown = category_result.all()
                        
                        # Get size analysis
                        size_result = await db.execute(
                            select(Document.title, Document.file_type, Document.file_size)
                            .where(Document.id.in_(effective_ids))
                            .order_by(Document.file_size.desc())
                            .limit(10)
                        )
                        largest_docs = size_result.all()
                        
                    except Exception as e:
                        logger.error(f"Analytics query failed for user {current_user.id}: {e}")
                        # Fallback to basic count
                        breakdown = []
                        category_breakdown = []
                        largest_docs = []
                
                    # PRODUCTION-GRADE RESPONSE GENERATION
                    response_parts = [f"📊 **Document Library Analysis** ({total_docs:,} documents)"]
                    
                    # Determine analysis type based on user intent
                    wants_category = any(phrase in normalized_msg for phrase in ["by category", "categorized", "category"])
                    wants_type = any(phrase in normalized_msg for phrase in ["by type", "by file type", "file type"])
                    
                    # Show category breakdown if requested or if categories exist
                    if wants_category or category_breakdown:
                        if category_breakdown:
                            response_parts.append("\n**📂 Breakdown by Category:**")
                            for category, count, total_size in category_breakdown:
                                size_mb = (total_size or 0) / (1024 * 1024)
                                response_parts.append(f"• **{category.title()}**: {count:,} documents ({size_mb:.1f} MB)")
                        else:
                            response_parts.append("\n**📂 Categories:** No categories assigned to documents")
                    
                    # Show file type breakdown if requested or if no categories
                    if wants_type or breakdown or not category_breakdown:
                        if breakdown:
                            response_parts.append("\n**📁 Breakdown by File Type:**")
                            for file_type, count, total_size in breakdown:
                                size_mb = (total_size or 0) / (1024 * 1024)
                                response_parts.append(f"• **{file_type.upper()}**: {count:,} documents ({size_mb:.1f} MB)")
                    
                    # Show largest documents if available
                    if largest_docs:
                        response_parts.append("\n**📈 Largest Documents:**")
                        for title, file_type, size in largest_docs[:5]:
                            size_mb = (size or 0) / (1024 * 1024)
                            response_parts.append(f"• {title} ({file_type}) - {size_mb:.1f} MB")
                    
                    # Add context-aware insights
                    scope_info = "selected documents" if selected_ids else "all accessible documents"
                    response_parts.append(f"\n*Analysis based on {scope_info}*")
                    
                    # Add smart follow-up suggestions
                    response_parts.append("\n**💡 Suggested Next Steps:**")
                    if len(breakdown) > 1:
                        response_parts.append("• Dive deeper into the largest category")
                        response_parts.append("• Compare document types side by side")
                    if len(largest_docs) > 0:
                        response_parts.append("• Analyze content of the largest documents")
                    response_parts.append("• Search for specific topics across documents")
                    response_parts.append("• Get trends over time")
                    
                    response_text = "\n".join(response_parts)
                    
            except Exception as e:
                logger.error(f"Analytics execution failed for user {current_user.id}: {e}")
                response_text = f"I encountered an error while analyzing your documents. Please try again or contact support if the issue persists."
            
            # Create conversation and messages
            if chat_request.conversation_id:
                conversation = await service.get_conversation(
                    chat_request.conversation_id,
                    current_user.id,
                    current_user.tenant_id
                )
            else:
                conversation = await service.create_conversation(
                    user_id=current_user.id,
                    tenant_id=current_user.tenant_id,
                    document_ids=chat_request.document_ids,
                )
            
            # Add messages
            await service.add_message(conversation.id, "user", chat_request.message)
            assistant_msg = await service.add_message(
                conversation.id, 
                "assistant", 
                response_text,
                metadata={
                    "intent": "analytics_proactive", 
                    "total_docs": total_docs,
                    "scope": "selected" if selected_ids else "all_accessible"
                }
            )
            
            return ChatResponse(
                conversation_id=conversation.id,
                message=response_text,
                metadata={
                    "intent": "analytics_proactive", 
                    "total_docs": total_docs,
                    "scope": "selected" if selected_ids else "all_accessible"
                }
            )
        
        # Handle count queries directly
        if is_count_query:
            from app.core.document_scope import get_effective_document_ids
            from app.models import Document
            from sqlalchemy import select, func
            
            # Get effective document IDs for the user
            # Convert document_ids to set of ints if provided, otherwise None
            selected_ids = None
            if chat_request.document_ids is not None and len(chat_request.document_ids) > 0:
                selected_ids = {int(doc_id) for doc_id in chat_request.document_ids}
            
            effective_ids = await get_effective_document_ids(db, current_user, selected_ids)
            
            if is_breakdown_query and effective_ids:
                # Get count by file type
                result = await db.execute(
                    select(Document.file_type, func.count(Document.id).label('count'))
                    .where(Document.id.in_(effective_ids))
                    .group_by(Document.file_type)
                    .order_by(func.count(Document.id).desc())
                )
                breakdown = result.all()
                
                # Format response
                total = sum(row.count for row in breakdown)
                response_text = f"You have access to {total:,} document(s) in total.\n\nBreakdown by file type:\n"
                for row in breakdown:
                    file_type = row.file_type or "Unknown"
                    response_text += f"- {file_type.upper()}: {row.count:,} documents\n"
                
                # Create a direct response
                from app.schemas.conversation import ChatResponse
                from uuid import uuid4
                
                # Get or create conversation
                if chat_request.conversation_id:
                    conversation = await service.get_conversation(
                        chat_request.conversation_id,
                        current_user.id,
                        current_user.tenant_id
                    )
                else:
                    conversation = await service.create_conversation(
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        document_ids=chat_request.document_ids,
                    )
                
                # Add messages
                await service.add_message(conversation.id, "user", chat_request.message)
                assistant_msg = await service.add_message(
                    conversation.id, 
                    "assistant", 
                    response_text,
                    metadata={"intent": "count_breakdown", "total_docs": total}
                )
                
                return ChatResponse(
                    conversation_id=conversation.id,
                    message=response_text,
                    metadata={"intent": "count_breakdown", "total_docs": total}
                )
            
            elif effective_ids:
                # Simple count
                total = len(effective_ids)
                response_text = f"You have access to {total:,} document(s) in total."
                
                # Create a direct response
                from app.schemas.conversation import ChatResponse
                from uuid import uuid4
                
                # Get or create conversation
                if chat_request.conversation_id:
                    conversation = await service.get_conversation(
                        chat_request.conversation_id,
                        current_user.id,
                        current_user.tenant_id
                    )
                else:
                    conversation = await service.create_conversation(
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        document_ids=chat_request.document_ids,
                    )
                
                # Add messages
                await service.add_message(conversation.id, "user", chat_request.message)
                assistant_msg = await service.add_message(
                    conversation.id, 
                    "assistant", 
                    response_text,
                    metadata={"intent": "count_simple", "total_docs": total}
                )
                
                return ChatResponse(
                    conversation_id=conversation.id,
                    message=response_text,
                    metadata={"intent": "count_simple", "total_docs": total}
                )
        
        # For all other queries, process through normal chat flow with library stats
        response = await service.process_chat_message(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            chat_request=chat_request
        )
        
        # Enhance response with library stats if not already included
        if hasattr(response, 'response') and response.response:
            # Add library stats to context for conversational awareness
            from app.core.document_scope import get_effective_document_ids
            from app.models import Document
            from sqlalchemy import select, func
            
            effective_ids = await get_effective_document_ids(db, current_user)
            if effective_ids:
                # Get total count
                count_result = await db.execute(
                    select(func.count()).select_from(
                        select(Document.id).where(Document.id.in_(effective_ids)).subquery()
                    )
                )
                total_docs = int(count_result.scalar() or 0)
                
                # Get breakdown by type
                breakdown_result = await db.execute(
                    select(Document.file_type, func.count(Document.id))
                    .where(Document.id.in_(effective_ids))
                    .group_by(Document.file_type)
                    .order_by(func.count(Document.id).desc())
                )
                breakdown = breakdown_result.all()
                
                # Add library stats to response metadata
                if not response.response.metadata:
                    response.response.metadata = {}
                
                # Determine scope based on document selection
                scope = "selected" if (chat_request.document_ids and len(chat_request.document_ids) > 0) else "all_accessible"

                response.response.metadata.update({
                    "library_stats": {
                        "total_documents": total_docs,
                        "breakdown": {ft: count for ft, count in breakdown}
                    },
                    "scope": scope
                })
        
        # Log performance metrics
        elapsed_time = time.time() - start_time
        logger.info(f"Chat response generated in {elapsed_time:.2f}s for user {current_user.email}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for user {current_user.email}: {str(e)}", exc_info=True)
        
        # Return a user-friendly error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your message. Please try again."
        )


@router.get("/diagnostics")
async def chat_diagnostics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Comprehensive chat system diagnostics
    
    Industry-standard health check endpoint for monitoring
    and troubleshooting chat system components.
    """
    try:
        # Only allow admin users to access diagnostics
        if getattr(current_user.role, 'value', current_user.role) != 'Admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Diagnostics access restricted to administrators"
            )
        
        logger.info(f"Chat diagnostics requested by admin: {current_user.email}")
        
        # Run comprehensive diagnostics
        diagnostics_result = await diagnose_chat_system(db, current_user.id)
        
        return {
            "status": "diagnostics_complete",
            "timestamp": time.time(),
            "requested_by": current_user.email,
            "system_health": diagnostics_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostics system error: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation"""
    service = AsyncConversationService(db)
    
    await service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    return {"message": "Conversation deleted successfully"}


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, str(conversation_id))
    
    try:
        # Authenticate user from WebSocket
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        token = auth_data.get("token")
        
        # Validate token and get user (simplified - implement proper auth)
        if not token:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Authentication required"
            }))
            await manager.disconnect(websocket, str(conversation_id))
            return
        
        # Get user from token (validate JWT similar to deps.get_current_user)
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id_str = payload.get("sub")
            if user_id_str is None:
                raise JWTError("Missing subject")
            user_id = int(user_id_str)
        except (JWTError, ValueError):
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Authentication failed"
            }))
            await manager.disconnect(websocket, str(conversation_id))
            return
        result = await db.execute(select(User).where(User.id == user_id))
        current_user = result.scalar_one_or_none()
        if not current_user:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "User not found"
            }))
            await manager.disconnect(websocket, str(conversation_id))
            return
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "conversation_id": str(conversation_id)
        }))
        
        # Create service instance  
        service = AsyncConversationService(db)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                # Process the message
                chat_request = ChatRequest(
                    message=message_data.get("content"),
                    conversation_id=conversation_id,
                    stream=True,
                    document_ids=message_data.get("document_ids"),
                    model=message_data.get("model"),
                    context_data=message_data.get("context_data")
                )
                
                # Send typing indicator
                await websocket.send_text(json.dumps({
                    "type": "typing",
                    "conversation_id": str(conversation_id)
                }))
                
                # Process and get response
                try:
                    # For streaming response, we'd implement chunked sending
                    response = await service.process_chat_message(
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                        chat_request=chat_request
                    )
                    
                    # Send the response
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "conversation_id": str(conversation_id),
                        "message": {
                            "id": str(response.response.id),
                            "role": "assistant",
                            "content": response.response.content,
                            "created_at": response.response.created_at.isoformat()
                        }
                    }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
            
            elif message_data.get("type") == "ping":
                # Handle ping/pong for connection keep-alive
                await websocket.send_text(json.dumps({
                    "type": "pong"
                }))
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, str(conversation_id))
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
        await manager.disconnect(websocket, str(conversation_id))