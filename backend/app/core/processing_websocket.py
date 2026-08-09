"""
WebSocket manager for real-time document processing updates
"""
import json
import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class ProcessingWebSocketManager:
    """Manages WebSocket connections for processing updates"""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store processing status for each document
        self.processing_status: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket for a user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections[user_id])}")
        
        # Send current processing status to newly connected client
        await self.send_current_status(websocket, user_id)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket for a user"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_current_status(self, websocket: WebSocket, user_id: str):
        """Send current processing status to a specific WebSocket"""
        try:
            # Get documents being processed by this user
            user_documents = {
                doc_id: status for doc_id, status in self.processing_status.items()
                if status.get('user_id') == user_id
            }
            
            if user_documents:
                await websocket.send_text(json.dumps({
                    "type": "status_sync",
                    "documents": user_documents,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        except Exception as e:
            logger.error(f"Failed to send current status: {e}")
    
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections for a specific user"""
        if user_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected_websockets = []
        
        for websocket in self.active_connections[user_id].copy():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected_websockets.append(websocket)
        
        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket, user_id)
    
    async def update_processing_step(
        self,
        document_id: str,
        user_id: str,
        step: str,
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        details: Optional[list] = None,
        error_message: Optional[str] = None
    ):
        """Update processing step and broadcast to user"""
        
        # Update internal status
        if document_id not in self.processing_status:
            self.processing_status[document_id] = {
                "user_id": user_id,
                "document_id": document_id,
                "steps": {},
                "created_at": datetime.utcnow().isoformat()
            }
        
        self.processing_status[document_id]["steps"][step] = {
            "status": status,
            "progress": progress,
            "message": message,
            "details": details or [],
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        }
        
        # Broadcast update to user
        update_message = {
            "type": "processing_update",
            "documentId": document_id,
            "step": step,
            "status": status,
            "progress": progress,
            "message": message,
            "details": details,
            "errorMessage": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_user(user_id, update_message)
        logger.info(f"Processing update sent: {document_id} - {step} - {status}")
    
    async def start_document_processing(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int
    ):
        """Initialize document processing status"""
        
        self.processing_status[document_id] = {
            "user_id": user_id,
            "document_id": document_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "steps": {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Send initialization message
        init_message = {
            "type": "processing_started",
            "documentId": document_id,
            "filename": filename,
            "fileType": file_type,
            "fileSize": file_size,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_user(user_id, init_message)
        logger.info(f"Document processing started: {document_id} - {filename}")
    
    async def complete_document_processing(
        self,
        document_id: str,
        user_id: str,
        success: bool,
        final_message: Optional[str] = None
    ):
        """Mark document processing as complete"""
        
        if document_id in self.processing_status:
            self.processing_status[document_id]["completed_at"] = datetime.utcnow().isoformat()
            self.processing_status[document_id]["success"] = success
        
        # Send completion message
        completion_message = {
            "type": "processing_completed",
            "documentId": document_id,
            "success": success,
            "message": final_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_user(user_id, completion_message)
        logger.info(f"Document processing completed: {document_id} - Success: {success}")
        
        # Clean up status after a delay (optional)
        asyncio.create_task(self._cleanup_completed_document(document_id, delay=300))  # 5 minutes
    
    async def _cleanup_completed_document(self, document_id: str, delay: int):
        """Clean up completed document status after delay"""
        await asyncio.sleep(delay)
        if document_id in self.processing_status:
            del self.processing_status[document_id]
            logger.info(f"Cleaned up processing status for document: {document_id}")
    
    def get_processing_stats(self, user_id: str) -> Dict[str, int]:
        """Get processing statistics for a user"""
        user_docs = [
            doc for doc in self.processing_status.values()
            if doc.get('user_id') == user_id
        ]
        
        stats = {
            "total": len(user_docs),
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        for doc in user_docs:
            if doc.get("success") is True:
                stats["completed"] += 1
            elif doc.get("success") is False:
                stats["failed"] += 1
            else:
                stats["processing"] += 1
        
        return stats


# Global instance
processing_ws_manager = ProcessingWebSocketManager()
