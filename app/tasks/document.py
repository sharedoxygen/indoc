"""
Document processing tasks for Celery
"""
from typing import Dict, Any
from uuid import UUID
from celery import Task
from sqlalchemy.orm import Session
import logging
import time

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.text_extraction_service import TextExtractionService
from app.services.search_service import SearchService
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# WebSocket progress updates (per-user) using processing_ws_manager
async def send_progress_update(document_id: str, step: str, status: str, progress: int, message: str = "", details: list = None):
    """Send real-time progress update via WebSocket. Determines user by document owner."""
    try:
        from app.core.processing_websocket import processing_ws_manager
        from app.db.session import SessionLocal as _SyncSession
        from app.models.document import Document as _Doc
        db = _SyncSession()
        try:
            doc = db.query(_Doc).filter(_Doc.uuid == document_id).first()
            user_id = str(doc.uploaded_by) if doc else None
        finally:
            db.close()
        if user_id:
            await processing_ws_manager.update_processing_step(
                document_id=document_id,
                user_id=user_id,
                step=step,
                status=status,
                progress=progress,
                message=message,
                details=details or []
            )
    except Exception as e:
        logger.warning(f"Failed to send progress update: {e}")


def run_async(coro):
    """Helper to run async code in a sync Celery task"""
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop.run_until_complete(coro)
    except RuntimeError:
        # Create new event loop if none exists or is closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class DocumentTask(Task):
    """Base task with database session management"""
    _db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DocumentTask, bind=True, name="app.tasks.document.process_document")
