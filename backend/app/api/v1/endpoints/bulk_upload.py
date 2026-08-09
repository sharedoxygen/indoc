"""
Bulk upload API endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.bulk_upload_service import BulkUploadService
from app.core.websocket_manager import WebSocketManager

router = APIRouter()
manager = WebSocketManager()


@router.post("/upload/bulk")
async def bulk_upload_files(
    files: List[UploadFile] = File(...),
    folder: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple files at once"""
    
    service = BulkUploadService(db)
    
    results = await service.process_multiple_files(
        files=files,
        user=current_user,
        tenant_id=current_user.tenant_id,
        folder=folder
    )
    
    return results


@router.post("/upload/zip")
async def upload_zip_file(
    file: UploadFile = File(...),
    preserve_structure: bool = Form(True),
    parent_folder: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a ZIP file containing multiple files/folders"""
    
    # Validate file is a ZIP
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive"
        )
    
    service = BulkUploadService(db)
    
    results = await service.process_zip_upload(
        zip_file=file,
        user=current_user,
        tenant_id=current_user.tenant_id,
        preserve_structure=preserve_structure,
        parent_folder=parent_folder
    )
    
    return results


@router.websocket("/ws/upload")
async def websocket_upload(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time upload progress"""
    
    # Generate unique WebSocket ID
    ws_id = str(UUID())
    await manager.connect(websocket, ws_id)
    
    try:
        # Authenticate user
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        token = auth_data.get("token")
        
        if not token:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Authentication required"
            }))
            await manager.disconnect(websocket, ws_id)
            return
        
        # Get user from token (implement proper JWT validation)
        # current_user = await get_user_from_token(token, db)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "ws_id": ws_id
        }))
        
        service = BulkUploadService(db)
        
        while True:
            # Receive upload request
            data = await websocket.receive_text()
            upload_data = json.loads(data)
            
            if upload_data.get("type") == "upload_zip":
                # Handle ZIP upload with progress
                try:
                    # The actual file would be sent via regular HTTP POST
                    # This WebSocket is just for progress updates
                    # Client should include ws_id in the HTTP request
                    
                    await websocket.send_text(json.dumps({
                        "type": "upload_started",
                        "message": "Processing upload..."
                    }))
                    
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
            
            elif upload_data.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong"
                }))
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, ws_id)
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
        await manager.disconnect(websocket, ws_id)