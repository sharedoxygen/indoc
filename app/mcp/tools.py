"""
Tool Registry for MCP Server
"""
from typing import Dict, Any, List, Optional, Callable


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register(
        self,
        name: str,
        description: str,
        provider: Any,
        method: str,
        parameters: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0"
    ):
        """
        Register a new tool
        
        Args:
            name: Unique tool name
            description: Tool description
            provider: Provider instance that implements the tool
            method: Method name on the provider
            parameters: Parameter schema
            version: Tool version
        """
        self.tools[name] = {
            "name": name,
            "description": description,
            "provider": provider,
            "method": method,
            "parameters": parameters or {},
            "version": version
        }
    
    def unregister(self, name: str):
        """Unregister a tool"""
        if name in self.tools:
            del self.tools[name]
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools"""
        return list(self.tools.values())
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool parameter schema"""
        tool = self.get_tool(name)
        if tool:
            return {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
                "version": tool["version"]
            }
        return None