def process_document(self, document_id: str) -> Dict[str, Any]:
    """Process a document: extract text, generate embeddings, index"""
    
    try:
        # Get document from database
        document = self.db.query(Document).filter(Document.uuid == document_id).first()
        
        if not document:
            logger.error(f"Document {document_id} not found")
            return {"status": "error", "message": "Document not found"}
        
        # Ensure underlying file still exists before doing anything else
        storage_path = Path(document.storage_path)
        if not storage_path.exists() or storage_path.stat().st_size == 0:
            document.status = "failed"
            document.error_message = f"File missing or zero-byte on disk: {document.storage_path}"
            self.db.commit()
            return {"status": "error", "message": document.error_message}

        # Update status
        document.status = "processing"
        self.db.commit()
        
        # Adaptive timeout helpers
        from datetime import datetime, timedelta
        def compute_budgets(file_size_bytes: int, file_type: str):
            size_mb = max(1, int(file_size_bytes / (1024 * 1024)))
            # Base budgets (seconds)
            if file_type.startswith("image/"):
                soft, hard = 120 + 2 * size_mb, 180 + 3 * size_mb
            elif file_type in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
                soft, hard = 60 + 1 * size_mb, 120 + 2 * size_mb
            else:
                soft, hard = 45 + size_mb, 90 + 2 * size_mb
            # Clamp to sane bounds
            soft = min(soft, 240)
            hard = min(hard, 360)
            return soft, hard

        soft_limit_s, hard_limit_s = compute_budgets(document.file_size or 0, document.file_type or "")
        step_started_at = datetime.utcnow()

        # Step 1: Virus Scan (0-20%)
        run_async(send_progress_update(
            document_id, 
            "virus_scan", 
            "processing", 
            0, 
            f"Starting virus scan for {document.filename}...",
            ["Checking file integrity", "Scanning for threats"]
        ))
        
        try:
            from app.services.virus_scanner import VirusScanner
            from app.core.config import settings
            scan_start = time.time()
            scanner = VirusScanner()
            
            # Send progress during scan
            run_async(send_progress_update(
                document_id, "virus_scan", "processing", 5, 
                f"Scanning {document.file_size // 1024}KB file...",
                [f"Elapsed: {time.time() - scan_start:.1f}s"]
            ))
            
            scan_result = scanner.scan_file_sync(Path(document.storage_path))
            scan_duration = time.time() - scan_start
            
            document.virus_scan_status = scan_result.get("status", "error")
            self.db.commit()
            
            # Send completion
            run_async(send_progress_update(
                document_id, "virus_scan", "processing", 15,
                f"Scan complete in {scan_duration:.1f}s",
                [f"Status: {scan_result.get('status', 'unknown')}"]
            ))

            # Handle infected files - always block these
            if scan_result.get("status") == "infected":
                run_async(send_progress_update(
                    document_id, "virus_scan", "failed", 100,
                    "⚠️ Virus detected!",
                    scan_result.get('threats', [])
                ))
                document.status = "failed"
                document.error_message = f"Virus detected: {', '.join(scan_result.get('threats', []))}"
                self.db.commit()
                logger.error(f"SECURITY: Virus detected in {document.filename}: {document.error_message}")
                return {"status": "error", "message": document.error_message}
            
            # Handle scan errors based on configuration
            if scan_result.get("status") == "error":
                if settings.VIRUS_SCAN_FAIL_ON_ERROR:
                    # Production strict mode: fail the upload
                    run_async(send_progress_update(
                        document_id, "virus_scan", "failed", 100,
                        "Virus scan failed",
                        [scan_result.get('error', 'Unknown error')]
                    ))
                    document.status = "failed"
                    document.error_message = f"Virus scan error: {scan_result.get('error', 'Unknown error')}"
                    self.db.commit()
                    logger.error(f"Virus scan failed for {document.filename}: {document.error_message}")
                    return {"status": "error", "message": document.error_message}
                else:
                    # Development lenient mode: log warning and continue
                    logger.warning(f"Virus scan error for {document.filename}: {scan_result.get('error')}; continuing (lenient mode)")

            # Mark virus scan as completed
            run_async(send_progress_update(
                document_id, "virus_scan", "completed", 100,
                f"✅ File is clean ({scan_duration:.1f}s)",
                [f"No threats detected"]
            ))
            logger.info(f"✅ Virus scan completed for: {document.filename} (status={document.virus_scan_status})")
        except Exception as e:
            from app.core.config import settings
            logger.error(f"Virus scan exception for {document.filename}: {e}")
            document.virus_scan_status = "error"
            self.db.commit()
            
            # Respect fail_on_error flag
            if settings.VIRUS_SCAN_FAIL_ON_ERROR:
                document.status = "failed"
                document.error_message = f"Virus scan failed: {str(e)}"
                self.db.commit()
                return {"status": "error", "message": document.error_message}

        # Step 2: Text Extraction (20-50%)
        # Check if this is an image file - skip text extraction for images
        file_extension = Path(document.storage_path).suffix.lower().strip('.')
        
        run_async(send_progress_update(
            document_id, "text_extraction", "processing", 0,
            f"Extracting text from {document.filename}...",
            [f"File type: {file_extension}"]
        ))
        
        text_service = TextExtractionService()
        extract_start = time.time()
        if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp']:
            # Images don't have extractable text - mark as text_extracted with empty text
            document.full_text = ""
            document.status = "text_extracted"
            self.db.commit()
            run_async(send_progress_update(
                document_id, "text_extraction", "completed", 100,
                "✅ Image file (no text to extract)",
                [f"Completed in {time.time() - extract_start:.1f}s"]
            ))
            logger.info(f"Skipped text extraction for image file: {document.filename}")
        else:
            # Regular text extraction for documents
            run_async(send_progress_update(
                document_id, "text_extraction", "processing", 30,
                f"Parsing {file_extension} file...",
                [f"Processing {document.file_size // 1024}KB"]
            ))
            
            extracted = text_service.extract_text_sync(Path(document.storage_path))
            extract_duration = time.time() - extract_start
            
            # Enforce adaptive hard limit per step
            if datetime.utcnow() - step_started_at > timedelta(seconds=hard_limit_s):
                run_async(send_progress_update(
                    document_id, "text_extraction", "failed", 100,
                    f"⏱️ Timeout ({hard_limit_s}s exceeded)"
                ))
                document.status = "failed"
                document.error_message = f"Processing timeout (> {hard_limit_s}s)"
                self.db.commit()
                return {"status": "error", "message": document.error_message}
            
            if extracted and extracted.get("success"):
                text_length = len(extracted.get("text", ""))
                document.full_text = extracted.get("text", "")
                document.status = "text_extracted"
                self.db.commit()
                run_async(send_progress_update(
                    document_id, "text_extraction", "completed", 100,
                    f"✅ Extracted {text_length:,} characters ({extract_duration:.1f}s)",
                    [f"Ready for indexing"]
                ))
            else:
                error_msg = extracted.get("error") if extracted else "Unknown extraction error"
                run_async(send_progress_update(
                    document_id, "text_extraction", "failed", 100,
                    f"❌ Extraction failed: {error_msg}"
                ))
                document.status = "failed"
                document.error_message = error_msg
                self.db.commit()
                return {"status": "error", "message": document.error_message}
        
        # Step 3: Elasticsearch Indexing (50-70%)
        run_async(send_progress_update(
            document_id, "elasticsearch_indexing", "processing", 0,
            "Indexing in Elasticsearch...",
            ["Preparing metadata", "Building search index"]
        ))
        
        # Prepare metadata
        metadata = {
                "filename": document.filename,
                "title": document.title or document.filename,
                "description": document.description or "",
                "file_type": document.file_type,
                "tags": document.tags or [],
                "uploaded_by": str(document.uploaded_by),
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat() if document.updated_at else document.created_at.isoformat(),
                "file_size": document.file_size
        }
        
        # Step 3: Elasticsearch Keyword Indexing (40-70%)
        elasticsearch_success = False
        try:
            from app.services.search.elasticsearch_service import ElasticsearchService
            es_start = time.time()
            es = ElasticsearchService()
            
            # Index document (returns bool, uses document_id as ES doc ID)
            success = es.index_document_sync(
                document_id=str(document.uuid),
                content=document.full_text,
                metadata=metadata
            )
            es_duration = time.time() - es_start
            
            # Commit if indexing succeeded
            if success:
                document.elasticsearch_id = str(document.uuid)
                self.db.commit()
                elasticsearch_success = True
                
                run_async(send_progress_update(
                    document_id, "elasticsearch_indexing", "completed", 100,
                    f"✅ Indexed in Elasticsearch ({es_duration:.1f}s)",
                    ["Document is now keyword searchable"]
                ))
                logger.info(f"✅ Elasticsearch indexed: {document.filename}")
            else:
                logger.warning(f"⚠️ Elasticsearch indexing failed for {document.filename}")
                run_async(send_progress_update(
                    document_id, "elasticsearch_indexing", "failed", 100,
                    f"⚠️ Elasticsearch indexing failed",
                    ["Check logs for details"]
                ))
                elasticsearch_success = False
                
        except Exception as e:
            logger.error(f"❌ Elasticsearch indexing error for {document.filename}: {e}")
            run_async(send_progress_update(
                document_id, "elasticsearch_indexing", "failed", 100,
                f"⚠️ Elasticsearch indexing failed",
                [str(e)]
            ))
            elasticsearch_success = False
        
        # Step 4: Qdrant Vector Indexing (70-100%)
        # Check if document has text content for vectorization
        has_text_content = bool(document.full_text and document.full_text.strip())
        
        qdrant_success = False
        if not has_text_content:
            # Images and files without text - skip vector indexing
            logger.info(f"📷 Skipping Qdrant for {document.filename} - no text content (likely image)")
            run_async(send_progress_update(
                document_id, "qdrant_vector_index", "completed", 100,
                "⏭️ Skipped (no text content)",
                ["Image/binary file - metadata searchable only"]
            ))
            document.qdrant_id = None  # Explicitly None, not False!
            self.db.commit()
            qdrant_success = True  # It's OK to skip
        else:
            # Has text content - proceed with vector indexing
            run_async(send_progress_update(
                document_id, "qdrant_vector_index", "processing", 0,
                "Generating embeddings for semantic search...",
                ["Creating vector representations"]
            ))
            
            try:
                from app.services.search.qdrant_service import QdrantService
                qdrant_start = time.time()
                qdrant = QdrantService()
                qdrant_doc_id = qdrant.index_document_sync(
                    document_id=str(document.uuid),
                    content=document.full_text,
                    metadata=metadata
                )
                qdrant_duration = time.time() - qdrant_start
                
                # Commit if we got an ID back
                if qdrant_doc_id:
                    document.qdrant_id = qdrant_doc_id
                    self.db.commit()
                    qdrant_success = True
                    
                    run_async(send_progress_update(
                        document_id, "qdrant_vector_index", "completed", 100,
                        f"✅ Vector indexed ({qdrant_duration:.1f}s)",
                        ["Semantic search ready"]
                    ))
                    logger.info(f"✅ Qdrant indexed: {document.filename}")
                else:
                    logger.warning(f"⚠️ Qdrant returned no ID for {document.filename}")
                    qdrant_success = False
                    
            except Exception as e:
                logger.error(f"❌ Qdrant indexing failed for {document.filename}: {e}")
                run_async(send_progress_update(
                    document_id, "qdrant_vector_index", "failed", 100,
                    f"⚠️ Vector indexing failed",
                    [str(e)]
                ))
                qdrant_success = False
        
        # CRITICAL: Determine final status based on content type and indexing success
        if elasticsearch_success and qdrant_success:
            if has_text_content:
                # Document with text - fully searchable
                document.status = "indexed"
                logger.info(f"✅ Document FULLY indexed in all systems: {document.filename}")
            else:
                # Image/binary - stored but not semantically searchable
                document.status = "stored"
                logger.info(f"📷 Document stored (metadata searchable): {document.filename}")
            
            self.db.commit()
            return {
                "status": "success",
                "document_id": str(document_id),
                "text_length": len(document.full_text or ""),
                "elasticsearch_id": document.elasticsearch_id,
                "qdrant_id": document.qdrant_id,
                "is_text_searchable": has_text_content
            }
        elif elasticsearch_success or qdrant_success:
            # Partial success - mark as such, not 'indexed'
            document.status = "partially_indexed"
            document.error_message = f"ES: {'✓' if elasticsearch_success else '✗'}, Qdrant: {'✓' if qdrant_success else '✗'}"
            self.db.commit()
            logger.warning(f"⚠️ Document partially indexed: {document.filename} - {document.error_message}")
            return {
                "status": "partial_success",
                "document_id": str(document_id),
                "text_length": len(document.full_text or ""),
                "warning": document.error_message
            }
        else:
            # Both failed - mark as failed
            document.status = "failed"
            document.error_message = "Both Elasticsearch and Qdrant indexing failed"
            self.db.commit()
            logger.error(f"❌ Document indexing completely failed: {document.filename}")
            return {
                "status": "error",
                "message": document.error_message
            }
            
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        
        if document:
            document.status = "failed"
            document.error_message = str(e)
            self.db.commit()
        
        return {
            "status": "error",
            "message": str(e)
        }


