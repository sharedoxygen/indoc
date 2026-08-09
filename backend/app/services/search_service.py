"""
Search service for document retrieval
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy import select
from app.models.document import Document

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result data class"""
    document_id: str
    chunk_id: Optional[str]
    content: str
    score: float
    metadata: Dict[str, Any]


class SearchService:
    """Service for searching and indexing documents using Elasticsearch and Weaviate"""
    
    def __init__(self, db=None):
        # db is optional; kept for compatibility with callers that pass a Session
        self.db = db
        self.elasticsearch_client = None  # Initialized by init_elasticsearch_client()
        self.weaviate_client = None  # Initialized by init_weaviate_client()
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for documents matching the query
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional filters to apply
            
        Returns:
            List of search results
        """
        try:
            results = []
            
            # If we have a database session, search actual documents
            if self.db:
                # Search in document content and chunks
                from sqlalchemy import or_, and_
                
                # Convert Session to AsyncSession if needed
                if hasattr(self.db, 'execute'):
                    # Build query to search document content
                    search_query = select(Document).where(
                        or_(
                            Document.title.ilike(f"%{query}%"),
                            Document.description.ilike(f"%{query}%"),
                            Document.full_text.ilike(f"%{query}%")
                        )
                    )
                    
                    # Apply filters if provided
                    if filters:
                        if 'document_ids' in filters:
                            search_query = search_query.where(
                                Document.uuid.in_(filters['document_ids'])
                            )
                    
                    search_query = search_query.limit(limit)
                    
                    # Execute query
                    if hasattr(self.db, 'execute'):
                        # Async session
                        result = await self.db.execute(search_query)
                        documents = result.scalars().all()
                    else:
                        # Sync session
                        documents = self.db.query(Document).filter(
                            or_(
                                Document.title.ilike(f"%{query}%"),
                                Document.description.ilike(f"%{query}%"),
                                Document.full_text.ilike(f"%{query}%")
                            )
                        ).limit(limit).all()
                    
                    # Convert documents to search results
                    for doc in documents:
                        # Calculate relevance score (simplified)
                        score = 0.5
                        if doc.title and query.lower() in doc.title.lower():
                            score += 0.3
                        if doc.description and query.lower() in doc.description.lower():
                            score += 0.2
                        
                        results.append(SearchResult(
                            document_id=str(doc.uuid),
                            chunk_id=None,
                            content=doc.full_text[:1000] if doc.full_text else doc.description or "",
                            score=score,
                            metadata={
                                "title": doc.title,
                                "filename": doc.filename,
                                "file_type": doc.file_type,
                                "created_at": doc.created_at.isoformat() if doc.created_at else None
                            }
                        ))
            
            logger.info(f"Search completed for query: {query[:50]}... Found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        alpha: float = 0.5
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining keyword and vector search
        
        Args:
            query: Search query string
            limit: Maximum number of results
            alpha: Weight for combining keyword and vector scores (0-1)
            
        Returns:
            List of search results
        """
        try:
            # TODO: Implement hybrid search
            results = []
            
            logger.info(f"Hybrid search completed for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error during hybrid search: {str(e)}")
            return []
    
    async def get_document_content_for_chat(
        self,
        document_ids: List[str],
        max_content_length: int = 4000
    ) -> List[Dict[str, Any]]:
        """
        Get document content optimized for chat conversations
        
        Args:
            document_ids: List of document UUIDs
            max_content_length: Maximum content length per document
            
        Returns:
            List of documents with content and metadata
        """
        try:
            documents = []
            
            if self.db:
                if hasattr(self.db, 'execute'):
                    # Async session
                    query = select(Document).where(Document.uuid.in_(document_ids))
                    result = await self.db.execute(query)
                    db_documents = result.scalars().all()
                else:
                    # Sync session
                    db_documents = self.db.query(Document).filter(
                        Document.uuid.in_(document_ids)
                    ).all()
                
                for doc in db_documents:
                    content = doc.full_text or doc.description or ""
                    
                    # Truncate content if too long
                    if len(content) > max_content_length:
                        content = content[:max_content_length] + "... (truncated)"
                    
                    documents.append({
                        "id": str(doc.uuid),
                        "title": doc.title or doc.filename,
                        "content": content,
                        "file_type": doc.file_type,
                        "metadata": {
                            "filename": doc.filename,
                            "file_size": doc.file_size,
                            "created_at": doc.created_at.isoformat() if doc.created_at else None,
                            "tags": doc.tags or []
                        }
                    })
            
            logger.info(f"Retrieved {len(documents)} documents for chat")
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving document content for chat: {e}")
            return []
    
    async def get_document_summary_context(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get document context optimized for summarization
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document with full content and metadata
        """
        try:
            if self.db:
                if hasattr(self.db, 'execute'):
                    # Async session
                    query = select(Document).where(Document.uuid == document_id)
                    result = await self.db.execute(query)
                    doc = result.scalar_one_or_none()
                else:
                    # Sync session
                    doc = self.db.query(Document).filter(
                        Document.uuid == document_id
                    ).first()
                
                if doc:
                    return {
                        "id": str(doc.uuid),
                        "title": doc.title or doc.filename,
                        "content": doc.full_text or "",
                        "description": doc.description,
                        "file_type": doc.file_type,
                        "metadata": {
                            "filename": doc.filename,
                            "file_size": doc.file_size,
                            "created_at": doc.created_at.isoformat() if doc.created_at else None,
                            "tags": doc.tags or [],
                            "language": doc.language
                        }
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving document for summary: {e}")
            return None
    
    # --- Indexing stubs used by Celery tasks ---
    def index_document_elasticsearch(self, document: Any) -> bool:
        """Index a document in Elasticsearch (stub)."""
        try:
            logger.info(f"[SearchService] (stub) Indexing document in Elasticsearch: id={document.id}")
            return True
        except Exception as e:
            logger.error(f"Elasticsearch indexing failed: {e}")
            return False

    def index_document_weaviate(self, document: Any) -> bool:
        """Index a document in Weaviate (stub)."""
        try:
            logger.info(f"[SearchService] (stub) Indexing document in Weaviate: id={document.id}")
            return True
        except Exception as e:
            logger.error(f"Weaviate indexing failed: {e}")
            return False

    def search_sync(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Synchronous version of search for Celery tasks"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.search(query, limit, filters))
        finally:
            loop.close()