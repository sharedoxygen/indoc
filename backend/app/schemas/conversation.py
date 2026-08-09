"""
Pydantic schemas for conversation functionality
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Literal
from uuid import UUID

RoleStr = Literal["user", "assistant"]


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
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    role: RoleStr
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="message_metadata")
    created_at: datetime


class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: Optional[str] = None
    document_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    user_id: UUID
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
    model: Optional[str] = None
    stream: bool = False
    # Enhanced context for better conversational experience
    context_data: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Schema for chat response"""
    conversation_id: UUID
    message: MessageResponse
    response: MessageResponse