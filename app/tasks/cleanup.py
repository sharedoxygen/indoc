"""
Cleanup tasks for maintaining data integrity
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.document import Document
from app.core.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.cleanup.cleanup_orphaned_documents")
def cleanup_orphaned_documents_task():
    """Celery task wrapper for orphaned document cleanup"""
    return cleanup_orphaned_documents()


@celery_app.task(name="app.tasks.cleanup.cleanup_failed_uploads")
def cleanup_failed_uploads_task():
    """Celery task wrapper for failed upload cleanup"""
    return cleanup_failed_uploads()


@celery_app.task(name="app.tasks.cleanup.cleanup_temp_files")
def cleanup_temp_files_task():
    """Celery task wrapper for temp file cleanup"""
    return cleanup_temp_files()


def cleanup_orphaned_documents():
    """
    Remove document records that reference non-existent files.
    This handles cases where file storage failed but DB records were created.
    """
    db: Session = SessionLocal()
    try:
        logger.info("Starting cleanup of orphaned documents...")
        
        # Find documents with status 'pending' that are older than 1 hour
        # These might be orphaned from failed uploads
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        orphaned_docs = db.query(Document).filter(
            Document.status == "pending",
            Document.created_at < cutoff_time
        ).all()
        
        cleaned_count = 0
        for doc in orphaned_docs:
            # Check if the actual file exists
            storage_path = Path(doc.storage_path)
            if not storage_path.exists():
                logger.warning(f"Removing orphaned document: {doc.filename} (file not found)")
                db.delete(doc)
                cleaned_count += 1
            else:
                # File exists but document is stuck in pending - mark as uploaded
                doc.status = "uploaded"
                logger.info(f"Marking stuck document as uploaded: {doc.filename}")
        
        db.commit()
        logger.info(f"Cleanup completed: {cleaned_count} orphaned documents removed")
        return {"status": "success", "cleaned": cleaned_count}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


     def cleanup_failed_uploads():
    """
    Remove document records for files that failed to upload properly.
    """
    db: Session = SessionLocal()
    try:
        logger.info("Starting cleanup of failed uploads...")
        
        # Find documents with status 'failed' that are older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        failed_docs = db.query(Document).filter(
            Document.status == "failed",
            Document.created_at < cutoff_time
        ).all()
        
        cleaned_count = 0
        for doc in failed_docs:
            # Remove the file if it exists
            storage_path = Path(doc.storage_path)
            if storage_path.exists():
                try:
                    storage_path.unlink()
                    logger.info(f"Removed failed upload file: {storage_path}")
                except Exception as e:
                    logger.warning(f"Could not remove file {storage_path}: {e}")
            
            # Remove the document record
            db.delete(doc)
            cleaned_count += 1
        
        db.commit()
        logger.info(f"Failed upload cleanup completed: {cleaned_count} records removed")
        return {"status": "success", "cleaned": cleaned_count}
        
    except Exception as e:
        logger.error(f"Failed upload cleanup failed: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


     def cleanup_temp_files():
    """
    Remove temporary files older than 1 hour.
    """
    try:
        logger.info("Starting cleanup of temporary files...")
        
        temp_dir = Path(settings.TEMP_REPO_PATH)
        if not temp_dir.exists():
            return {"status": "success", "cleaned": 0}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        cleaned_count = 0
        
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Removed temp file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove temp file {file_path}: {e}")
        
        logger.info(f"Temp file cleanup completed: {cleaned_count} files removed")
        return {"status": "success", "cleaned": cleaned_count}
        
    except Exception as e:
        logger.error(f"Temp file cleanup failed: {e}")
        return {"status": "error", "message": str(e)}
