"""
LLM-related Celery tasks
"""
from app.core.celery_app import celery_app
from celery import Task
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.llm.generate_embeddings")
def generate_embeddings(text: str, model: str = "default"):
    """Generate embeddings for text using LLM"""
    logger.info(f"Generating embeddings for text with model: {model}")
    # Implementation here
    return {"status": "success", "embeddings": []}
