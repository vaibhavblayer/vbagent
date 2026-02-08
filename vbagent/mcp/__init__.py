"""MCP (Model Context Protocol) server for vbagent.

This module provides an MCP server that exposes vbagent tools to external
agents like Kiro, Cursor, and Claude Desktop.
"""

from vbagent.mcp.server import MCPServer

__all__ = ["MCPServer"]
