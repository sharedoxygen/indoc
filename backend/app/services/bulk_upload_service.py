"""
Bulk upload service for handling folder structures and multiple files
"""
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
import asyncio
import aiofiles
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
import hashlib
import mimetypes

from app.models.document import Document
from app.models.user import User
from app.services.file_service import FileService
from app.services.virus_scan_service import VirusScanService
from app.core.config import settings
from app.core.websocket_manager import WebSocketManager


class BulkUploadService:
    """Service for handling bulk file uploads and folder structures"""
    
    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService(db)
        self.virus_scanner = VirusScanService()
        self.ws_manager = WebSocketManager()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_zip_upload(
        self,
        zip_file: UploadFile,
        user: User,
        tenant_id: UUID,
        preserve_structure: bool = True,
        parent_folder: Optional[str] = None,
        websocket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a ZIP file upload containing multiple files/folders"""
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / zip_file.filename
            
            # Save uploaded ZIP file
            async with aiofiles.open(zip_path, 'wb') as f:
                content = await zip_file.read()
                await f.write(content)
            
            # Scan ZIP file for viruses
            await self._broadcast_progress(websocket_id, "Scanning for viruses...", 5)
            is_safe = await self.virus_scanner.scan_file(str(zip_path))
            if not is_safe:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Virus detected in uploaded file"
                )
            
            # Extract ZIP file
            await self._broadcast_progress(websocket_id, "Extracting files...", 10)
            extracted_path = temp_path / "extracted"
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extracted_path)
            
            # Process extracted files
            results = await self.process_folder(
                folder_path=extracted_path,
                user=user,
                tenant_id=tenant_id,
                preserve_structure=preserve_structure,
                parent_folder=parent_folder,
                websocket_id=websocket_id,
                start_progress=15,
                end_progress=95
            )
            
            await self._broadcast_progress(websocket_id, "Upload complete!", 100)
            
            return results
    
    async def process_folder(
        self,
        folder_path: Path,
        user: User,
        tenant_id: UUID,
        preserve_structure: bool = True,
        parent_folder: Optional[str] = None,
        websocket_id: Optional[str] = None,
        start_progress: int = 0,
        end_progress: int = 100
    ) -> Dict[str, Any]:
        """Process a folder and all its contents recursively"""
        
        results = {
            "total_files": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "skipped_duplicates": 0,
            "files": [],
            "errors": []
        }
        
        # Collect all files to process
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(folder_path)
                all_files.append((file_path, relative_path))
        
        results["total_files"] = len(all_files)
        
        # Process each file
        for idx, (file_path, relative_path) in enumerate(all_files):
            # Calculate progress
            progress = start_progress + ((idx + 1) / len(all_files)) * (end_progress - start_progress)
            
            # Skip system files
            if file_path.name.startswith('.'):
                continue
            
            try:
                # Determine folder structure
                folder_structure = None
                if preserve_structure and parent_folder:
                    folder_parts = list(relative_path.parts[:-1])
                    if folder_parts:
                        folder_structure = f"{parent_folder}/{'/'.join(folder_parts)}"
                    else:
                        folder_structure = parent_folder
                elif preserve_structure:
                    folder_parts = list(relative_path.parts[:-1])
                    if folder_parts:
                        folder_structure = '/'.join(folder_parts)
                
                # Broadcast progress
                await self._broadcast_progress(
                    websocket_id,
                    f"Processing {file_path.name}...",
                    int(progress)
                )
                
                # Process individual file
                document = await self._process_single_file(
                    file_path=file_path,
                    user=user,
                    tenant_id=tenant_id,
                    folder_structure=folder_structure
                )
                
                if document:
                    results["successful_uploads"] += 1
                    results["files"].append({
                        "id": str(document.id),
                        "filename": document.filename,
                        "path": folder_structure,
                        "size": document.file_size,
                        "status": "success"
                    })
                else:
                    results["skipped_duplicates"] += 1
                    results["files"].append({
                        "filename": file_path.name,
                        "path": folder_structure,
                        "status": "duplicate"
                    })
                    
            except Exception as e:
                results["failed_uploads"] += 1
                results["errors"].append({
                    "filename": file_path.name,
                    "error": str(e)
                })
                results["files"].append({
                    "filename": file_path.name,
                    "path": folder_structure,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    async def _process_single_file(
        self,
        file_path: Path,
        user: User,
        tenant_id: UUID,
        folder_structure: Optional[str] = None
    ) -> Optional[Document]:
        """Process a single file and add to database"""
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes")
        
        # Calculate file hash
        file_hash = await self._calculate_file_hash(file_path)
        
        # Check for duplicates
        existing_doc = self.db.query(Document).filter(
            Document.file_hash == file_hash,
            Document.tenant_id == tenant_id
        ).first()
        
        if existing_doc:
            return None  # Skip duplicate
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # Copy file to storage location
        storage_path = self.upload_dir / f"{tenant_id}" / f"{file_hash}_{file_path.name}"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, storage_path)
        
        # Create document record
        document = Document(
            id=uuid4(),
            tenant_id=tenant_id,
            filename=file_path.name,
            file_path=str(storage_path),
            file_size=file_size,
            file_hash=file_hash,
            mime_type=mime_type,
            uploaded_by=user.id,
            folder_structure=folder_structure,
            metadata={
                "original_path": str(file_path),
                "upload_method": "bulk"
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        
        # Queue for text extraction and indexing (async)
        asyncio.create_task(self._queue_for_processing(document))
        
        return document
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _queue_for_processing(self, document: Document):
        """Queue document for text extraction and indexing"""
        # This would integrate with Celery or similar task queue
        # For now, we'll just mark it as pending
        document.processing_status = "pending"
        self.db.commit()
    
    async def _broadcast_progress(
        self,
        websocket_id: Optional[str],
        message: str,
        progress: int
    ):
        """Broadcast upload progress via WebSocket"""
        if websocket_id:
            await self.ws_manager.broadcast_json_to_conversation(
                {
                    "type": "upload_progress",
                    "message": message,
                    "progress": progress
                },
                websocket_id
            )
    
    async def process_multiple_files(
        self,
        files: List[UploadFile],
        user: User,
        tenant_id: UUID,
        folder: Optional[str] = None,
        websocket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process multiple file uploads"""
        
        results = {
            "total_files": len(files),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "skipped_duplicates": 0,
            "files": [],
            "errors": []
        }
        
        for idx, file in enumerate(files):
            progress = ((idx + 1) / len(files)) * 100
            
            try:
                await self._broadcast_progress(
                    websocket_id,
                    f"Processing {file.filename}...",
                    int(progress)
                )
                
                # Save temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
                    content = await file.read()
                    tmp_file.write(content)
                    tmp_path = Path(tmp_file.name)
                
                # Process the file
                document = await self._process_single_file(
                    file_path=tmp_path,
                    user=user,
                    tenant_id=tenant_id,
                    folder_structure=folder
                )
                
                # Clean up temp file
                tmp_path.unlink()
                
                if document:
                    results["successful_uploads"] += 1
                    results["files"].append({
                        "id": str(document.id),
                        "filename": document.filename,
                        "size": document.file_size,
                        "status": "success"
                    })
                else:
                    results["skipped_duplicates"] += 1
                    results["files"].append({
                        "filename": file.filename,
                        "status": "duplicate"
                    })
                    
            except Exception as e:
                results["failed_uploads"] += 1
                results["errors"].append({
                    "filename": file.filename,
                    "error": str(e)
                })
                results["files"].append({
                    "filename": file.filename,
                    "status": "failed",
                    "error": str(e)
                })
        
        await self._broadcast_progress(websocket_id, "Upload complete!", 100)
        
        return results