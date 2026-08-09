#!/usr/bin/env python3
"""
Initialize Search Indices
Populate Elasticsearch and Qdrant with existing documents
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService
from app.services.text_extraction_service import TextExtractionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchIndexInitializer:
    """Initialize and populate search indices"""
    
    def __init__(self):
        self.es_service = ElasticsearchService()
        self.qdrant_service = QdrantService()
        self.text_service = TextExtractionService()
    
    async def initialize_indices(self):
        """Initialize Elasticsearch and Qdrant indices"""
        logger.info("🚀 Initializing search indices...")
        
        # Initialize Elasticsearch index
        logger.info("📊 Setting up Elasticsearch index...")
        es_ready = await self.es_service.ensure_index_exists()
        if not es_ready:
            logger.error("❌ Failed to initialize Elasticsearch index")
            return False
        
        # Initialize Qdrant schema
        logger.info("🧠 Setting up Qdrant schema...")
        qdrant_ready = await self.qdrant_service.ensure_schema_exists()
        if not qdrant_ready:
            logger.error("❌ Failed to initialize Qdrant schema")
            return False
        
        logger.info("✅ Search indices initialized successfully")
        return True
    
    async def populate_indices(self):
        """Populate indices with existing documents"""
        logger.info("📄 Populating search indices with documents...")
        
        async with AsyncSessionLocal() as session:
            # Get all documents
            result = await session.execute(
                select(Document).where(Document.status == 'indexed')
            )
            documents = result.scalars().all()
            
            logger.info(f"Found {len(documents)} indexed documents to process")
            
            success_count = 0
            for i, doc in enumerate(documents):
                try:
                    # Use existing full_text or extract from storage_path
                    if doc.full_text:
                        content = doc.full_text
                    elif doc.storage_path:
                        content = await self.text_service.extract_text(doc.storage_path, doc.file_type)
                    else:
                        content = doc.description or doc.filename
                    
                    # Prepare metadata
                    metadata = {
                        "filename": doc.filename,
                        "title": doc.title or doc.filename,
                        "description": doc.description or "",
                        "file_type": doc.file_type,
                        "tags": doc.tags or [],
                        "uploaded_by": str(doc.uploaded_by),
                        "created_at": doc.created_at.isoformat(),
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else doc.created_at.isoformat(),
                        "file_size": doc.file_size
                    }
                    
                    # Index in both services concurrently
                    es_task = self.es_service.index_document(str(doc.uuid), content, metadata)
                    qdrant_task = self.qdrant_service.add_document(str(doc.uuid), content, metadata)
                    
                    es_success, qdrant_success = await asyncio.gather(
                        es_task, qdrant_task, return_exceptions=True
                    )
                    
                    if es_success and qdrant_success:
                        success_count += 1
                    
                    # Progress logging
                    if (i + 1) % 50 == 0:
                        logger.info(f"📊 Processed {i + 1}/{len(documents)} documents ({success_count} successful)")
                
                except Exception as e:
                    logger.error(f"Error processing document {doc.uuid}: {str(e)}")
            
            logger.info(f"✅ Successfully indexed {success_count}/{len(documents)} documents")
            return success_count
    
    async def health_check(self):
        """Check health of search services"""
        logger.info("🔍 Checking search services health...")
        
        # Check Elasticsearch
        es_health = await self.es_service.health_check()
        logger.info(f"📊 Elasticsearch: {es_health['status']}")
        
        # Check Qdrant
        qdrant_health = await self.qdrant_service.health_check()
        logger.info(f"🧠 Qdrant: {qdrant_health['status']}")
        
        return es_health["status"] == "healthy" and qdrant_health["status"] == "healthy"


async def main():
    """Main function"""
    initializer = SearchIndexInitializer()
    
    # Check health first
    if not await initializer.health_check():
        logger.error("❌ Search services are not healthy")
        return
    
    # Initialize indices
    if not await initializer.initialize_indices():
        logger.error("❌ Failed to initialize search indices")
        return
    
    # Populate with existing documents
    indexed_count = await initializer.populate_indices()
    
    logger.info("🎉 Search index initialization complete!")
    logger.info(f"📊 {indexed_count} documents are now searchable")
    logger.info("🔍 Hybrid search (Elasticsearch + Qdrant) is ready!")


if __name__ == "__main__":
    asyncio.run(main())
