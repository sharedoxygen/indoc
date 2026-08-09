"""
Chat Streaming Endpoint - Server-Sent Events (SSE)

Per Review C3.5: Implement streaming for better UX (no 30s blank screen)
Per Review C5.4: Progressive text display
"""
import asyncio
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.conversation import ChatRequest
from app.services.async_conversation_service import AsyncConversationService

router = APIRouter()
logger = logging.getLogger(__name__)


async def generate_sse_stream(
    message: str,
    conversation_service: AsyncConversationService,
    user_id: int,
    tenant_id: str,
    chat_request: ChatRequest
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events stream for chat response
    
    Yields SSE formatted messages:
    - data: {"type": "status", "message": "Searching documents..."}
    - data: {"type": "chunk", "text": "partial response"}
    - data: {"type": "done", "conversation_id": "uuid"}
    """
    try:
        # Step 1: Status update - Starting
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing your question...'})}\n\n"
        await asyncio.sleep(0.1)
        
        # Step 2: Status update - Searching
        yield f"data: {json.dumps({'type': 'status', 'message': 'Searching your documents...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 3: Status update - Analyzing
        yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing context...'})}\n\n"
        await asyncio.sleep(0.5)
        
        # Step 4: Status update - Generating
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating response...'})}\n\n"
        
        # Step 5: Process chat message (this is where actual work happens)
        # For now, get the complete response
        # TODO: Integrate streaming at LLM level for true token-by-token streaming
        response_obj = await conversation_service.process_chat_message(
            user_id=user_id,
            tenant_id=tenant_id,
            chat_request=chat_request
        )
        
        # Step 6: Stream response in chunks (simulate streaming)
        response_text = response_obj.response.content
        chunk_size = 50  # characters per chunk
        
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i+chunk_size]
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
            await asyncio.sleep(0.05)  # Small delay for smooth typing effect
        
        # Step 7: Send completion
        completion_data = {
            'type': 'done',
            'conversation_id': str(response_obj.conversation_id),
            'message_id': str(response_obj.response.id),
            'sources': response_obj.sources if hasattr(response_obj, 'sources') else []
        }
        yield f"data: {json.dumps(completion_data)}\n\n"
        
    except HTTPException as e:
        # Send error via SSE
        yield f"data: {json.dumps({'type': 'error', 'message': e.detail})}\n\n"
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred while generating the response'})}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream chat response with Server-Sent Events
    
    Returns SSE stream with:
    - Status updates (searching, analyzing, generating)
    - Response chunks (progressive text)
    - Completion notification with metadata
    
    Client usage:
        const eventSource = new EventSource('/api/v1/chat/stream');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'chunk') {
                appendText(data.text);
            }
        };
    """
    logger.info(f"📡 Streaming chat request from {current_user.email}")
    
    service = AsyncConversationService(db)
    
    return StreamingResponse(
        generate_sse_stream(
            message=chat_request.message,
            conversation_service=service,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            chat_request=chat_request
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

