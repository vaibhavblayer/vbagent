"""MCP (Model Context Protocol) server for vbagent.

This module provides an MCP server that exposes vbagent tools to external
agents like Kiro, Cursor, and Claude Desktop.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vbagent.mcp.server import MCPServer

__all__ = ["MCPServer"]


def __getattr__(name: str) -> Any:
    """Keep lightweight chat policy imports from initializing the MCP server."""
    if name == "MCPServer":
        from vbagent.mcp.server import MCPServer

        return MCPServer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
