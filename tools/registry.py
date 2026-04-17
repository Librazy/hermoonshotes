"""Tool registry for Hermes Agent.

This module provides the registry for tool registration and discovery.
Tools register themselves by calling registry.register() at module load time.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for tools.
    
    Tools register themselves by calling register() at module load time.
    The registry supports:
    - Tool schemas (for LLM tool definitions)
    - Handler functions (for executing tools)
    - Check functions (for determining tool availability)
    - Environment variable requirements
    """
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}
        self._check_fns: Dict[str, Callable] = {}
    
    def register(
        self,
        name: str,
        toolset: str,
        schema: Dict[str, Any],
        handler: Callable,
        check_fn: Optional[Callable[[], bool]] = None,
        requires_env: Optional[List[str]] = None,
        is_async: bool = False
    ):
        """Register a tool.
        
        Args:
            name: Tool name (must be unique)
            toolset: Toolset category (e.g., 'web', 'utility')
            schema: JSON schema for tool parameters
            handler: Function to execute when tool is called
            check_fn: Function to check if tool is available
            requires_env: List of required environment variables
            is_async: Whether the handler is async
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' is already registered, overwriting")
        
        self._tools[name] = {
            "name": name,
            "toolset": toolset,
            "schema": schema,
            "requires_env": requires_env or [],
            "is_async": is_async
        }
        self._handlers[name] = handler
        self._check_fns[name] = check_fn or (lambda: True)
        
        logger.debug(f"Registered tool: {name} (toolset: {toolset})")
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool definition or None if not found
        """
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler by name.
        
        Args:
            name: Tool name
            
        Returns:
            Handler function or None if not found
        """
        return self._handlers.get(name)
    
    def is_available(self, name: str) -> bool:
        """Check if a tool is available.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool is available
        """
        if name not in self._check_fns:
            return False
        try:
            return self._check_fns[name]()
        except Exception as e:
            logger.error(f"Error checking availability for '{name}': {e}")
            return False
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def list_available_tools(self) -> List[str]:
        """List all available tool names.
        
        Returns:
            List of available tool names
        """
        return [name for name in self._tools.keys() if self.is_available(name)]
    
    def get_tool_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool schema for LLM.
        
        Args:
            name: Tool name
            
        Returns:
            Tool schema or None if not found
        """
        tool = self._tools.get(name)
        if not tool:
            return None
        return tool.get("schema")
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all available tools.
        
        Returns:
            List of tool schemas
        """
        schemas = []
        for name in self.list_available_tools():
            schema = self.get_tool_schema(name)
            if schema:
                schemas.append(schema)
        return schemas


# Global registry instance
registry = ToolRegistry()
