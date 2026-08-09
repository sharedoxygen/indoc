"""
WebSocket connection manager for real-time features
"""
from typing import Dict, List
from fastapi import WebSocket
import json


class WebSocketManager:
    """Manager for WebSocket connections"""
    
    def __init__(self):
        # Store active connections by conversation_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, conversation_id: str):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        
        self.active_connections[conversation_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, conversation_id: str):
        """Remove a WebSocket connection"""
        if conversation_id in self.active_connections:
            if websocket in self.active_connections[conversation_id]:
                self.active_connections[conversation_id].remove(websocket)
            
            # Clean up empty conversation rooms
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        await websocket.send_text(message)
    
    async def broadcast_to_conversation(self, message: str, conversation_id: str):
        """Broadcast a message to all connections in a conversation"""
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                await connection.send_text(message)
    
    async def broadcast_json_to_conversation(self, data: dict, conversation_id: str):
        """Broadcast JSON data to all connections in a conversation"""
        message = json.dumps(data)
        await self.broadcast_to_conversation(message, conversation_id)
    
    def get_connection_count(self, conversation_id: str) -> int:
        """Get the number of active connections for a conversation"""
        if conversation_id in self.active_connections:
            return len(self.active_connections[conversation_id])
        return 0
    
    def get_all_conversation_ids(self) -> List[str]:
        """Get all conversation IDs with active connections"""
        return list(self.active_connections.keys())