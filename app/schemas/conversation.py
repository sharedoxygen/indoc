"""
Pydantic schemas for conversation functionality
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, StringConstraints
from typing import Annotated
from uuid import UUID

RoleStr = Annotated[str, StringConstraints(pattern="^(user|assistant)$")]


class MessageBase(BaseModel):
    """Base message schema"""
    content: str
    role: RoleStr
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    pass


class MessageResponse(BaseModel):
    """Schema for message response"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID
    conversation_id: UUID
    role: RoleStr
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="message_metadata")
    created_at: datetime

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle message_metadata field"""
        return cls(
            id=obj.id,
            conversation_id=obj.conversation_id,
            role=obj.role,
            content=obj.content,
            metadata=obj.message_metadata if hasattr(obj, 'message_metadata') else {},
            created_at=obj.created_at
        )


class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: Optional[str] = None
    document_id: Optional[int] = None  # DB uses integer FK
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="conversation_metadata")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    pass


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    """Schema for listing conversations"""
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int


class ChatRequest(BaseModel):
    """Schema for chat request"""
    message: str
    conversation_id: Optional[UUID] = None
    document_ids: Optional[List[UUID]] = None
    stream: bool = False
    # Enhanced context for better conversational experience
    context_data: Optional[Dict[str, Any]] = None
    # Optional high-level intent detected by the client (e.g., analytics_summary)
    intent: Optional[str] = None
    # Optional formatting preferences from the client
    # Example: { "prefer": "table", "strict": True, "table": { "columns_hint": ["Document Type","Count","Percentage","Description"] } }
    formatting: Optional[Dict[str, Any]] = None


class SourceCitation(BaseModel):
    """Source document citation"""
    document_id: str
    document_uuid: Optional[str] = None
    title: str
    filename: Optional[str] = None
    file_type: Optional[str] = None
    snippet: Optional[str] = None  # Relevant excerpt from document
    relevance_score: Optional[float] = None
    page_number: Optional[int] = None


class ChatResponse(BaseModel):
    """Schema for chat response with source citations"""
    conversation_id: UUID
    message: MessageResponse
    response: MessageResponse
    sources: List[SourceCitation] = Field(default_factory=list, description="Source documents cited in response")
    grounding_confidence: Optional[float] = Field(default=None, description="Answer grounding confidence score (0-1)")