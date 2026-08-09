"""
Celery tasks initialization
"""
from app.core.celery_app import celery_app

# Import all task modules to register them
from app.tasks import document, search, llm, maintenance

__all__ = ["celery_app", "document", "search", "llm", "maintenance"]