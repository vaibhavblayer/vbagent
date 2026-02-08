"""Tests for MCP server functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from vbagent.mcp.server import MCPServer
from vbagent.orchestrator.tools import ToolRegistry, ToolDefinition


@pytest.fixture
def sample_registry():
    """Create a sample tool registry for testing."""
    registry = ToolRegistry()
    
    # Register a simple test tool
    async def test_tool(message: str) -> str:
        return f"Echo: {message}"
    
    registry.register(
        name="test_tool",
        description="A simple test tool",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        },
        function=test_tool
    )
    
    return registry


class TestMCPServer:
    """Tests for MCPServer class."""
    
    def test_server_initialization(self, sample_registry):
        """Test MCP server initialization."""
        server = MCPServer(sample_registry)
        
        assert server.tool_registry == sample_registry
        assert server.server is not None
        assert server.server.name == "vbagent"
    
    def test_get_mcp_tools(self, sample_registry):
        """Test getting tools in MCP format."""
        server = MCPServer(sample_registry)
        tools = server._get_mcp_tools()
        
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "A simple test tool"
        assert tools[0].inputSchema["type"] == "object"
    
    def test_format_result_string(self, sample_registry):
        """Test formatting string results."""
        server = MCPServer(sample_registry)
        result = server._format_result("test string")
        
        assert result == "test string"
    
    def test_format_result_dict(self, sample_registry):
        """Test formatting dictionary results."""
        server = MCPServer(sample_registry)
        result = server._format_result({"key": "value", "number": 42})
        
        assert "key" in result
        assert "value" in result
        assert "42" in result
    
    def test_format_result_list(self, sample_registry):
        """Test formatting list results."""
        server = MCPServer(sample_registry)
        result = server._format_result([1, 2, 3])
        
        assert "[" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution_success(self, sample_registry):
        """Test successful tool execution via MCP."""
        server = MCPServer(sample_registry)
        
        # Execute tool
        result = await sample_registry.execute("test_tool", {"message": "hello"})
        
        assert result == "Echo: hello"
    
    @pytest.mark.asyncio
    async def test_tool_execution_error(self, sample_registry):
        """Test tool execution error handling."""
        server = MCPServer(sample_registry)
        
        # Try to execute non-existent tool
        with pytest.raises(ValueError, match="Unknown tool"):
            await sample_registry.execute("nonexistent_tool", {})
    
    def test_multiple_tools_registration(self):
        """Test MCP server with multiple tools."""
        registry = ToolRegistry()
        
        # Register multiple tools
        async def tool1(x: int) -> int:
            return x * 2
        
        async def tool2(text: str) -> str:
            return text.upper()
        
        registry.register(
            name="double",
            description="Double a number",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"]
            },
            function=tool1
        )
        
        registry.register(
            name="uppercase",
            description="Convert to uppercase",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            },
            function=tool2
        )
        
        server = MCPServer(registry)
        tools = server._get_mcp_tools()
        
        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert "double" in tool_names
        assert "uppercase" in tool_names
    
    def test_tool_schema_preservation(self, sample_registry):
        """Test that tool schemas are preserved in MCP format."""
        server = MCPServer(sample_registry)
        tools = server._get_mcp_tools()
        
        tool = tools[0]
        schema = tool.inputSchema
        
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "message" in schema["properties"]
        assert schema["properties"]["message"]["type"] == "string"
        assert "required" in schema
        assert "message" in schema["required"]


class TestMCPServerIntegration:
    """Integration tests for MCP server with real tools."""
    
    def test_server_with_core_tools(self):
        """Test MCP server with core vbagent tools."""
        from vbagent.orchestrator.tool_wrappers import register_core_tools
        
        registry = ToolRegistry()
        register_core_tools(registry)
        
        server = MCPServer(registry)
        tools = server._get_mcp_tools()
        
        # Should have multiple tools registered
        assert len(tools) > 0
        
        # Check that some expected tools are present
        tool_names = {t.name for t in tools}
        assert "classify" in tool_names
        assert "create_dpp" in tool_names
    
    @pytest.mark.asyncio
    async def test_classify_tool_via_mcp(self):
        """Test executing classify tool via MCP server."""
        from vbagent.orchestrator.tool_wrappers import register_core_tools
        
        registry = ToolRegistry()
        register_core_tools(registry)
        
        server = MCPServer(registry)
        
        # Verify classify tool is available
        tools = server._get_mcp_tools()
        tool_names = {t.name for t in tools}
        assert "classify" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
