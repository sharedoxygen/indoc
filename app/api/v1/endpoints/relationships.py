"""
Document Relationship API endpoints
Analyze how documents relate to each other through citations and content
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.document_relationships import DocumentRelationshipAnalyzer

router = APIRouter()


class DocumentRelationshipResponse(BaseModel):
    """Response for document relationship analysis"""
    document_id: str
    filename: str
    analysis_timestamp: str
    relationships: List[Dict[str, Any]]
    citations_found: int
    similar_documents: int
    related_documents: int
    total_relationships: int


class DocumentNetworkResponse(BaseModel):
    """Response for document network analysis"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    statistics: Dict[str, Any]


class CitationPathResponse(BaseModel):
    """Response for citation path analysis"""
    source_document_id: str
    target_document_id: str
    path_found: bool
    path: Optional[List[str]] = None
    description: Optional[str] = None


@router.get("/analyze/{document_id}", response_model=DocumentRelationshipResponse)
async def analyze_document_relationships(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze relationships for a specific document"""
    
    try:
        analyzer = DocumentRelationshipAnalyzer(db)
        analysis = await analyzer.analyze_document_relationships(document_id)
        
        return DocumentRelationshipResponse(**analysis)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze document relationships: {str(e)}"
        )


@router.post("/network", response_model=DocumentNetworkResponse)
async def get_document_network(
    document_ids: List[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the relationship network for a set of documents"""
    
    if not document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one document ID is required"
        )
    
    if len(document_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot analyze more than 50 documents at once"
        )
    
    try:
        analyzer = DocumentRelationshipAnalyzer(db)
        network = await analyzer.get_document_network(document_ids)
        
        return DocumentNetworkResponse(**network)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate document network: {str(e)}"
        )


@router.get("/citation-path")
async def find_citation_path(
    source_document_id: UUID = Query(..., description="Source document ID"),
    target_document_id: UUID = Query(..., description="Target document ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find citation path between two documents"""
    
    if source_document_id == target_document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target documents cannot be the same"
        )
    
    try:
        analyzer = DocumentRelationshipAnalyzer(db)
        path = await analyzer.find_citation_path(source_document_id, target_document_id)
        
        response = CitationPathResponse(
            source_document_id=str(source_document_id),
            target_document_id=str(target_document_id),
            path_found=path is not None
        )
        
        if path:
            response.path = [str(doc_id) for doc_id in path]
            if len(path) == 2:
                response.description = "Direct citation found"
            else:
                response.description = f"Citation path found through {len(path) - 2} intermediate document(s)"
        else:
            response.description = "No citation path found between documents"
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find citation path: {str(e)}"
        )


@router.get("/related/{document_id}")
async def get_related_documents(
    document_id: UUID,
    relationship_types: Optional[List[str]] = Query(None, description="Filter by relationship types"),
    min_strength: float = Query(0.5, ge=0.0, le=1.0, description="Minimum relationship strength"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of related documents"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get documents related to the specified document"""
    
    try:
        analyzer = DocumentRelationshipAnalyzer(db)
        analysis = await analyzer.analyze_document_relationships(document_id)
        
        # Filter relationships
        filtered_relationships = []
        for rel in analysis["relationships"]:
            # Filter by relationship type
            if relationship_types and rel["relationship_type"] not in relationship_types:
                continue
            
            # Filter by minimum strength
            if rel["strength"] < min_strength:
                continue
            
            filtered_relationships.append(rel)
        
        # Sort by strength and limit
        filtered_relationships.sort(key=lambda x: x["strength"], reverse=True)
        filtered_relationships = filtered_relationships[:limit]
        
        return {
            "document_id": str(document_id),
            "related_documents": filtered_relationships,
            "total_found": len(filtered_relationships),
            "filters_applied": {
                "relationship_types": relationship_types,
                "min_strength": min_strength,
                "limit": limit
            }
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get related documents: {str(e)}"
        )


@router.get("/citations/{document_id}")
async def get_document_citations(
    document_id: UUID,
    citation_types: Optional[List[str]] = Query(None, description="Filter by citation types"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum citation confidence"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get citations found within a document"""
    
    try:
        analyzer = DocumentRelationshipAnalyzer(db)
        analysis = await analyzer.analyze_document_relationships(document_id)
        
        # Extract citation information from relationships
        citations = []
        for rel in analysis["relationships"]:
            if rel["relationship_type"] == "cites":
                citation_info = {
                    "target_document_id": rel["document_b_id"],
                    "confidence": rel["strength"],
                    "description": rel["description"],
                    "evidence": rel["evidence"]
                }
                
                # Apply filters
                if min_confidence and citation_info["confidence"] < min_confidence:
                    continue
                
                citations.append(citation_info)
        
        return {
            "document_id": str(document_id),
            "citations": citations,
            "total_citations": len(citations),
            "analysis_timestamp": analysis["analysis_timestamp"]
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document citations: {str(e)}"
        )


@router.get("/types")
async def get_relationship_types():
    """Get available relationship types and their descriptions"""
    
    relationship_types = {
        "cites": {
            "name": "Cites",
            "description": "Document directly references or cites another document",
            "examples": ["References to other reports", "Bibliography citations", "Page references"]
        },
        "similar_to": {
            "name": "Similar To",
            "description": "Documents with similar content or topics",
            "examples": ["Related reports", "Similar research", "Comparable analyses"]
        },
        "related_to": {
            "name": "Related To", 
            "description": "Documents that share common topics or themes",
            "examples": ["Same project documents", "Related topics", "Common themes"]
        },
        "part_of": {
            "name": "Part Of",
            "description": "Document is part of a larger document set or series",
            "examples": ["Chapters of a book", "Sections of a report", "Series installments"]
        },
        "contradicts": {
            "name": "Contradicts",
            "description": "Documents that present conflicting information",
            "examples": ["Opposing viewpoints", "Conflicting data", "Different conclusions"]
        }
    }
    
    citation_types = {
        "reference": {
            "name": "Reference",
            "description": "Direct reference to another document or source",
            "confidence_range": "0.7 - 0.9"
        },
        "quote": {
            "name": "Quote",
            "description": "Direct quotation from another source",
            "confidence_range": "0.8 - 0.95"
        },
        "temporal": {
            "name": "Temporal",
            "description": "Reference based on dates or time periods",
            "confidence_range": "0.5 - 0.7"
        }
    }
    
    return {
        "relationship_types": relationship_types,
        "citation_types": citation_types,
        "strength_levels": {
            "high": {"min": 0.8, "description": "Strong relationship with high confidence"},
            "medium": {"min": 0.5, "description": "Moderate relationship with reasonable confidence"},
            "low": {"min": 0.2, "description": "Weak relationship with low confidence"}
        }
    }
