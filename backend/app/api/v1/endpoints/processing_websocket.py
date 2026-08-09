"""
WebSocket endpoints for real-time processing updates
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any
from app.core.processing_websocket import processing_ws_manager
from app.core.security import get_current_user_websocket
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/processing")
async def processing_websocket_endpoint(
    websocket: WebSocket,
    token: str = None
):
    """
    WebSocket endpoint for real-time document processing updates
    
    Expected URL: ws://localhost:8000/ws/processing?token=<jwt_token>
    """
    
    # Authenticate user from token
    try:
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return
        
        user = await get_current_user_websocket(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
            
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    user_id = str(user.id)
    
    try:
        # Connect to processing manager
        await processing_ws_manager.connect(websocket, user_id)
        
        # Listen for messages from client
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types from client
                await handle_client_message(message, user_id, user)
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from user {user_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
        processing_ws_manager.disconnect(websocket, user_id)
        
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        processing_ws_manager.disconnect(websocket, user_id)


async def handle_client_message(message: Dict[str, Any], user_id: str, user: User):
    """Handle messages from WebSocket client"""
    
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await processing_ws_manager.broadcast_to_user(user_id, {
            "type": "pong",
            "timestamp": message.get("timestamp")
        })
        
    elif message_type == "get_stats":
        # Send processing statistics
        stats = processing_ws_manager.get_processing_stats(user_id)
        await processing_ws_manager.broadcast_to_user(user_id, {
            "type": "stats_update",
            "stats": stats
        })
        
    elif message_type == "retry_processing":
        # Handle retry request
        document_id = message.get("documentId")
        if document_id:
            await handle_retry_processing(document_id, user_id, user)
        
    elif message_type == "cancel_processing":
        # Handle cancel request
        document_id = message.get("documentId")
        if document_id:
            await handle_cancel_processing(document_id, user_id, user)
            
    else:
        logger.warning(f"Unknown message type from user {user_id}: {message_type}")


async def handle_retry_processing(document_id: str, user_id: str, user: User):
    """Handle document processing retry request"""
    try:
        # Import here to avoid circular imports
        from app.tasks.document import process_document
        from app.db.session import AsyncSessionLocal
        from app.models.document import Document
        from sqlalchemy import select
        
        # Get document from database
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                await processing_ws_manager.broadcast_to_user(user_id, {
                    "type": "error",
                    "message": f"Document {document_id} not found"
                })
                return
            
            # Check if user owns the document or has permission
            if document.uploaded_by != user.id and user.role not in ['Admin', 'Reviewer']:
                await processing_ws_manager.broadcast_to_user(user_id, {
                    "type": "error",
                    "message": "Permission denied"
                })
                return
            
            # Reset document status
            document.status = "processing"
            document.error_message = None
            await db.commit()
            
            # Start processing pipeline
            await processing_ws_manager.start_document_processing(
                document_id=str(document.uuid),
                user_id=user_id,
                filename=document.filename,
                file_type=document.file_type,
                file_size=document.file_size
            )
            
            # Queue processing task
            process_document.delay(str(document.uuid))
            
            logger.info(f"Document processing retried: {document_id} by user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to retry processing for {document_id}: {e}")
        await processing_ws_manager.broadcast_to_user(user_id, {
            "type": "error",
            "message": f"Failed to retry processing: {str(e)}"
        })


async def handle_cancel_processing(document_id: str, user_id: str, user: User):
    """Handle document processing cancellation request"""
    try:
        # Import here to avoid circular imports
        from app.db.session import AsyncSessionLocal
        from app.models.document import Document
        from sqlalchemy import select
        
        # Get document from database
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.uuid == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                await processing_ws_manager.broadcast_to_user(user_id, {
                    "type": "error",
                    "message": f"Document {document_id} not found"
                })
                return
            
            # Check if user owns the document or has permission
            if document.uploaded_by != user.id and user.role not in ['Admin', 'Reviewer']:
                await processing_ws_manager.broadcast_to_user(user_id, {
                    "type": "error",
                    "message": "Permission denied"
                })
                return
            
            # Cancel processing (mark as failed)
            document.status = "failed"
            document.error_message = "Processing cancelled by user"
            await db.commit()
            
            # Send cancellation update
            await processing_ws_manager.complete_document_processing(
                document_id=document_id,
                user_id=user_id,
                success=False,
                final_message="Processing cancelled"
            )
            
            logger.info(f"Document processing cancelled: {document_id} by user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to cancel processing for {document_id}: {e}")
        await processing_ws_manager.broadcast_to_user(user_id, {
            "type": "error",
            "message": f"Failed to cancel processing: {str(e)}"
        })
