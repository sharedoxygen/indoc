"""
Maintenance Celery tasks
"""
from app.core.celery_app import celery_app
from celery import Task
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.document import Document

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.maintenance.cleanup_old_sessions")
def cleanup_old_sessions():
    """Clean up old user sessions"""
    logger.info("Cleaning up old sessions")
    # Implementation here
    return {"status": "success", "cleaned": 0}


@celery_app.task(name="app.tasks.maintenance.update_tenant_usage")
def update_tenant_usage():
    """Update tenant usage statistics"""
    logger.info("Updating tenant usage")
    # Implementation here
    return {"status": "success"}


@celery_app.task(name="app.tasks.maintenance.fail_stuck_documents")
def fail_stuck_documents(timeout_minutes: int = 5):
    """Mark documents stuck in 'uploaded' or 'processing' beyond timeout as failed."""
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stuck = db.query(Document).filter(
            Document.status.in_(["uploaded", "processing"]),
        ).all()
        updated = 0
        for doc in stuck:
            # If never updated or very old, mark failed
            if not doc.updated_at or doc.updated_at < cutoff:
                doc.status = "failed"
                if not getattr(doc, 'error_message', None):
                    doc.error_message = "Processing timeout"
                updated += 1
        if updated:
            db.commit()
        logger.info(f"fail_stuck_documents: marked {updated} as failed")
        return {"status": "success", "failed": updated}
    except Exception as e:
        logger.error(f"fail_stuck_documents error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
