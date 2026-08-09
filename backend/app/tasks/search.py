"""
Search-related Celery tasks
"""
from app.core.celery_app import celery_app
from celery import Task
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
import logging

logger = logging.getLogger(__name__)


class SearchTask(Task):
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


@celery_app.task(base=SearchTask, bind=True, name="app.tasks.search.reindex_all")
def reindex_all_documents(self):
    """Reindex all documents in search engines"""
    logger.info("Starting full reindex of all documents")
    # Implementation here
    return {"status": "success", "message": "Reindex completed"}
