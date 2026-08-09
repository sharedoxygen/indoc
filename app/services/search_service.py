"""
Search service for document retrieval
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID as UUID_t
from dataclasses import dataclass
from app.core.cache import cache_service
from app.core.document_scope import get_effective_document_ids
from sqlalchemy import select
from app.models.document import Document
from app.models.user import User

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
    """Service for searching and indexing documents using Elasticsearch and Qdrant"""
    
    def __init__(self, db=None):
        # db is optional; kept for compatibility with callers that pass a Session
        self.db = db
        # Use the shared app-level clients rather than opening a new
        # Elasticsearch/Qdrant connection (and reloading the embedding
        # model) on every SearchService instantiation - this class is
        # created per-request by chat, conversation, and MCP services.
        try:
            from app.services.search.elasticsearch_service import get_elasticsearch_service
            self.elasticsearch_client = get_elasticsearch_service()
        except Exception as e:
            logger.warning(f"Failed to initialize Elasticsearch client: {e}")
            self.elasticsearch_client = None

        try:
            from app.services.search.qdrant_service import get_qdrant_service
            self.qdrant_client = get_qdrant_service()
        except Exception as e:
            logger.warning(f"Failed to initialize Qdrant client: {e}")
            self.qdrant_client = None
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user: Optional[User] = None,
        selected_document_ids: Optional[set] = None
    ) -> List[SearchResult]:
        """
        Search for documents matching the query with role-based scope enforcement
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            filters: Optional filters to apply
            user: Current user (for scope enforcement)
            selected_document_ids: Optional set of document IDs from frontend selection
            
        Returns:
            List of search results
        """
        try:
            # Try hybrid search first if clients are available
            if self.elasticsearch_client and self.qdrant_client:
                logger.debug(f"Using hybrid search for query: {query}")
                return await self.hybrid_search(query, limit, alpha=0.5, user=user, selected_document_ids=selected_document_ids)
            
            # Fallback to database search
            logger.debug(f"Using database search (fallback) for query: {query}")
            results = []
            
            # If we have a database session, search actual documents
            if self.db:
                # Search in document content and chunks
                from sqlalchemy import or_, and_
                
                # Apply scope-based filtering if user is provided
                effective_doc_ids = None
                if user and hasattr(self.db, 'execute'):
                    effective_doc_ids = await get_effective_document_ids(
                        self.db, user, selected_document_ids
                    )
                    if not effective_doc_ids:
                        # No accessible documents
                        return []
                
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
                    
                    # Apply scope filtering
                    if effective_doc_ids is not None:
                        search_query = search_query.where(Document.id.in_(effective_doc_ids))
                    
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
        alpha: float = 0.5,
        user: Optional[User] = None,
        selected_document_ids: Optional[set] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining Elasticsearch keyword search and Qdrant
        vector search, fused by min-max normalized weighted score.

        Args:
            query: Search query string
            limit: Maximum number of results
            alpha: Weight given to the keyword (Elasticsearch) score vs the
                vector (Qdrant) score, 0-1. 1.0 = keyword only, 0.0 = vector only.

        Returns:
            List of search results
        """
        if not self.db:
            return []

        # Always enforce scope (RBAC/ABAC + selection) before touching search engines
        allowed_uuids: Optional[set] = None
        if user and hasattr(self.db, 'execute'):
            effective_doc_ids = await get_effective_document_ids(
                self.db, user, selected_document_ids
            )
            if not effective_doc_ids:
                return []
            uuid_result = await self.db.execute(
                select(Document.uuid).where(Document.id.in_(effective_doc_ids))
            )
            allowed_uuids = {str(u) for u in uuid_result.scalars().all()}

        widened_limit = limit * 3
        es_hits: List[Dict[str, Any]] = []
        vector_hits: List[Dict[str, Any]] = []

        if self.elasticsearch_client:
            try:
                es_hits = await self.elasticsearch_client.search(query, limit=widened_limit)
            except Exception as e:
                logger.warning(f"Elasticsearch leg of hybrid search failed: {e}")

        if self.qdrant_client:
            try:
                import asyncio
                vector_hits = await asyncio.to_thread(
                    self.qdrant_client.vector_search, query, widened_limit
                )
            except Exception as e:
                logger.warning(f"Qdrant leg of hybrid search failed: {e}")

        if allowed_uuids is not None:
            es_hits = [h for h in es_hits if h.get("id") in allowed_uuids]
            vector_hits = [h for h in vector_hits if h.get("document_id") in allowed_uuids]

        if not es_hits and not vector_hits:
            # Both search engines unavailable or empty - fall back to DB keyword search
            logger.warning("Hybrid search found nothing via ES/Qdrant, falling back to DB search")
            return await self._keyword_fallback_search(query, limit, allowed_uuids)

        def normalize(scores: Dict[str, float]) -> Dict[str, float]:
            if not scores:
                return {}
            lo, hi = min(scores.values()), max(scores.values())
            if hi == lo:
                return {k: 1.0 for k in scores}
            return {k: (v - lo) / (hi - lo) for k, v in scores.items()}

        es_scores = normalize({h["id"]: h["score"] for h in es_hits})
        vector_scores = normalize({h["document_id"]: h["score"] for h in vector_hits})

        es_by_id = {h["id"]: h for h in es_hits}
        vector_by_id = {h["document_id"]: h for h in vector_hits}

        combined_ids = set(es_scores) | set(vector_scores)
        fused: List[Tuple[str, float]] = [
            (doc_id, alpha * es_scores.get(doc_id, 0.0) + (1 - alpha) * vector_scores.get(doc_id, 0.0))
            for doc_id in combined_ids
        ]
        fused.sort(key=lambda pair: pair[1], reverse=True)

        results: List[SearchResult] = []
        for doc_id, score in fused[:limit]:
            es_hit = es_by_id.get(doc_id)
            vec_hit = vector_by_id.get(doc_id)
            payload = (vec_hit or {}).get("payload", {})

            if es_hit:
                content = es_hit.get("snippet", "")
                title = es_hit.get("title") or es_hit.get("filename")
                filename = es_hit.get("filename")
                file_type = es_hit.get("file_type")
                created_at = es_hit.get("created_at")
            else:
                content = payload.get("content_preview", "")
                title = payload.get("title") or payload.get("filename")
                filename = payload.get("filename")
                file_type = payload.get("file_type")
                created_at = payload.get("created_at")

            results.append(SearchResult(
                document_id=doc_id,
                chunk_id=None,
                content=content[:1000],
                score=score,
                metadata={
                    "title": title,
                    "filename": filename,
                    "file_type": file_type,
                    "created_at": created_at
                }
            ))

        logger.info(
            f"Hybrid search completed for query: {query[:50]}... "
            f"({len(es_hits)} keyword, {len(vector_hits)} vector, {len(results)} fused)"
        )
        return results

    async def _keyword_fallback_search(
        self,
        query: str,
        limit: int,
        allowed_uuids: Optional[set] = None
    ) -> List[SearchResult]:
        """
        Last-resort DB LIKE search used when Elasticsearch and Qdrant are both
        unavailable. Scope must already be resolved by the caller.
        """
        try:
            from sqlalchemy import or_

            kw_query = select(Document).where(
                or_(
                    Document.title.ilike(f"%{query}%"),
                    Document.description.ilike(f"%{query}%"),
                    Document.full_text.ilike(f"%{query}%")
                )
            )
            if allowed_uuids is not None:
                kw_query = kw_query.where(Document.uuid.in_(allowed_uuids))
            kw_query = kw_query.limit(limit)

            kw_result = await self.db.execute(kw_query)
            kw_docs = kw_result.scalars().all()

            results = []
            for doc in kw_docs:
                score = 0.5
                ql = query.lower()
                if doc.title and ql in doc.title.lower():
                    score += 0.3
                if doc.description and ql in doc.description.lower():
                    score += 0.2
                results.append(SearchResult(
                    document_id=str(doc.uuid),
                    chunk_id=None,
                    content=(doc.description or doc.full_text or "")[:1000],
                    score=score,
                    metadata={
                        "title": doc.title or doc.filename,
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None
                    }
                ))
            return results
        except Exception as e:
            logger.error(f"Error during keyword fallback search: {str(e)}")
            return []
    
    async def get_document_content_for_chat(
        self,
        document_ids: List[str],
        max_content_length: int = 4000
    ) -> List[Dict[str, Any]]:
        """
        Get document content optimized for chat conversations with caching
        
        Args:
            document_ids: List of document UUIDs
            max_content_length: Maximum content length per document
            
        Returns:
            List of documents with content and metadata
        """
        try:
            documents = []
            
            # Check cache for each document first
            cache_keys = [f"doc_content:{doc_id}" for doc_id in document_ids]
            cached_docs = await cache_service.get_many(cache_keys)
            
            uncached_ids = []
            for i, doc_id in enumerate(document_ids):
                cache_key = cache_keys[i]
                if cache_key in cached_docs:
                    documents.append(cached_docs[cache_key])
                else:
                    uncached_ids.append(doc_id)
            
            # Fetch uncached documents from DB
            if uncached_ids and self.db:
                # Normalize IDs to UUID objects for DB queries
                normalized_ids: List[UUID_t] = []
                for did in uncached_ids:
                    try:
                        normalized_ids.append(did if isinstance(did, UUID_t) else UUID_t(did))
                    except Exception:
                        # Skip invalid UUIDs
                        continue

                if hasattr(self.db, 'execute'):
                    # Async session - no tenant filtering for search service
                    query = select(Document).where(Document.uuid.in_(normalized_ids))
                    result = await self.db.execute(query)
                    db_documents = result.scalars().all()
                else:
                    # Sync session - no tenant filtering for search service
                    db_documents = self.db.query(Document).filter(
                        Document.uuid.in_(normalized_ids)
                    ).all()
                
                # Process and cache new documents
                new_cached_docs = {}
                for doc in db_documents:
                    content = doc.full_text or doc.description or ""
                    
                    # Truncate content if too long
                    if len(content) > max_content_length:
                        content = content[:max_content_length] + "... (truncated)"
                    
                    doc_data = {
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
                    }
                    documents.append(doc_data)
                    new_cached_docs[f"doc_content:{doc.uuid}"] = doc_data
                
                # Cache new documents for 30 minutes
                if new_cached_docs:
                    await cache_service.set_many(new_cached_docs, ttl=1800)
            
            logger.info(f"Retrieved {len(documents)} documents for chat ({len(cached_docs)} cached)")
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
    
    # --- Indexing methods used by Celery tasks (e.g. reindex_document) ---
    def _document_index_metadata(self, document: Any) -> Dict[str, Any]:
        """Build the metadata payload shared by Elasticsearch and Qdrant indexing"""
        return {
            "filename": document.filename,
            "title": document.title or document.filename,
            "description": document.description or "",
            "file_type": document.file_type,
            "tags": document.tags or [],
            "uploaded_by": str(document.uploaded_by),
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "file_size": document.file_size
        }

    def index_document_elasticsearch(self, document: Any) -> bool:
        """Index (or reindex) a document in Elasticsearch"""
        if not self.elasticsearch_client:
            logger.error(f"Cannot index document {document.id} in Elasticsearch: client unavailable")
            return False
        try:
            return self.elasticsearch_client.index_document_sync(
                document_id=str(document.uuid),
                content=document.full_text or "",
                metadata=self._document_index_metadata(document)
            )
        except Exception as e:
            logger.error(f"Elasticsearch indexing failed for document {document.id}: {e}")
            return False

    def index_document_qdrant(self, document: Any) -> bool:
        """Index (or reindex) a document in Qdrant"""
        if not document.full_text or not document.full_text.strip():
            logger.info(f"Skipping Qdrant indexing for document {document.id}: no text content")
            return True
        if not self.qdrant_client:
            logger.error(f"Cannot index document {document.id} in Qdrant: client unavailable")
            return False
        try:
            return bool(self.qdrant_client.index_document_sync(
                document_id=str(document.uuid),
                content=document.full_text,
                metadata=self._document_index_metadata(document)
            ))
        except Exception as e:
            logger.error(f"Qdrant indexing failed for document {document.id}: {e}")
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