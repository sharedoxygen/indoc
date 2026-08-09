"""
Conversation service for document chat functionality
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import json
import asyncio
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.schemas.conversation import (
    ConversationCreate, ConversationResponse, 
    MessageCreate, MessageResponse,
    ChatRequest, ChatResponse
)
from app.core.config import settings
from app.mcp.client import MCPClient
from app.services.search_service import SearchService


class ConversationService:
    """Service for managing document conversations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.mcp_client = MCPClient()
        self.search_service = SearchService(db)
    
    async def create_conversation(
        self, 
        user_id: UUID,
        tenant_id: UUID,
        document_id: Optional[UUID] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation"""
        
        document_db_id = None
        # If document_id provided, verify it exists and user has access
        if document_id:
            document = self.db.query(Document).filter(
                Document.uuid == document_id,
                Document.tenant_id == tenant_id
            ).first()
            
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found or access denied"
                )
            
            document_db_id = document.id
            if not title:
                title = f"Chat with {document.filename}"
        
        conversation = Conversation(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            document_id=document_db_id,
            title=title or "New Conversation",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    async def get_conversation(
        self, 
        conversation_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> Conversation:
        """Get a conversation by ID"""
        
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.tenant_id == tenant_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return conversation
    
    async def list_conversations(
        self,
        user_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List user's conversations"""
        
        query = self.db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.tenant_id == tenant_id
        ).order_by(desc(Conversation.updated_at))
        
        total = query.count()
        conversations = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "conversations": conversations,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to a conversation"""
        
        message = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        self.db.add(message)
        
        # Update conversation's updated_at
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    async def get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 50
    ) -> List[Message]:
        """Get conversation message history"""
        
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).limit(limit).all()
        
        return messages
    
    async def process_chat_message(
        self,
        user_id: UUID,
        tenant_id: UUID,
        chat_request: ChatRequest
    ) -> ChatResponse:
        """Process a chat message and generate response"""
        
        # Get or create conversation
        if chat_request.conversation_id:
            conversation = await self.get_conversation(
                chat_request.conversation_id,
                user_id,
                tenant_id
            )
        else:
            conversation = await self.create_conversation(
                user_id,
                tenant_id,
                document_id=chat_request.document_ids[0] if chat_request.document_ids else None
            )
            # Store all document IDs in the conversation's metadata
            if chat_request.document_ids:
                conversation.metadata = {"document_ids": [str(doc_id) for doc_id in chat_request.document_ids]}
                self.db.commit()

        # Add user message
        user_message = await self.add_message(
            conversation.id,
            "user",
            chat_request.message
        )
        
        # Get conversation context
        context = await self._build_conversation_context(
            conversation,
            chat_request.message
        )
        
        # Generate response using MCP/LLM
        response_content = await self._generate_response(
            chat_request.message,
            context,
            chat_request.stream
        )
        
        # Add assistant message
        assistant_message = await self.add_message(
            conversation.id,
            "assistant",
            response_content,
            metadata={"context_used": bool(context)}
        )
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=MessageResponse.from_orm(user_message),
            response=MessageResponse.from_orm(assistant_message)
        )
    
    async def _build_conversation_context(
        self,
        conversation: Conversation,
        query: str
    ) -> str:
        """Build context for the conversation"""

        context_parts = []
        document_ids_to_search = []

        # Get document IDs from metadata if available
        if 'document_ids' in conversation.metadata:
            document_ids_to_search = [UUID(doc_id) for doc_id in conversation.metadata.get('document_ids', [])]
        elif conversation.document_id:
            document_ids_to_search.append(conversation.document_id)

        # Add document context if available
        if document_ids_to_search:
            search_results = await self.search_service.hybrid_search(
                query=query,
                document_ids=[str(doc_id) for doc_id in document_ids_to_search],
                limit=5  # Increase limit for multi-document search
            )

            if search_results:
                context_parts.append("Relevant document sections:")
                for result in search_results:
                    context_parts.append(f"- {result.get('content', '')[:500]}")

        # Add recent conversation history
        recent_messages = await self.get_conversation_history(
            conversation.id,
            limit=10
        )
        
        if recent_messages:
            context_parts.append("\nRecent conversation:")
            for msg in recent_messages[-5:]:  # Last 5 messages
                context_parts.append(f"{msg.role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    async def _generate_response(
        self,
        query: str,
        context: str,
        stream: bool = False
    ) -> str:
        """Generate response using LLM service"""
        try:
            from app.services.llm_service import LLMService
            llm_service = LLMService()
            
            # Check if Ollama is available
            if not await llm_service.check_ollama_connection():
                return "I'm unable to connect to the language model right now. Please ensure Ollama is running and try again."
            
            # Handle different types of queries
            if any(word in query.lower() for word in ['summary', 'summarize', 'sum up']):
                # Extract document content from context for summarization
                if context and 'Document Context:' in context:
                    doc_content = context.split('Document Context:')[1].split('Recent conversation:')[0].strip()
                    return await llm_service.summarize_document(doc_content)
            
            elif any(word in query.lower() for word in ['sentiment', 'tone', 'feeling', 'emotion']):
                # Sentiment analysis
                if context and 'Document Context:' in context:
                    doc_content = context.split('Document Context:')[1].split('Recent conversation:')[0].strip()
                    sentiment_result = await llm_service.analyze_sentiment(doc_content)
                    return sentiment_result.get('analysis', 'Unable to analyze sentiment.')
            
            elif any(word in query.lower() for word in ['key points', 'main points', 'important', 'highlights']):
                # Key points extraction
                if context and 'Document Context:' in context:
                    doc_content = context.split('Document Context:')[1].split('Recent conversation:')[0].strip()
                    key_points = await llm_service.extract_key_points(doc_content)
                    if key_points:
                        return "Here are the key points from the document:\n\n" + "\n".join([f"• {point}" for point in key_points])
                    else:
                        return "I couldn't extract specific key points from the document."
            
            elif any(word in query.lower() for word in ['entities', 'people', 'names', 'organizations', 'companies']):
                # Entity extraction
                if context and 'Document Context:' in context:
                    doc_content = context.split('Document Context:')[1].split('Recent conversation:')[0].strip()
                    entities = await llm_service.extract_entities(doc_content)
                    
                    response_parts = ["Here are the entities I found in the document:"]
                    for entity_type, items in entities.items():
                        if items:
                            response_parts.append(f"\n**{entity_type.title()}:** {', '.join(items)}")
                    
                    return "\n".join(response_parts) if len(response_parts) > 1 else "I couldn't find specific entities in the document."
            
            # Default: general question answering
            conversation_history = []
            if context and 'Recent conversation:' in context:
                history_text = context.split('Recent conversation:')[1]
                # Parse conversation history (simplified)
                for line in history_text.split('\n'):
                    if ':' in line and line.strip():
                        role, content = line.split(':', 1)
                        conversation_history.append({
                            "role": role.strip().lower(),
                            "content": content.strip()
                        })
            
            # Extract documents from context
            documents = []
            if context and 'Relevant document sections:' in context:
                doc_sections = context.split('Relevant document sections:')[1].split('Recent conversation:')[0]
                for line in doc_sections.split('\n'):
                    if line.startswith('- '):
                        documents.append({
                            "content": line[2:],  # Remove "- " prefix
                            "title": "Document Section"
                        })
            
            return await llm_service.answer_question(query, documents, conversation_history)
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error while processing your request. Please try again."
    
    async def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """Delete a conversation and all its messages"""
        
        conversation = await self.get_conversation(
            conversation_id,
            user_id,
            tenant_id
        )
        
        self.db.delete(conversation)
        self.db.commit()
        
        return True