"""Tests for the Tool Registry System."""

import pytest
from jsonschema import ValidationError
from vbagent.orchestrator.tools import ToolDefinition, ToolRegistry


# Sample tool functions for testing
def sample_tool_sync(arg1: str, arg2: int) -> str:
    """Sample synchronous tool."""
    return f"{arg1}_{arg2}"


async def sample_tool_async(arg1: str) -> str:
    """Sample asynchronous tool."""
    return f"async_{arg1}"


def tool_with_error(arg1: str) -> str:
    """Tool that raises an error."""
    raise ValueError(f"Error with {arg1}")


class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""
    
    def test_tool_definition_creation(self):
        """Test creating a ToolDefinition."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            function=sample_tool_sync
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.parameters == {"type": "object", "properties": {}}
        assert tool.function == sample_tool_sync


class TestToolRegistry:
    """Tests for ToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test that registry initializes empty."""
        registry = ToolRegistry()
        assert len(registry.tools) == 0
        assert registry.list_tools() == []
    
    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        
        registry.register(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "integer"}
                },
                "required": ["arg1", "arg2"]
            },
            function=sample_tool_sync
        )
        
        assert "test_tool" in registry.tools
        assert len(registry.list_tools()) == 1
        
        tool = registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
    
    def test_register_duplicate_tool_raises_error(self):
        """Test that registering duplicate tool raises ValueError."""
        registry = ToolRegistry()
        
        registry.register(
            name="test_tool",
            description="First tool",
            parameters={"type": "object"},
            function=sample_tool_sync
        )
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                name="test_tool",
                description="Duplicate tool",
                parameters={"type": "object"},
                function=sample_tool_sync
            )
    
    def test_get_tool_definitions_openai(self):
        """Test OpenAI format conversion."""
        registry = ToolRegistry()
        
        registry.register(
            name="tool1",
            description="First tool",
            parameters={
                "type": "object",
                "properties": {"arg": {"type": "string"}}
            },
            function=sample_tool_sync
        )
        
        registry.register(
            name="tool2",
            description="Second tool",
            parameters={
                "type": "object",
                "properties": {"num": {"type": "integer"}}
            },
            function=sample_tool_async
        )
        
        openai_format = registry.get_tool_definitions_openai()
        
        assert len(openai_format) == 2
        assert openai_format[0]["type"] == "function"
        assert openai_format[0]["function"]["name"] == "tool1"
        assert openai_format[0]["function"]["description"] == "First tool"
        assert "properties" in openai_format[0]["function"]["parameters"]
        
        assert openai_format[1]["type"] == "function"
        assert openai_format[1]["function"]["name"] == "tool2"
    
    def test_get_tool_definitions_anthropic(self):
        """Test Anthropic format conversion."""
        registry = ToolRegistry()
        
        registry.register(
            name="tool1",
            description="First tool",
            parameters={
                "type": "object",
                "properties": {"arg": {"type": "string"}}
            },
            function=sample_tool_sync
        )
        
        anthropic_format = registry.get_tool_definitions_anthropic()
        
        assert len(anthropic_format) == 1
        assert anthropic_format[0]["name"] == "tool1"
        assert anthropic_format[0]["description"] == "First tool"
        assert "input_schema" in anthropic_format[0]
        assert anthropic_format[0]["input_schema"]["type"] == "object"
    
    def test_get_tool_definitions_mcp(self):
        """Test MCP format conversion."""
        registry = ToolRegistry()
        
        registry.register(
            name="tool1",
            description="First tool",
            parameters={
                "type": "object",
                "properties": {"arg": {"type": "string"}}
            },
            function=sample_tool_sync
        )
        
        mcp_format = registry.get_tool_definitions_mcp()
        
        assert len(mcp_format) == 1
        assert mcp_format[0]["name"] == "tool1"
        assert mcp_format[0]["description"] == "First tool"
        assert "inputSchema" in mcp_format[0]
        assert mcp_format[0]["inputSchema"]["type"] == "object"
    
    def test_get_tool_definitions_google(self):
        """Test Google format conversion."""
        registry = ToolRegistry()
        
        registry.register(
            name="tool1",
            description="First tool",
            parameters={
                "type": "object",
                "properties": {"arg": {"type": "string"}}
            },
            function=sample_tool_sync
        )
        
        google_format = registry.get_tool_definitions_google()
        
        assert len(google_format) == 1
        assert google_format[0]["name"] == "tool1"
        assert google_format[0]["description"] == "First tool"
        assert "parameters" in google_format[0]
    
    def test_get_tool_definitions_xai(self):
        """Test xAI format conversion (should match OpenAI)."""
        registry = ToolRegistry()
        
        registry.register(
            name="tool1",
            description="First tool",
            parameters={
                "type": "object",
                "properties": {"arg": {"type": "string"}}
            },
            function=sample_tool_sync
        )
        
        xai_format = registry.get_tool_definitions_xai()
        openai_format = registry.get_tool_definitions_openai()
        
        assert xai_format == openai_format
    
    @pytest.mark.asyncio
    async def test_execute_sync_tool(self):
        """Test executing a synchronous tool."""
        registry = ToolRegistry()
        
        registry.register(
            name="test_tool",
            description="Test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "integer"}
                },
                "required": ["arg1", "arg2"]
            },
            function=sample_tool_sync
        )
        
        result = await registry.execute(
            "test_tool",
            {"arg1": "hello", "arg2": 42}
        )
        
        assert result == "hello_42"
    
    @pytest.mark.asyncio
    async def test_execute_async_tool(self):
        """Test executing an asynchronous tool."""
        registry = ToolRegistry()
        
        registry.register(
            name="async_tool",
            description="Async test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                },
                "required": ["arg1"]
            },
            function=sample_tool_async
        )
        
        result = await registry.execute(
            "async_tool",
            {"arg1": "test"}
        )
        
        assert result == "async_test"
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises_error(self):
        """Test that executing unknown tool raises ValueError."""
        registry = ToolRegistry()
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await registry.execute("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_arguments(self):
        """Test that invalid arguments raise ValidationError."""
        registry = ToolRegistry()
        
        registry.register(
            name="test_tool",
            description="Test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "integer"}
                },
                "required": ["arg1", "arg2"]
            },
            function=sample_tool_sync
        )
        
        # Missing required argument
        with pytest.raises(ValidationError):
            await registry.execute("test_tool", {"arg1": "hello"})
        
        # Wrong type
        with pytest.raises(ValidationError):
            await registry.execute(
                "test_tool",
                {"arg1": "hello", "arg2": "not_an_int"}
            )
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self):
        """Test that tool errors are properly wrapped."""
        registry = ToolRegistry()
        
        registry.register(
            name="error_tool",
            description="Tool that errors",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                },
                "required": ["arg1"]
            },
            function=tool_with_error
        )
        
        with pytest.raises(Exception, match="Error executing tool 'error_tool'"):
            await registry.execute("error_tool", {"arg1": "test"})
    
    def test_validate_arguments_valid(self):
        """Test argument validation with valid arguments."""
        registry = ToolRegistry()
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        # Should not raise
        registry._validate_arguments(schema, {"name": "John", "age": 30})
        registry._validate_arguments(schema, {"name": "Jane"})
    
    def test_validate_arguments_invalid(self):
        """Test argument validation with invalid arguments."""
        registry = ToolRegistry()
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        # Missing required field
        with pytest.raises(ValidationError):
            registry._validate_arguments(schema, {"age": 30})
        
        # Wrong type
        with pytest.raises(ValidationError):
            registry._validate_arguments(schema, {"name": 123})
    
    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = ToolRegistry()
        
        registry.register(
            name="test_tool",
            description="Test",
            parameters={"type": "object"},
            function=sample_tool_sync
        )
        
        tool = registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        
        # Non-existent tool
        assert registry.get_tool("nonexistent") is None
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        
        registry.register(
            name="test_tool",
            description="Test",
            parameters={"type": "object"},
            function=sample_tool_sync
        )
        
        assert "test_tool" in registry.tools
        
        # Unregister existing tool
        result = registry.unregister("test_tool")
        assert result is True
        assert "test_tool" not in registry.tools
        
        # Unregister non-existent tool
        result = registry.unregister("nonexistent")
        assert result is False
    
    def test_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()
        
        assert registry.list_tools() == []
        
        registry.register(
            name="tool1",
            description="First",
            parameters={"type": "object"},
            function=sample_tool_sync
        )
        
        registry.register(
            name="tool2",
            description="Second",
            parameters={"type": "object"},
            function=sample_tool_async
        )
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools
