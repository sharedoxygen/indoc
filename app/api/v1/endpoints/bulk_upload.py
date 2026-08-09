"""
Bulk upload API endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.bulk_upload_service import BulkUploadService
from app.core.websocket_manager import WebSocketManager

router = APIRouter()
manager = WebSocketManager()


@router.get("/test")
async def test_bulk_upload():
    """Simple test endpoint to verify bulk upload router is working"""
    return {"status": "ok", "message": "Bulk upload router is accessible"}


@router.post("/upload/bulk")
async def bulk_upload_files(
    files: List[UploadFile] = File(...),
    folder: Optional[str] = Form(None),
    folder_mapping: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    document_set_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload multiple files at once with optional folder structure preservation"""
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Bulk upload called with {len(files) if files else 0} files")
        logger.info(f"User: {current_user.username if current_user else 'None'} (ID: {current_user.id if current_user else 'None'})")
        logger.info(f"Tenant ID: {current_user.tenant_id if current_user else 'None'}")
        logger.info(f"Folder mapping: {folder_mapping[:100] if folder_mapping else 'None'}")
        
        # Validate files
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided for upload"
            )
        
        # Validate file count (reasonable limit)
        if len(files) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many files. Maximum 100 files per upload."
            )
        
        service = BulkUploadService(db)
        
        # Parse folder mapping if provided
        folder_map = None
        if folder_mapping:
            try:
                folder_map = json.loads(folder_mapping)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid folder_mapping JSON: {str(e)}"
                )
        
        # Build metadata
        metadata = {}
        if title:
            metadata['title'] = title
        if description:
            metadata['description'] = description
        if tags:
            metadata['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
        
        results = await service.process_multiple_files(
            files=files,
            user=current_user,
            tenant_id=current_user.tenant_id,
            folder=folder,
            folder_mapping=folder_map,
            metadata=metadata,
            document_set_id=document_set_id
        )
        
        return results
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors and return a proper error response
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_msg = str(e) if str(e) else repr(e)
        error_trace = traceback.format_exc()
        logger.error(f"❌ BULK UPLOAD ERROR: {error_msg}")
        logger.error(f"Full traceback:\n{error_trace}")
        
        # Return detailed error for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {error_msg}\n\nTraceback: {error_trace[:500]}"
        )


@router.post("/upload/zip")
async def upload_zip_file(
    file: UploadFile = File(...),
    preserve_structure: bool = Form(True),
    parent_folder: Optional[str] = Form(None),
    document_set_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
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
        parent_folder=parent_folder,
        document_set_id=document_set_id
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