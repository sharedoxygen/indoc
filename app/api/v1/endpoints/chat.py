"""
Chat API endpoints for document conversations
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Body
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import uuid4
from datetime import datetime
import json
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate, ConversationResponse, ConversationListResponse,
    ChatRequest, ChatResponse, MessageResponse
)
from app.services.conversation_service import ConversationService
from app.services.search_service import SearchService
from app.services.llm_service import LLMService
from app.services.chat_history_service import chat_history_service, StorageQuotaExceeded
from app.models.conversation import Conversation, Message
from app.core.context_manager import context_manager
from app.core.websocket_manager import WebSocketManager
from app.core.document_scope import get_effective_document_ids
from app.models.document import Document

router = APIRouter()
manager = WebSocketManager()


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation with optional document attachment"""
    # Determine tenant_id, without generating a new one for filtering
    tenant_id = current_user.tenant_id or uuid4()
    # Manually create conversation record using integer document_id
    new_conv = Conversation(
        id=uuid4(),
        tenant_id=tenant_id,
        user_id=current_user.id,
        document_id=conversation.document_id,
        title=conversation.title or ""
    )
    db.add(new_conv)
    await db.flush()  # Flush to get the ID without committing yet
    # Return response without loading messages
    # Will be committed by get_db dependency
    return ConversationResponse(
        id=new_conv.id,
        tenant_id=new_conv.tenant_id,
        user_id=new_conv.user_id,
        title=new_conv.title,
        document_id=new_conv.document_id,
        metadata=new_conv.conversation_metadata or {},
        created_at=new_conv.created_at,
        updated_at=new_conv.updated_at,
        messages=[]
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's conversations with proper tenant isolation"""
    try:
        # Handle tenant_id for multi-tenant isolation
        user_tenant_id = getattr(current_user, 'tenant_id', None)
        
        # Build query with proper tenant isolation
        query = select(Conversation).where(Conversation.user_id == current_user.id)
        
        # Multi-tenant: filter by tenant_id if user has one
        # Single-tenant: show all conversations for the user
        if user_tenant_id:
            query = query.where(
                (Conversation.tenant_id == user_tenant_id) | 
                (Conversation.tenant_id.is_(None))  # Include legacy conversations
            )
        
        # Add pagination and ordering
        query = query.order_by(Conversation.updated_at.desc())
        
        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0
        
        # Get conversations with pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        # Convert to response format
        conversation_responses = []
        for conv in conversations:
            # Load messages for each conversation
            messages_result = await db.execute(
                select(Message).where(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
            )
            messages = messages_result.scalars().all()
            
            conversation_responses.append(ConversationResponse(
                id=conv.id,
                tenant_id=conv.tenant_id,
                user_id=conv.user_id,
                title=conv.title,
                document_id=conv.document_id,
                metadata=conv.conversation_metadata or {},
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=[MessageResponse.from_orm(msg) for msg in messages]
            ))
        
        return ConversationListResponse(
            conversations=conversation_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing conversations for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific conversation with messages and proper tenant isolation"""
    try:
        user_tenant_id = getattr(current_user, 'tenant_id', None)
        
        # Build query with tenant isolation
        query = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        
        # Add tenant filtering if user has tenant_id
        if user_tenant_id:
            query = query.where(
                (Conversation.tenant_id == user_tenant_id) |
                (Conversation.tenant_id.is_(None))  # Include legacy conversations
            )
        
        result = await db.execute(query)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Load messages for this conversation
        messages_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = messages_result.scalars().all()
        
        return ConversationResponse(
            id=conversation.id,
            tenant_id=conversation.tenant_id,
            user_id=conversation.user_id,
            title=conversation.title,
            document_id=conversation.document_id,
            metadata=conversation.conversation_metadata or {},
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[MessageResponse.from_orm(msg) for msg in messages]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message and get response (hardened path)."""
    try:
        # Retrieve user tenant_id; do not generate a new one for filtering
        db_tenant_id = current_user.tenant_id

        # Get or create conversation with proper tenant isolation
        conversation: Conversation | None = None
        if chat_request.conversation_id:
            # Load existing conversation with tenant check
            query = select(Conversation).where(
                Conversation.id == chat_request.conversation_id,
                Conversation.user_id == current_user.id
            )
            
            # Add tenant filtering only if user has a tenant_id
            if db_tenant_id is not None:
                query = query.where(
                    (Conversation.tenant_id == db_tenant_id) |
                    (Conversation.tenant_id.is_(None))  # Include legacy conversations
                )
            
            result = await db.execute(query)
            conversation = result.scalar_one_or_none()
            if conversation is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
            
            # ALWAYS update conversation metadata with current document_ids
            current_metadata = conversation.conversation_metadata or {}
            if chat_request.document_ids:
                current_metadata["document_ids"] = [str(d) for d in chat_request.document_ids]
            # Keep existing document_ids if none provided in this request
            elif "document_ids" not in current_metadata:
                current_metadata["document_ids"] = []
            
            conversation.conversation_metadata = current_metadata
            conversation.updated_at = datetime.utcnow()
            # Will be committed by get_db dependency
                
        else:
            # Create new conversation
            conversation = Conversation(
                id=uuid4(),
                tenant_id=db_tenant_id or uuid4(),
                user_id=current_user.id,
                document_id=None,
                title=chat_request.message[:60] if chat_request.message else "New Conversation",
                conversation_metadata={"document_ids": [str(d) for d in (chat_request.document_ids or [])]}
            )
            db.add(conversation)
            await db.flush()  # Flush to get conversation ID
            # Will be committed by get_db dependency

        # Persist user message with document context metadata
        user_message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role="user",
            content=chat_request.message,
            message_metadata={
                "document_ids": [str(d) for d in (chat_request.document_ids or [])]
            }
        )
        db.add(user_message)
        await db.flush()  # Flush to get message ID
        # Will be committed by get_db dependency

        # Check for special intent queries FIRST (before any context building)
        normalized_q = (chat_request.message or "").lower().strip()
        logger.info(f"Checking for intent in query: '{normalized_q}'")
        
        # Robust regex-based detection for count queries
        count_patterns = [
            r"\bhow\s+many\b",  # Simplified - just "how many" is enough
            r"\b(number|count|quantity)\s+(of|total)",
            r"\bdocument[s]?\s+(count|total)",
            r"\bcount\b.*\bdocument",
            r"\btotal\s+document"
        ]
        is_count_question = any(re.search(p, normalized_q) for p in count_patterns)
        
        # Check if user wants breakdown by category/type
        is_breakdown_query = any(
            phrase in normalized_q for phrase in [
                "by category", "by type", "by file type", "breakdown", 
                "categorized", "grouped by", "group by", "per type", "by media type"
            ]
        )
        
        logger.info(f"Intent detection - Count: {is_count_question}, Breakdown: {is_breakdown_query}")
        
        # Handle SIMPLE count queries (not multi-part complex questions)
        # Check if this is a simple count or a complex multi-part query
        # Consider punctuation variants (e.g., "also, ...") and explicit multi-part verbs
        is_multipart_query = (
            bool(re.search(r"\b(also|and|then)\b", normalized_q))
            or "after that" in normalized_q
            or "followed by" in normalized_q
            or "sort by" in normalized_q
            or "order by" in normalized_q
            or "organize by" in normalized_q
            or "summarize" in normalized_q
        )
        
        # Only use rule-based count for simple, single-purpose count questions
        if is_count_question and not is_multipart_query:
            logger.info("Processing count query")
            meta = conversation.conversation_metadata or {}
            doc_ids = chat_request.document_ids or meta.get("document_ids", [])
            total_docs = 0
            breakdown_text = ""
            
            if doc_ids:
                total_docs = len(set(str(d) for d in doc_ids))
                # Get breakdown if requested
                if is_breakdown_query:
                    breakdown_result = await db.execute(
                        select(Document.file_type, func.count(Document.id))
                        .where(Document.uuid.in_([str(d) for d in doc_ids]))
                        .group_by(Document.file_type)
                    )
                    breakdown = breakdown_result.all()
                    if breakdown:
                        breakdown_text = "\n\nBreakdown by type:\n" + "\n".join([f"- {ft or 'Unknown'}: {count}" for ft, count in breakdown])
            else:
                effective_ids = await get_effective_document_ids(db, current_user, None)
                if effective_ids:
                    # Use DB count for accuracy
                    count_result = await db.execute(
                        select(func.count()).select_from(
                            select(Document.id).where(Document.id.in_(effective_ids)).subquery()
                        )
                    )
                    total_docs = int(count_result.scalar() or 0)
                    
                    # Get breakdown if requested
                    if is_breakdown_query and total_docs > 0:
                        breakdown_result = await db.execute(
                            select(Document.file_type, func.count(Document.id))
                            .where(Document.id.in_(effective_ids))
                            .group_by(Document.file_type)
                            .order_by(func.count(Document.id).desc())
                        )
                        breakdown = breakdown_result.all()
                        if breakdown:
                            breakdown_text = "\n\nBreakdown by file type:\n" + "\n".join([f"- {ft.upper() if ft else 'Unknown'}: {count:,} documents" for ft, count in breakdown])
            
            assistant_text = f"You have access to {total_docs:,} document(s) in total.{breakdown_text}"

            assistant_message = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_text,
                message_metadata={
                    "context_used": False,
                    "model_used": "rule-based",
                    "token_budget": 0,
                    "intent": "count_breakdown" if is_breakdown_query else "count_simple",
                    "total_docs": total_docs
                }
            )
            db.add(assistant_message)
            await db.flush()  # Flush to get message ID
            # Will be committed by get_db dependency

            user_msg_resp = MessageResponse.from_orm(user_message)
            user_msg_resp.metadata["document_ids"] = [str(d) for d in (chat_request.document_ids or [])]
            assistant_msg_resp = MessageResponse.from_orm(assistant_message)
            return ChatResponse(
                conversation_id=conversation.id,
                message=user_msg_resp,
                response=assistant_msg_resp
            )
        
        # Library analytics intent: summarize by media type and category, sorted by size
        wants_media_type = any(
            phrase in normalized_q for phrase in [
                "by media type", "by file type", "per type", "group by type", "group by file type"
            ]
        )
        wants_category = any(
            phrase in normalized_q for phrase in [
                "by category", "within the particular media type", "within each type", "by classification"
            ]
        )
        wants_sort_by_size = any(
            phrase in normalized_q for phrase in [
                "sort by content size", "sorted by size", "order by size", "largest first", "by total size"
            ]
        )
        is_analytics_intent = (wants_media_type and wants_category) or (wants_media_type and wants_sort_by_size)

        # Conversation-aware fallback: if the previous assistant response performed
        # library analytics, treat follow-ups like "summarize each by category" as
        # analytics requests even if the user omitted "by media type".
        if not is_analytics_intent:
            try:
                # Look for the most recent ASSISTANT message (not the just-saved user message)
                prev_res = await db.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation.id,
                        Message.role == "assistant"
                    )
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                prev_msg = prev_res.scalars().first()
                prev_intent = (prev_msg.message_metadata or {}).get("intent") if prev_msg else None
                if prev_intent in {"library_analytics", "count_breakdown", "count_simple"}:
                    if any(kw in normalized_q for kw in ["summarize", "each", "category", "by category", "breakdown"]):
                        is_analytics_intent = True
                        # Default to media-type grouping when carrying context forward
                        if not wants_media_type:
                            wants_media_type = True
            except Exception:
                pass
        
        if is_analytics_intent:
            # Compute aggregates within current scope
            meta = conversation.conversation_metadata or {}
            selected_doc_uuids = chat_request.document_ids or meta.get("document_ids", [])
            
            # Helper to format sizes
            def _format_size(num_bytes: int) -> str:
                try:
                    size = float(num_bytes or 0)
                except Exception:
                    size = 0.0
                units = ["B", "KB", "MB", "GB", "TB"]
                i = 0
                while size >= 1024 and i < len(units) - 1:
                    size /= 1024.0
                    i += 1
                return f"{size:,.1f} {units[i]}"
            
            # Determine scope filter
            if selected_doc_uuids:
                base_q = (
                    select(
                        Document.file_type,
                        Document.classification,
                        func.count(Document.id).label("doc_count"),
                        func.sum(Document.file_size).label("total_size"),
                    )
                    .where(Document.uuid.in_([str(d) for d in selected_doc_uuids]))
                    .group_by(Document.file_type, Document.classification)
                )
                total_count_q = select(func.count()).select_from(
                    select(Document.id).where(Document.uuid.in_([str(d) for d in selected_doc_uuids])).subquery()
                )
            else:
                effective_ids = await get_effective_document_ids(db, current_user, None)
                if not effective_ids:
                    effective_ids = set()
                base_q = (
                    select(
                        Document.file_type,
                        Document.classification,
                        func.count(Document.id).label("doc_count"),
                        func.sum(Document.file_size).label("total_size"),
                    )
                    .where(Document.id.in_(effective_ids))
                    .group_by(Document.file_type, Document.classification)
                )
                total_count_q = select(func.count()).select_from(
                    select(Document.id).where(Document.id.in_(effective_ids)).subquery()
                )
            
            # Order primarily by size desc so larger media types appear first
            result = await db.execute(base_q.order_by(func.sum(Document.file_size).desc()))
            rows = result.all()
            total_count_res = await db.execute(total_count_q)
            total_docs = int(total_count_res.scalar() or 0)
            
            # Organize aggregates by file_type with per-category breakdown
            from collections import defaultdict
            type_totals = defaultdict(lambda: {"doc_count": 0, "total_size": 0})
            type_categories = defaultdict(lambda: defaultdict(lambda: {"doc_count": 0, "total_size": 0}))
            for file_type, classification, doc_count, total_size in rows:
                ft = (file_type or "UNKNOWN").upper()
                cat = getattr(classification, "value", str(classification) if classification is not None else "UNKNOWN")
                dc = int(doc_count or 0)
                ts = int(total_size or 0)
                type_totals[ft]["doc_count"] += dc
                type_totals[ft]["total_size"] += ts
                type_categories[ft][cat]["doc_count"] += dc
                type_categories[ft][cat]["total_size"] += ts
            
            # Sort media types by total size desc
            sorted_types = sorted(type_totals.items(), key=lambda kv: kv[1]["total_size"], reverse=True)
            
            lines = [f"You have access to {total_docs:,} document(s) in total."]
            if not rows:
                lines.append("No documents found in the current scope.")
            else:
                lines.append("\nSummary by media type (sorted by total content size):")
                for ft, agg in sorted_types:
                    lines.append(
                        f"- {ft}: {agg['doc_count']:,} documents, total {_format_size(agg['total_size'])}"
                    )
                    # Within each type, list categories by size desc
                    categories_sorted = sorted(
                        type_categories[ft].items(), key=lambda kv: kv[1]["total_size"], reverse=True
                    )
                    for cat, cagg in categories_sorted:
                        lines.append(
                            f"  - {cat}: {cagg['doc_count']:,} documents, {_format_size(cagg['total_size'])}"
                        )
            assistant_text = "\n".join(lines)
            
            assistant_message = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_text,
                message_metadata={
                    "context_used": False,
                    "model_used": "analytics",
                    "token_budget": 0,
                    "intent": "library_analytics",
                    "sorted_by": "total_size",
                },
            )
            db.add(assistant_message)
            await db.flush()  # Flush to get message ID
            # Will be committed by get_db dependency

            user_msg_resp = MessageResponse.from_orm(user_message)
            user_msg_resp.metadata["document_ids"] = [str(d) for d in (chat_request.document_ids or [])]
            assistant_msg_resp = MessageResponse.from_orm(assistant_message)
            return ChatResponse(
                conversation_id=conversation.id,
                message=user_msg_resp,
                response=assistant_msg_resp,
            )
        
        # Determine model and user role for normal processing
        selected_model = getattr(chat_request, 'model', None) or "gpt-oss:20b"
        user_role = getattr(current_user.role, "value", current_user.role) if hasattr(current_user.role, "value") else str(current_user.role)
        
        # Build intelligent context with proper sizing
        try:
            meta = conversation.conversation_metadata or {}
            doc_ids = chat_request.document_ids or meta.get("document_ids", [])
            logger.info(f"Chat doc_ids: {doc_ids}")
            
            # Extract keyword(s) for summarize-by-keyword intent
            keyword_query: Optional[str] = None
            if "summarize" in normalized_q and any(w in normalized_q for w in ["include", "including", "contains", "containing", "keyword"]):
                # Prefer quoted keywords first
                quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", chat_request.message or "")
                flat = [q for pair in quoted for q in pair if q]
                if flat:
                    keyword_query = " ".join(flat).strip()
                else:
                    # Heuristic: take words after 'includes'/'containing' up to punctuation
                    m = re.search(r"(?:include|including|contains|containing)\s+([\w\- ]{3,50})", normalized_q)
                    if m:
                        keyword_query = m.group(1).strip()

            # Intent: related documents (relationships)
            is_related_docs_question = any(
                phrase in normalized_q for phrase in [
                    "what documents are you related to",
                    "documents you are related to",
                    "related documents",
                    "what docs are you related to"
                ]
            )

            if is_related_docs_question:
                # Fetch recent/active documents for the user scope and present as relationships list
                effective_ids = await get_effective_document_ids(db, current_user, None)
                if not effective_ids:
                    assistant_text = "I couldn't find any documents in your current scope."
                else:
                    rel_query = (
                        select(Document)
                        .where(Document.id.in_(effective_ids))
                        .order_by(Document.updated_at.desc())
                        .limit(15)
                    )
                    rel_result = await db.execute(rel_query)
                    rel_docs = rel_result.scalars().all()
                    if not rel_docs:
                        assistant_text = "I couldn't find related documents in your scope."
                    else:
                        lines = ["Here are documents related to your activity/scope:"]
                        for d in rel_docs:
                            created = d.created_at.isoformat() if getattr(d, 'created_at', None) else ''
                            lines.append(f"- {d.title or d.filename} ({d.file_type}) {created}")
                        assistant_text = "\n".join(lines)

                assistant_message = Message(
                    id=uuid4(),
                    conversation_id=conversation.id,
                    role="assistant",
                    content=assistant_text,
                    message_metadata={
                        "context_used": False,
                        "model_used": "relationship-list",
                        "token_budget": 0,
                        "scope": "selected" if (chat_request.document_ids or meta.get("document_ids")) else "all_accessible"
                    }
                )
                db.add(assistant_message)
                await db.flush()  # Flush to get message ID
                # Will be committed by get_db dependency

                user_msg_resp = MessageResponse.from_orm(user_message)
                user_msg_resp.metadata["document_ids"] = [str(d) for d in (chat_request.document_ids or [])]
                assistant_msg_resp = MessageResponse.from_orm(assistant_message)
                return ChatResponse(
                    conversation_id=conversation.id,
                    message=user_msg_resp,
                    response=assistant_msg_resp
                )

            # Get documents
            documents = []
            search = SearchService(db)
            if doc_ids:
                documents = await search.get_document_content_for_chat([str(d) for d in doc_ids], max_content_length=2000)
                logger.info(f"Retrieved {len(documents)} documents with content from selected IDs")
            else:
                # No explicit selection
                # If summarization with keyword detected, favor broader retrieval on that keyword
                if keyword_query:
                    search_results = await search.hybrid_search(
                        query=keyword_query,
                        limit=25,
                        user=current_user,
                        selected_document_ids=None
                    )
                else:
                    # General question: retrieve a small, relevant set from full accessible scope
                    search_results = await search.hybrid_search(
                        query=chat_request.message or "",
                        limit=5,
                        user=current_user,
                        selected_document_ids=None
                    )
                candidate_doc_ids = [r.document_id for r in search_results]
                if candidate_doc_ids:
                    documents = await search.get_document_content_for_chat(candidate_doc_ids, max_content_length=2000)
                logger.info(
                    (
                        f"Summarize-by-keyword detected, keyword='{keyword_query}', "
                        if keyword_query else ""
                    ) +
                    f"No doc_ids provided; retrieved {len(documents)} context documents from all accessible docs"
                )
            
            # Get conversation history
            history_result = await db.execute(
                select(Message).where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at).limit(10)
            )
            history_messages = history_result.scalars().all()
            conversation_history = [
                {"role": msg.role, "content": msg.content} 
                for msg in history_messages[:-1]  # Exclude current message
            ]
            
            # Get document library statistics for context
            effective_ids = await get_effective_document_ids(db, current_user, None)
            library_stats = {}
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
                
                library_stats = {
                    "total_documents": total_docs,
                    "breakdown": {ft: count for ft, count in breakdown}
                }
            
            # Calculate context budget based on model and user role
            token_budget = context_manager.calculate_user_context_budget(selected_model, user_role)
            
            # Build context items, and attach lightweight citation metadata to pass through to the LLM and UI
            # Each document in `documents` should already contain id/title/content/metadata
            context_items = context_manager.build_context_items(
                user_message=chat_request.message,
                documents=documents,
                conversation_history=conversation_history,
                metadata={
                    "conversation_id": str(conversation.id),
                    "user_role": user_role,
                    "scope": "selected" if doc_ids else "all_accessible",
                    "library_stats": library_stats,  # Include document library statistics
                    "document_sources": [
                        {
                            "id": d.get("id"),
                            "title": d.get("title"),
                            "filename": (d.get("metadata") or {}).get("filename"),
                            "file_type": d.get("file_type"),
                            "created_at": (d.get("metadata") or {}).get("created_at"),
                        }
                        for d in documents
                    ]
                }
            )
            
            # Optimize context to fit budget
            context_text, context_metadata = context_manager.optimize_context(
                context_items=context_items,
                token_budget=token_budget,
                preserve_document_balance=True
            )
            
            logger.info(f"Context optimized: {context_metadata['utilization_percent']}% of budget used")
            
        except Exception as e:
            logger.error(f"Error building intelligent context: {e}")
            context_text = f"Current question: {chat_request.message}"
            context_metadata = {"error": str(e)}
            token_budget = 4096

        # Generate assistant response via LLM (with auto-fallback)
        llm = LLMService()
        try:
            # Multi-provider LLM handles connection automatically (Ollama → OpenAI → graceful)
            assistant_text = await llm.generate_response(
                prompt=chat_request.message,
                context=context_text,
                temperature=0.3  # Low temp for factual responses
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            assistant_text = "I encountered an error while generating a response. Please try again."

        assistant_message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_text,
            message_metadata={
                "context_used": bool(context_text and context_text.strip()),
                "context_metadata": context_metadata if 'context_metadata' in locals() else {},
                "model_used": selected_model,
                "token_budget": token_budget if 'token_budget' in locals() else 0,
                # Provide light-weight source list for UI rendering
                "sources": context_manager.safe_extract_sources(context_metadata) if 'context_metadata' in locals() else [],
                "scope": "selected" if (chat_request.document_ids or meta.get("document_ids")) else "all_accessible"
            }
        )
        db.add(assistant_message)
        await db.flush()  # Flush to get message ID
        # Will be committed by get_db dependency

        # Construct message and response payloads, ensuring document_ids are included
        user_msg_resp = MessageResponse.from_orm(user_message)
        # Always include document_ids metadata from request
        user_msg_resp.metadata["document_ids"] = [str(d) for d in (chat_request.document_ids or [])]
        assistant_msg_resp = MessageResponse.from_orm(assistant_message)
        
        # CRITICAL: Extract source citations from documents used
        from app.schemas.conversation import SourceCitation
        source_citations = []
        
        # Use the actual documents that were retrieved for this chat
        if 'documents' in locals() and documents:
            for doc in documents[:5]:  # Top 5 sources
                # Get content snippet (first 200 chars of actual content)
                content_snippet = None
                if doc.get('content'):
                    content_snippet = doc['content'][:200]
                elif doc.get('full_text'):
                    content_snippet = doc['full_text'][:200]
                
                source_citations.append(SourceCitation(
                    document_id=str(doc.get('id', '')),
                    document_uuid=str(doc.get('uuid', '')),
                    title=doc.get('title', 'Unknown'),
                    filename=doc.get('filename') or (doc.get('metadata') or {}).get('filename'),
                    file_type=doc.get('file_type'),
                    snippet=content_snippet,
                    relevance_score=doc.get('relevance_score') or doc.get('score')
                ))
        
        # Get grounding confidence from verification
        grounding_conf = None
        if assistant_message.message_metadata:
            grounding_conf = assistant_message.message_metadata.get('grounding_confidence')
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=user_msg_resp,
            response=assistant_msg_resp,
            sources=source_citations,
            grounding_confidence=grounding_conf
        )
    except HTTPException:
        raise
    except Exception as e:
        # Return explicit error for rapid diagnosis in UI
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation"""
    service = ConversationService(db)
    
    await service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    return {"message": "Conversation deleted successfully"}


@router.post("/conversations/bulk-delete")
async def bulk_delete_conversations(
    # Accept a raw JSON array from the client (e.g., ["id1","id2"]) rather than {"conversation_ids": [...]}
    conversation_ids: List[UUID] = Body(..., embed=False, description="List of conversation UUIDs to delete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete multiple conversations at once"""
    service = ConversationService(db)
    
    deleted_count = 0
    errors = []
    
    for conversation_id in conversation_ids:
        try:
            await service.delete_conversation(
                conversation_id=conversation_id,
                user_id=current_user.id,
                tenant_id=current_user.tenant_id
            )
            deleted_count += 1
        except Exception as e:
            errors.append({"conversation_id": str(conversation_id), "error": str(e)})
    
    return {
        "message": f"Successfully deleted {deleted_count} conversation(s)",
        "deleted_count": deleted_count,
        "errors": errors
    }


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time chat.

    Note: We reuse the HTTP chat() flow to ensure a single path for
    conversation/message persistence and consistent metadata. This avoids
    divergence between WS and HTTP paths and guarantees that chat history
    is always stored and retrievable.
    """
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
        
        # Get current user from token for authenticated WebSocket sessions
        current_user = await get_current_user(token, db)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps(jsonable_encoder({
            "type": "connected",
            "conversation_id": str(conversation_id)
        })))
        
        # We intentionally do NOT use ConversationService here to avoid
        # sync/async ORM mismatches. We reuse the chat() route logic instead.
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                # Process the message via the same logic as the HTTP endpoint
                chat_request = ChatRequest(
                    message=message_data.get("content"),
                    conversation_id=conversation_id,
                    document_ids=message_data.get("document_ids"),
                    model=message_data.get("model"),
                    stream=False
                )

                # Send typing indicator
                await websocket.send_text(json.dumps(jsonable_encoder({
                    "type": "typing",
                    "conversation_id": str(conversation_id)
                })))

                try:
                    # Reuse HTTP chat flow for persistence + metadata
                    response_payload = await chat(
                        chat_request=chat_request,
                        db=db,
                        current_user=current_user
                    )

                    # Send the response (include metadata for UI scope/sources)
                    await websocket.send_text(json.dumps(jsonable_encoder({
                        "type": "message",
                        "conversation_id": str(conversation_id),
                        "message": {
                            "id": str(response_payload.response.id),
                            "role": "assistant",
                            "content": response_payload.response.content,
                            "created_at": response_payload.response.created_at,
                            "metadata": getattr(response_payload.response, "metadata", None)
                        }
                    })))
                except Exception as e:
                    await websocket.send_text(json.dumps(jsonable_encoder({
                        "type": "error",
                        "message": str(e)
                    })))
            
            elif message_data.get("type") == "ping":
                # Handle ping/pong for connection keep-alive
                await websocket.send_text(json.dumps(jsonable_encoder({
                    "type": "pong"
                })))
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, str(conversation_id))
    except Exception as e:
        await websocket.send_text(json.dumps(jsonable_encoder({
            "type": "error",
            "message": str(e)
        })))
        await manager.disconnect(websocket, str(conversation_id))