@celery_app.task(base=DocumentTask, bind=True, name="app.tasks.document.batch_process_documents")
def batch_process_documents(self, document_ids: list) -> Dict[str, Any]:
    """Process multiple documents in batch"""
    
    results = {
        "total": len(document_ids),
        "successful": 0,
        "failed": 0,
        "documents": []
    }
    
    for doc_id in document_ids:
        result = process_document.delay(doc_id)
        
        # Track results
        if result.get("status") == "success":
            results["successful"] += 1
        else:
            results["failed"] += 1
        
        results["documents"].append({
            "id": doc_id,
            "task_id": result.id,
            "status": result.get("status")
        })
    
    return results


@celery_app.task(base=DocumentTask, bind=True, name="app.tasks.document.process_pending_documents")
def process_pending_documents(self) -> Dict[str, Any]:
    """Periodic task to enqueue documents awaiting processing.

    Picks up both 'pending' and legacy 'uploaded' statuses and immediately
    flips them to 'processing' to avoid duplicate task enqueues.
    """
    try:
        pending_docs = (
            self.db.query(Document)
            .filter(Document.status.in_(["pending", "uploaded"]))
            .limit(25)
            .all()
        )

        if not pending_docs:
            return {"status": "success", "message": "No pending documents"}

        processed = 0
        for doc in pending_docs:
            # Mark as processing to prevent re-enqueueing in subsequent runs
            doc.status = "processing"
            self.db.add(doc)
            self.db.commit()

            process_document.delay(str(doc.uuid))
            processed += 1

        return {"status": "success", "processed": processed}
    except Exception as e:
        logger.error(f"Error processing pending documents: {str(e)}")
        return {"status": "error", "message": str(e)}


@celery_app.task(base=DocumentTask, bind=True, name="app.tasks.document.reindex_document")
def reindex_document(self, document_id: str) -> Dict[str, Any]:
    """Reindex a document in search engines"""
    
    try:
        document = self.db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            return {"status": "error", "message": "Document not found"}
        
        search_service = SearchService(self.db)
        
        # Reindex in Elasticsearch
        search_service.index_document_elasticsearch(document)
        
        # Reindex in Weaviate
        search_service.index_document_qdrant(document)
        
        document.is_indexed = True
        self.db.commit()
        
        return {
            "status": "success",
            "document_id": str(document_id)
        }
        
    except Exception as e:
        logger.error(f"Error reindexing document {document_id}: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }