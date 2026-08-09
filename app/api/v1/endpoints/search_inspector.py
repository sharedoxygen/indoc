"""
Search Inspector API - provides read-only access to search system internals
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.search.elasticsearch_service import get_elasticsearch_service
from app.services.search.qdrant_service import get_qdrant_service
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.document import Document

router = APIRouter()


class SearchSystemStats(BaseModel):
    postgresql: int
    elasticsearch: int
    qdrant: int
    synced: bool


class ElasticsearchDocument(BaseModel):
    id: str
    score: float | None
    filename: str | None
    title: str | None
    content_preview: str | None
    file_type: str | None
    file_size: int | None
    tags: list[str] | None
    created_at: str | None
    uploaded_by: str | None


class QdrantPoint(BaseModel):
    id: str
    document_id: str | None
    filename: str | None
    content_preview: str | None
    indexed_at: str | None
    file_type: str | None
    vector_dimension: int | None
    chunk_index: int | None


class PostgresDocument(BaseModel):
    uuid: str
    filename: str
    status: str
    has_elasticsearch_id: bool
    has_qdrant_id: bool
    created_at: str
    file_size: int | None
    file_type: str | None
    uploaded_by: str | None
    error_message: str | None
    processing_time_ms: int | None


@router.get("/stats", response_model=SearchSystemStats)
async def get_search_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document counts from all search systems"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        # PostgreSQL count
        result = await db.execute(select(func.count(Document.id)))
        pg_count = result.scalar() or 0
        logger.info(f"PostgreSQL count: {pg_count}")
        
        # Elasticsearch count
        es_service = get_elasticsearch_service()
        es_count = await es_service.count_documents()
        logger.info(f"Elasticsearch count: {es_count}")
        
        # Qdrant count
        qdrant_service = get_qdrant_service()
        qdrant_count = qdrant_service.count_vectors()
        logger.info(f"Qdrant count: {qdrant_count}")
        
        return SearchSystemStats(
            postgresql=pg_count,
            elasticsearch=es_count,
            qdrant=qdrant_count,
            synced=(pg_count == es_count == qdrant_count)
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Stats error: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}\n{error_trace[:500]}")


@router.get("/elasticsearch", response_model=List[ElasticsearchDocument])
async def get_elasticsearch_documents(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """Get documents from Elasticsearch"""
    es_service = get_elasticsearch_service()
    
    try:
        # Use match_all query to get all documents
        response = await es_service.client.search(
            index=es_service.index_name,
            body={
                "query": {"match_all": {}},
                "size": limit,
                "sort": [{"created_at": {"order": "desc"}}]
            }
        )
        
        docs = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            docs.append(ElasticsearchDocument(
                id=source.get("document_id", "unknown"),
                score=hit.get("_score"),
                filename=source.get("filename"),
                title=source.get("title"),
                content_preview=source.get("full_text", "")[:300] if source.get("full_text") else None,
                file_type=source.get("file_type"),
                file_size=source.get("file_size"),
                tags=source.get("tags", []),
                created_at=source.get("created_at"),
                uploaded_by=source.get("uploaded_by")
            ))
        
        return docs
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Elasticsearch error: {str(e)}\n{error_trace[:500]}")


@router.get("/qdrant", response_model=List[QdrantPoint])
async def get_qdrant_vectors(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """Get vector points from Qdrant"""
    qdrant_service = get_qdrant_service()
    
    try:
        points = qdrant_service.scroll_points(limit=limit)
        
        vectors = []
        for point in points:
            payload = point.get("payload", {})
            # Get vector dimension from the point if available
            vector_dim = None
            if "vector" in point and point["vector"]:
                vector_dim = len(point["vector"]) if isinstance(point["vector"], list) else None
            
            vectors.append(QdrantPoint(
                id=str(point.get("id")),
                document_id=payload.get("document_id"),
                filename=payload.get("filename"),
                content_preview=payload.get("content", "")[:300] if payload.get("content") else None,
                indexed_at=payload.get("indexed_at"),
                file_type=payload.get("file_type"),
                vector_dimension=vector_dim or 384,  # Default to MiniLM dimension
                chunk_index=payload.get("chunk_index", 0)
            ))
        
        return vectors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant error: {str(e)}")


@router.get("/postgresql", response_model=List[PostgresDocument])
async def get_postgresql_documents(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get documents from PostgreSQL"""
    
    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    documents = result.scalars().all()
    
    docs = []
    for doc in documents:
        # Calculate processing time if available
        processing_time = None
        if doc.created_at and doc.updated_at:
            processing_time = int((doc.updated_at - doc.created_at).total_seconds() * 1000)
        
        # Get uploaded_by user email/name if available
        uploaded_by_str = None
        if hasattr(doc, 'uploaded_by_user') and doc.uploaded_by_user:
            uploaded_by_str = doc.uploaded_by_user.email or f"User#{doc.uploaded_by}"
        elif doc.uploaded_by:
            uploaded_by_str = f"User#{doc.uploaded_by}"
        
        docs.append(PostgresDocument(
            uuid=str(doc.uuid),
            filename=doc.filename,
            status=doc.status,
            has_elasticsearch_id=doc.elasticsearch_id is not None,
            has_qdrant_id=doc.qdrant_id is not None,
            created_at=doc.created_at.isoformat() if doc.created_at else "",
            file_size=doc.file_size,
            file_type=doc.file_type,
            uploaded_by=uploaded_by_str,
            error_message=doc.error_message,
            processing_time_ms=processing_time
        ))
    
    return docs

