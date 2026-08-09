"""
Search endpoints
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit import AuditLog
from app.mcp.providers.search_provider import SearchProvider
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

router = APIRouter()
search_provider = SearchProvider()


class SearchQuery(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    offset: int = 0
    search_type: str = "hybrid"  # hybrid, keyword, semantic


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    execution_time_ms: float
    filters: Optional[Dict[str, Any]]


@router.post("/query", response_model=SearchResponse)
async def search_documents(
    search_query: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for documents using hybrid search
    """
    
    # Add user context to filters
    context = {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": getattr(current_user.role, "value", current_user.role)
        }
    }
    
    # Apply role-based filtering
    if search_query.filters is None:
        search_query.filters = {}
    
    if getattr(current_user.role, "value", current_user.role) not in ["Admin", "Reviewer"]:
        search_query.filters["uploaded_by"] = current_user.id
    
    # Perform search
    try:
        results = await search_provider.search(
            query=search_query.query,
            filters=search_query.filters,
            limit=search_query.limit,
            context=context
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    
    # Log search
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="search",
        resource_type="search",
        request_params={
            "query": search_query.query,
            "filters": search_query.filters,
            "limit": search_query.limit
        },
        details={
            "result_count": len(results.get("results", [])),
            "execution_time_ms": results.get("execution_time_ms")
        }
    )
    db.add(audit_log)
    # Will be committed by get_db dependency
    
    return SearchResponse(**results)


class RerankRequest(BaseModel):
    query: str
    results: List[Dict[str, Any]]


@router.post("/rerank")
async def rerank_results(
    rerank_request: RerankRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Re-rank search results for better relevance
    """
    
    try:
        reranked = await search_provider.rerank(
            query=rerank_request.query,
            results=rerank_request.results
        )
        
        return {
            "query": rerank_request.query,
            "results": reranked,
            "total_results": len(reranked)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reranking failed: {str(e)}"
        )


@router.get("/documents/{document_id}/similar")
async def find_similar_documents(
    document_id: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Find documents similar to a given document
    """
    
    try:
        similar = await search_provider.get_similar_documents(
            document_id=document_id,
            limit=limit,
            context={
                "user": {
                    "id": current_user.id,
                    "role": getattr(current_user.role, "value", current_user.role)
                }
            }
        )
        
        # Log similarity search
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            action="search",
            resource_type="similarity",
            resource_id=document_id,
            details={"similar_count": len(similar)}
        )
        db.add(audit_log)
        # Will be committed by get_db dependency
        
        return {
            "source_document": document_id,
            "similar_documents": similar,
            "total": len(similar)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Similarity search failed: {str(e)}"
        )


class KeywordExtractionRequest(BaseModel):
    text: str
    max_keywords: int = 10


@router.post("/extract-keywords")
async def extract_keywords(
    request: KeywordExtractionRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Extract keywords from text
    """
    
    try:
        keywords = await search_provider.extract_keywords(
            text=request.text,
            max_keywords=request.max_keywords
        )
        
        return {
            "keywords": keywords,
            "count": len(keywords)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Keyword extraction failed: {str(e)}"
        )