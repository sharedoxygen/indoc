"""
Admin endpoints for system maintenance
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.tasks.cleanup import cleanup_orphaned_documents, cleanup_failed_uploads, cleanup_temp_files
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/cleanup/orphaned-documents")
async def cleanup_orphaned_documents_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger cleanup of orphaned documents"""
    # Check if user has admin privileges
    if not hasattr(current_user, 'role') or current_user.role.value != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = cleanup_orphaned_documents()
        return result
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


     @router.post("/cleanup/failed-uploads")
async def cleanup_failed_uploads_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger cleanup of failed uploads"""
    # Check if user has admin privileges
    if not hasattr(current_user, 'role') or current_user.role.value != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = cleanup_failed_uploads()
        return result
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


     @router.post("/cleanup/temp-files")
async def cleanup_temp_files_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger cleanup of temporary files"""
    # Check if user has admin privileges
    if not hasattr(current_user, 'role') or current_user.role.value != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = cleanup_temp_files()
        return result
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


     @router.post("/cleanup/all")
async def cleanup_all_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run all cleanup tasks"""
    # Check if user has admin privileges
    if not hasattr(current_user, 'role') or current_user.role.value != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        results = {
            "orphaned_documents": cleanup_orphaned_documents(),
            "failed_uploads": cleanup_failed_uploads(),
            "temp_files": cleanup_temp_files()
        }
        return results
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
