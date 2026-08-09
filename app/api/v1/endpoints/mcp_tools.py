"""
MCP Tools API endpoints
Expose Model Context Protocol tools for document analysis
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.mcp.client import MCPClient

router = APIRouter()


class ToolCallRequest(BaseModel):
    """Request to call an MCP tool"""
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Arguments for the tool")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the tool")


class ToolCallResponse(BaseModel):
    """Response from MCP tool execution"""
    tool: str
    result: Dict[str, Any]
    status: str
    execution_time: Optional[str] = None
    error: Optional[str] = None


class DocumentInsightsRequest(BaseModel):
    """Request for document insights analysis"""
    document_ids: List[str] = Field(..., description="List of document IDs to analyze")
    analysis_type: str = Field("comprehensive", description="Type of analysis: basic, comprehensive, focused")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")


class DocumentComparisonRequest(BaseModel):
    """Request for document comparison"""
    document_ids: List[str] = Field(..., description="List of document IDs to compare (minimum 2)")
    comparison_criteria: List[str] = Field(["content", "themes", "dates"], description="Criteria for comparison")
    
    class Config:
        schema_extra = {
            "example": {
                "document_ids": ["uuid-1", "uuid-2"],
                "comparison_criteria": ["content", "themes", "metadata"]
            }
        }


class DocumentSummaryRequest(BaseModel):
    """Request for document summary generation"""
    document_ids: List[str] = Field(..., description="List of document IDs to summarize")
    summary_type: str = Field("executive", description="Type of summary: executive, detailed, focused")
    length: str = Field("medium", description="Summary length: short, medium, long")
    focus_areas: Optional[List[str]] = Field(None, description="Specific topics to focus on")


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection"""
    document_ids: List[str] = Field(..., description="List of document IDs to analyze")
    anomaly_types: List[str] = Field(["compliance", "content", "metadata"], description="Types of anomalies to detect")


@router.get("/tools", response_model=List[Dict[str, Any]])
async def get_available_tools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available MCP tools and their descriptions"""
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        tools = await mcp_client.get_available_tools()
        return tools
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available tools: {str(e)}"
        )


@router.get("/tools/examples")
async def get_tool_examples(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage examples for all MCP tools"""
    
    try:
        mcp_client = MCPClient(db)
        examples = mcp_client.get_tool_usage_examples()
        return examples
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool examples: {str(e)}"
        )


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_mcp_tool(
    request: ToolCallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Call any MCP tool with provided arguments"""
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        result = await mcp_client.call_tool(request.tool_name, request.arguments)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return ToolCallResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.post("/insights")
async def analyze_document_insights(
    request: DocumentInsightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze documents for key insights, themes, and patterns"""
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        result = await mcp_client.call_tool("document_insights", {
            "document_ids": request.document_ids,
            "analysis_type": request.analysis_type,
            "context": {"focus_areas": request.focus_areas}
        })
        
        if "error" in result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
        
        return result["result"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document insights analysis failed: {str(e)}"
        )


@router.post("/compare")
async def compare_documents(
    request: DocumentComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare multiple documents across various criteria"""
    
    if len(request.document_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 documents required for comparison"
        )
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        result = await mcp_client.call_tool("compare_documents", {
            "document_ids": request.document_ids,
            "comparison_criteria": request.comparison_criteria
        })
        
        if "error" in result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
        
        return result["result"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document comparison failed: {str(e)}"
        )


@router.post("/summarize")
async def generate_document_summary(
    request: DocumentSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate intelligent summaries of documents"""
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        result = await mcp_client.call_tool("document_summary", {
            "document_ids": request.document_ids,
            "summary_type": request.summary_type,
            "length": request.length,
            "focus_areas": request.focus_areas
        })
        
        if "error" in result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
        
        return result["result"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document summary generation failed: {str(e)}"
        )


@router.post("/detect-anomalies")
async def detect_document_anomalies(
    request: AnomalyDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect anomalies and potential issues in documents"""
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        result = await mcp_client.call_tool("detect_anomalies", {
            "document_ids": request.document_ids,
            "anomaly_types": request.anomaly_types
        })
        
        if "error" in result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
        
        return result["result"]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        )


@router.post("/auto-analyze")
async def auto_analyze_conversation_documents(
    document_ids: List[str],
    user_message: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Automatically analyze documents based on user's message intent"""
    
    try:
        mcp_client = MCPClient(db)
        await mcp_client.connect()
        
        # Analyze user message to suggest appropriate tools
        message_analysis = await mcp_client.send_message(user_message, {"document_ids": document_ids})
        
        auto_results = {
            "user_message": user_message,
            "document_ids": document_ids,
            "suggested_tools": message_analysis["suggested_tools"],
            "analysis_results": {}
        }
        
        # Execute suggested tools automatically
        for tool_name in message_analysis["suggested_tools"][:2]:  # Limit to 2 tools to avoid overload
            try:
                if tool_name == "document_insights":
                    result = await mcp_client.call_tool(tool_name, {"document_ids": document_ids})
                elif tool_name == "compare_documents" and len(document_ids) >= 2:
                    result = await mcp_client.call_tool(tool_name, {"document_ids": document_ids})
                elif tool_name == "document_summary":
                    result = await mcp_client.call_tool(tool_name, {"document_ids": document_ids})
                else:
                    continue
                
                if result.get("status") == "success":
                    auto_results["analysis_results"][tool_name] = result["result"]
                    
            except Exception as tool_error:
                logger.warning(f"Auto-analysis tool {tool_name} failed: {tool_error}")
        
        return auto_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-analysis failed: {str(e)}"
        )


@router.get("/health")
async def mcp_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check MCP system health and available providers"""
    
    try:
        mcp_client = MCPClient(db)
        connected = await mcp_client.connect()
        
        if not connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP system not available"
            )
        
        tools = await mcp_client.get_available_tools()
        
        return {
            "status": "healthy",
            "mcp_connected": connected,
            "available_tools": len(tools),
            "tool_names": [tool["name"] for tool in tools],
            "providers": list(mcp_client.providers.keys()),
            "timestamp": "2024-09-07T01:30:00Z"  # Would use actual timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MCP health check failed: {str(e)}"
        )
