"""
MCP Server - Central orchestrator for tool calls
"""
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
import json
import asyncio
from datetime import datetime

from app.mcp.tools import ToolRegistry
from app.mcp.providers.search_provider import SearchProvider
from app.mcp.providers.database_provider import DatabaseProvider
from app.mcp.providers.file_provider import FileProvider
from app.core.config import settings
from app.services.llm_service import LLMService


class MCPServer:
    """
    Model Context Protocol Server
    Orchestrates tool calls between LLM and various providers
    """
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.llm_service = LLMService()
        
        # Initialize providers
        self.search_provider = SearchProvider()
        self.database_provider = DatabaseProvider()
        self.file_provider = FileProvider()
        
        # Register tools
        self._register_tools()
        
        # Metrics
        self.call_metrics = []
    
    def _register_tools(self):
        """Register all available tools with the registry"""
        
        # Search tools
        self.tool_registry.register(
            name="search_documents",
            description="Search for documents using hybrid search (keyword + semantic)",
            provider=self.search_provider,
            method="search",
            parameters={
                "query": {"type": "string", "required": True},
                "filters": {"type": "object", "required": False},
                "limit": {"type": "integer", "required": False, "default": 10}
            }
        )
        
        self.tool_registry.register(
            name="rerank_results",
            description="Re-rank search results for better relevance",
            provider=self.search_provider,
            method="rerank",
            parameters={
                "query": {"type": "string", "required": True},
                "results": {"type": "array", "required": True}
            }
        )
        
        # Database tools
        self.tool_registry.register(
            name="get_document_metadata",
            description="Retrieve metadata for a document",
            provider=self.database_provider,
            method="get_metadata",
            parameters={
                "document_id": {"type": "string", "required": True}
            }
        )
        
        self.tool_registry.register(
            name="update_document_metadata",
            description="Update metadata for a document",
            provider=self.database_provider,
            method="update_metadata",
            parameters={
                "document_id": {"type": "string", "required": True},
                "metadata": {"type": "object", "required": True}
            }
        )
        
        # File tools
        self.tool_registry.register(
            name="read_document",
            description="Read the content of a document",
            provider=self.file_provider,
            method="read_file",
            parameters={
                "document_id": {"type": "string", "required": True}
            }
        )
        
        self.tool_registry.register(
            name="extract_text",
            description="Extract text from a document",
            provider=self.file_provider,
            method="extract_text",
            parameters={
                "document_id": {"type": "string", "required": True},
                "page_range": {"type": "array", "required": False}
            }
        )
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with given parameters
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            context: Optional context (user info, session, etc.)
        
        Returns:
            Tool execution result
        """
        start_time = datetime.utcnow()
        
        try:
            # Get tool from registry
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            
            # Validate parameters
            validated_params = self._validate_parameters(tool, parameters)
            
            # Execute tool
            provider = tool["provider"]
            method = getattr(provider, tool["method"])
            
            if asyncio.iscoroutinefunction(method):
                result = await method(**validated_params, context=context)
            else:
                result = method(**validated_params, context=context)
            
            # Record metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._record_metrics(tool_name, execution_time, "success")
            
            return {
                "tool": tool_name,
                "status": "success",
                "result": result,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._record_metrics(tool_name, execution_time, "error")
            
            return {
                "tool": tool_name,
                "status": "error",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def execute_chain(
        self,
        tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a chain of tools sequentially
        
        Args:
            tools: List of tool configurations [{name, parameters}, ...]
            context: Optional context
        
        Returns:
            List of tool execution results
        """
        results = []
        chain_context = context or {}
        
        for tool_config in tools:
            # Execute tool
            result = await self.execute_tool(
                tool_config["name"],
                tool_config.get("parameters", {}),
                chain_context
            )
            
            results.append(result)
            
            # Update context with result for next tool
            if result["status"] == "success":
                chain_context["previous_result"] = result["result"]
            else:
                # Stop chain on error
                break
        
        return results
    
    async def generate_with_tools(
        self,
        prompt: str,
        available_tools: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate LLM response with tool access
        
        Args:
            prompt: User prompt
            available_tools: List of tool names available to LLM
            context: Optional context
        
        Returns:
            LLM response with tool calls
        """
        # Get available tools
        if available_tools:
            tools = [self.tool_registry.get_tool(name) for name in available_tools]
            tools = [t for t in tools if t]  # Filter None values
        else:
            tools = self.tool_registry.list_tools()
        
        # Format tools for LLM
        tool_descriptions = self._format_tools_for_llm(tools)
        
        # Generate response with tools
        response = await self.llm_service.generate_with_tools(
            prompt=prompt,
            tools=tool_descriptions,
            context=context
        )
        
        # Execute any tool calls from LLM
        if "tool_calls" in response:
            tool_results = []
            for call in response["tool_calls"]:
                result = await self.execute_tool(
                    call["name"],
                    call["parameters"],
                    context
                )
                tool_results.append(result)
            
            response["tool_results"] = tool_results
        
        return response
    
    def _validate_parameters(
        self,
        tool: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize tool parameters"""
        validated = {}
        tool_params = tool.get("parameters", {})
        
        for param_name, param_config in tool_params.items():
            if param_config.get("required", False) and param_name not in parameters:
                raise ValueError(f"Required parameter '{param_name}' missing")
            
            if param_name in parameters:
                # Type validation could be added here
                validated[param_name] = parameters[param_name]
            elif "default" in param_config:
                validated[param_name] = param_config["default"]
        
        return validated
    
    def _format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format tool descriptions for LLM consumption"""
        formatted = []
        
        for tool in tools:
            formatted.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {})
            })
        
        return formatted
    
    def _record_metrics(self, tool_name: str, execution_time: float, status: str):
        """Record tool execution metrics"""
        self.call_metrics.append({
            "tool": tool_name,
            "timestamp": datetime.utcnow().isoformat(),
            "execution_time": execution_time,
            "status": status
        })
        
        # Keep only last 1000 metrics in memory
        if len(self.call_metrics) > 1000:
            self.call_metrics = self.call_metrics[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tool execution metrics"""
        if not self.call_metrics:
            return {"total_calls": 0, "tools": {}}
        
        # Aggregate metrics by tool
        tool_metrics = {}
        for metric in self.call_metrics:
            tool = metric["tool"]
            if tool not in tool_metrics:
                tool_metrics[tool] = {
                    "calls": 0,
                    "errors": 0,
                    "total_time": 0,
                    "avg_time": 0
                }
            
            tool_metrics[tool]["calls"] += 1
            if metric["status"] == "error":
                tool_metrics[tool]["errors"] += 1
            tool_metrics[tool]["total_time"] += metric["execution_time"]
        
        # Calculate averages
        for tool in tool_metrics:
            calls = tool_metrics[tool]["calls"]
            if calls > 0:
                tool_metrics[tool]["avg_time"] = tool_metrics[tool]["total_time"] / calls
        
        return {
            "total_calls": len(self.call_metrics),
            "tools": tool_metrics
        }