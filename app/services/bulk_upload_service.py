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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import mimetypes

from app.models.document import Document
from app.models.user import User
from app.services.virus_scanner import VirusScanner
from app.core.config import settings
from app.core.websocket_manager import WebSocketManager


class BulkUploadService:
    """Service for handling bulk file uploads and folder structures"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.virus_scanner = VirusScanner()
        self.ws_manager = WebSocketManager()
        self.upload_dir = settings.STORAGE_PATH
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_zip_upload(
        self,
        zip_file: UploadFile,
        user: User,
        tenant_id: UUID,
        preserve_structure: bool = True,
        parent_folder: Optional[str] = None,
        websocket_id: Optional[str] = None,
        document_set_id: Optional[str] = None
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
            scan_result = await self.virus_scanner.scan_file(zip_path)
            if not scan_result.get("clean", False):
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
                end_progress=95,
                document_set_id=document_set_id
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
        end_progress: int = 100,
        document_set_id: Optional[str] = None
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
                
                # Process individual file with metadata
                document = await self._process_single_file(
                    file_path=file_path,
                    user=user,
                    tenant_id=tenant_id,
                    folder_structure=folder_structure,
                    metadata=None,  # ZIP uploads don't have user metadata
                    document_set_id=document_set_id
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
        folder_structure: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document_set_id: Optional[str] = None
    ) -> Optional[Document]:
        """Process a single file and add to database with full audit metadata"""
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes")
        
        # Calculate file hash
        file_hash = await self._calculate_file_hash(file_path)
        
        # Check for duplicates
        result = await self.db.execute(
            select(Document).where(
                Document.file_hash == file_hash,
                Document.tenant_id == tenant_id
            )
        )
        existing_doc = result.scalar_one_or_none()
        
        if existing_doc:
            return None  # Skip duplicate
        
        # Extract original filename from metadata FIRST (needed for storage path)
        original_filename = metadata.get('original_filename') if metadata else None
        if original_filename:
            # Get just the filename without folder path for storage
            base_filename = Path(original_filename).name
            title = Path(original_filename).stem  # Use original filename without extension
            final_storage_name = f"{file_hash}_{base_filename}"
        else:
            title = file_path.stem  # Fallback to temp name if no original provided
            final_storage_name = f"{file_hash}_{file_path.name}"
        
        # Determine MIME type and file extension
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        file_extension = file_path.suffix.lower().strip('.')
        
        # Copy file to storage location with original filename
        storage_path = self.upload_dir / f"{tenant_id}" / final_storage_name
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, storage_path)
        
        # Build comprehensive audit metadata
        audit_metadata = {
            "original_path": str(file_path),
            "upload_method": "bulk",
            "upload_timestamp": datetime.utcnow().isoformat(),
            "uploaded_by_id": user.id,
            "uploaded_by_email": user.email,
            "tenant_id": str(tenant_id),
            "file_hash": file_hash,
            "mime_type": mime_type,
            "folder_structure": folder_structure
        }
        
        # Merge user-provided metadata
        if metadata:
            audit_metadata.update({
                "user_metadata": metadata
            })
        
        description = metadata.get('description') if metadata else None
        tags = metadata.get('tags', []) if metadata else []
        
        # If user provided a title, add it to description or custom metadata
        if metadata and metadata.get('title'):
            user_title = metadata.get('title')
            # Prepend user title to description if exists, otherwise use as description
            if description:
                description = f"{user_title}: {description}"
            else:
                description = user_title
        
        # Create document record with full audit trail using base filename (no folder path)
        final_filename = Path(original_filename).name if original_filename else file_path.name
        document = Document(
            # Let SQLAlchemy auto-generate id and uuid
            tenant_id=tenant_id,
            filename=final_filename,
            storage_path=str(storage_path),
            file_size=file_size,
            file_hash=file_hash,
            file_type=file_extension,
            uploaded_by=user.id,
            folder_path=folder_structure,
            title=title,
            description=description,
            tags=tags,
            custom_metadata=audit_metadata,
            document_set_id=document_set_id,  # Link to document set
            status="pending"
            # Let SQLAlchemy auto-generate timestamps
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
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
        try:
            from app.tasks.document import process_document
            process_document.delay(str(document.uuid))
        except Exception as e:
            # If queuing fails, just log it
            import logging
            logging.error(f"Failed to queue document for processing: {e}")
    
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
        folder_mapping: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        websocket_id: Optional[str] = None,
        document_set_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process multiple file uploads with folder structure preservation"""
        
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
                
                # Determine folder structure for this file
                folder_structure = folder
                if folder_mapping and file.filename in folder_mapping:
                    # Use the mapped folder path from the frontend
                    relative_path = folder_mapping[file.filename]
                    # Extract directory path (remove filename)
                    folder_structure = str(Path(relative_path).parent) if relative_path else None
                    if folder_structure == '.':
                        folder_structure = None
                
                # Save temporary file with proper extension only (not full path)
                file_ext = Path(file.filename).suffix or '.bin'
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    content = await file.read()
                    tmp_file.write(content)
                    tmp_path = Path(tmp_file.name)
                
                # Process the file with metadata (pass original filename)
                metadata_with_filename = (metadata or {}).copy()
                metadata_with_filename['original_filename'] = file.filename
                
                document = await self._process_single_file(
                    file_path=tmp_path,
                    user=user,
                    tenant_id=tenant_id,
                    folder_structure=folder_structure,
                    metadata=metadata_with_filename,
                    document_set_id=document_set_id
                )
                
                # Clean up temp file
                tmp_path.unlink()
                
                if document:
                    results["successful_uploads"] += 1
                    results["files"].append({
                        "id": str(document.id),
                        "document_uuid": str(document.uuid),
                        "filename": file.filename,  # Original filename for frontend matching
                        "stored_filename": document.filename,  # Stored filename with hash
                        "folder_path": folder_structure,
                        "size": document.file_size,
                        "status": "success"
                    })
                else:
                    results["skipped_duplicates"] += 1
                    results["files"].append({
                        "filename": file.filename,
                        "folder_path": folder_structure,
                        "status": "duplicate"
                    })
                    
            except Exception as e:
                # Rollback transaction for this file to allow others to continue
                await self.db.rollback()
                
                results["failed_uploads"] += 1
                error_msg = str(e)
                results["errors"].append({
                    "filename": file.filename,
                    "error": error_msg
                })
                results["files"].append({
                    "filename": file.filename,
                    "status": "failed",
                    "error": error_msg
                })
        
        await self._broadcast_progress(websocket_id, "Upload complete!", 100)
        
        return results