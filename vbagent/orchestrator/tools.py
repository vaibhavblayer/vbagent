"""Tool Registry System for the Conversational Orchestrator.

This module provides a unified system for registering and managing tools that can be
exposed to LLM APIs (OpenAI, Anthropic, Google, xAI) and MCP servers.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional
import jsonschema
from jsonschema import ValidationError


@dataclass
class ToolDefinition:
    """Definition of a tool with its schema and execution function.
    
    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of what the tool does
        parameters: JSON Schema defining the tool's parameters
        function: Callable that executes the tool
    """
    name: str
    description: str
    parameters: dict
    function: Callable


class ToolRegistry:
    """Central registry for all vbagent tools.
    
    Provides unified interface for tool registration, format conversion,
    argument validation, and execution. Supports multiple LLM providers
    (OpenAI, Anthropic, Google, xAI) and MCP protocol.
    """
    
    def __init__(self):
        """Initialize an empty tool registry."""
        self.tools: dict[str, ToolDefinition] = {}
    
    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        function: Callable
    ) -> None:
        """Register a tool in the registry.
        
        Args:
            name: Unique identifier for the tool
            description: Human-readable description
            parameters: JSON Schema for tool parameters
            function: Callable that executes the tool
            
        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered")
        
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            function=function
        )
    
    def get_tool_definitions_openai(self) -> list[dict]:
        """Get tool definitions in OpenAI function calling format.
        
        Returns:
            List of tool definitions formatted for OpenAI API
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self.tools.values()
        ]
    
    def get_tool_definitions_anthropic(self) -> list[dict]:
        """Get tool definitions in Anthropic tool use format.
        
        Returns:
            List of tool definitions formatted for Anthropic API
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    def get_tool_definitions_mcp(self) -> list[dict]:
        """Get tool definitions in MCP (Model Context Protocol) format.
        
        Returns:
            List of tool definitions formatted for MCP
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    def get_tool_definitions_google(self) -> list[dict]:
        """Get tool definitions in Google Gemini format.
        
        Returns:
            List of tool definitions formatted for Google API
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    def get_tool_definitions_xai(self) -> list[dict]:
        """Get tool definitions in xAI Grok format.
        
        xAI uses OpenAI-compatible format.
        
        Returns:
            List of tool definitions formatted for xAI API
        """
        return self.get_tool_definitions_openai()
    
    async def execute(
        self,
        tool_name: str,
        arguments: dict
    ) -> Any:
        """Execute a tool with validation and error handling.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            Result from tool execution
            
        Raises:
            ValueError: If tool is not found
            ValidationError: If arguments don't match schema
            Exception: Any exception raised by the tool function
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        
        # Validate arguments against schema
        try:
            self._validate_arguments(tool.parameters, arguments)
        except ValidationError as e:
            raise ValidationError(
                f"Invalid arguments for tool '{tool_name}': {e.message}"
            )
        
        # Execute function with error handling
        try:
            # Check if function is async
            if hasattr(tool.function, '__call__'):
                import inspect
                if inspect.iscoroutinefunction(tool.function):
                    result = await tool.function(**arguments)
                else:
                    result = tool.function(**arguments)
            else:
                result = tool.function(**arguments)
            return result
        except Exception as e:
            # Re-raise with context about which tool failed
            raise Exception(f"Error executing tool '{tool_name}': {str(e)}") from e
    
    def _validate_arguments(
        self,
        schema: dict,
        arguments: dict
    ) -> None:
        """Validate arguments against JSON Schema.
        
        Args:
            schema: JSON Schema to validate against
            arguments: Arguments to validate
            
        Raises:
            ValidationError: If validation fails
        """
        jsonschema.validate(instance=arguments, schema=schema)
    
    def list_tools(self) -> list[str]:
        """Get list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.
        
        Args:
            name: Name of the tool
            
        Returns:
            ToolDefinition if found, None otherwise
        """
        return self.tools.get(name)
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool from the registry.
        
        Args:
            name: Name of the tool to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self.tools:
            del self.tools[name]
            return True
        return False
