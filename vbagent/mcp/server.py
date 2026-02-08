"""MCP Server implementation for vbagent.

Exposes vbagent tools via the Model Context Protocol for integration
with external agents like Kiro, Cursor, and Claude Desktop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from vbagent.orchestrator.tools import ToolRegistry


logger = logging.getLogger(__name__)


class MCPServer:
    """MCP protocol server for vbagent tools.
    
    Exposes all registered vbagent tools via the Model Context Protocol,
    allowing external agents to discover and execute tools.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """Initialize MCP server.
        
        Args:
            tool_registry: ToolRegistry instance with registered tools
        """
        self.tool_registry = tool_registry
        self.server = Server("vbagent")
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return self._get_mcp_tools()
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Execute a tool and return results."""
            try:
                result = await self.tool_registry.execute(name, arguments)
                return [TextContent(
                    type="text",
                    text=self._format_result(result)
                )]
            except Exception as e:
                logger.error(f"Tool execution failed: {name}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    def _get_mcp_tools(self) -> list[Tool]:
        """Get all tools in MCP format.
        
        Returns:
            List of Tool objects for MCP protocol
        """
        mcp_tools = []
        
        for tool_def in self.tool_registry.tools.values():
            mcp_tool = Tool(
                name=tool_def.name,
                description=tool_def.description,
                inputSchema=tool_def.parameters
            )
            mcp_tools.append(mcp_tool)
        
        return mcp_tools
    
    def _format_result(self, result: Any) -> str:
        """Format tool execution result for MCP response.
        
        Args:
            result: Tool execution result
            
        Returns:
            Formatted string representation
        """
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            import json
            return json.dumps(result, indent=2)
        elif isinstance(result, list):
            import json
            return json.dumps(result, indent=2)
        else:
            return str(result)
    
    async def run(self) -> None:
        """Run the MCP server with stdio transport.
        
        This starts the server and listens for MCP protocol messages
        on stdin/stdout.
        """
        logger.info("Starting vbagent MCP server")
        logger.info(f"Exposing {len(self.tool_registry.tools)} tools")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
