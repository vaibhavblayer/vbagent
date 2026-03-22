"""Integration tests for tool wrappers with the registry."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from vbagent.orchestrator import ToolRegistry, register_core_tools


class TestToolIntegration:
    """Integration tests for tools registered in the registry."""
    
    def test_all_tools_registered(self):
        """Test that all core tools are properly registered."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        expected_tools = ["scan", "classify", "tikz", "variant", "convert"]
        registered_tools = registry.list_tools()
        
        for tool in expected_tools:
            assert tool in registered_tools, f"Tool '{tool}' not registered"
    
    def test_tool_schemas_have_required_fields(self):
        """Test that all tool schemas have required fields."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        for tool_name in registry.list_tools():
            tool = registry.get_tool(tool_name)
            
            # Check basic structure
            assert tool.name == tool_name
            assert tool.description != ""
            assert isinstance(tool.parameters, dict)
            assert "type" in tool.parameters
            assert "properties" in tool.parameters
            
            # Check that properties is not empty
            assert len(tool.parameters["properties"]) > 0
    
    def test_openai_format_conversion(self):
        """Test that tools can be converted to OpenAI format."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        openai_tools = registry.get_tool_definitions_openai()
        
        # Check that we have all registered tools
        assert len(openai_tools) == len(registry.list_tools())
        
        for tool in openai_tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
    
    def test_anthropic_format_conversion(self):
        """Test that tools can be converted to Anthropic format."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        anthropic_tools = registry.get_tool_definitions_anthropic()
        
        # Check that we have all registered tools
        assert len(anthropic_tools) == len(registry.list_tools())
        
        for tool in anthropic_tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "type" in tool["input_schema"]
            assert "properties" in tool["input_schema"]
    
    def test_mcp_format_conversion(self):
        """Test that tools can be converted to MCP format."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        mcp_tools = registry.get_tool_definitions_mcp()
        
        # Check that we have all registered tools
        assert len(mcp_tools) == len(registry.list_tools())
        
        for tool in mcp_tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]
            assert "properties" in tool["inputSchema"]
    
    @pytest.mark.asyncio
    @patch('vbagent.agents.classifier.classify')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    async def test_execute_classify_tool_through_registry(self, mock_path, mock_classify):
        """Test executing classify tool through the registry."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_result = Mock()
        mock_result.subject = "physics"
        mock_result.question_type = "mcq_sc"
        mock_result.has_diagram = False
        mock_result.confidence = 0.95
        mock_result.model_dump_json = Mock(return_value='{}')
        mock_classify.return_value = mock_result
        
        # Execute through registry
        registry = ToolRegistry()
        register_core_tools(registry)
        
        result = await registry.execute(
            "classify",
            {"image": "test.png"}
        )
        
        # Verify result
        assert result["question_type"] == "mcq_sc"
        assert result["subject"] == "physics"
        assert result["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_arguments(self):
        """Test that invalid arguments are caught by validation."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        # Missing required argument
        with pytest.raises(Exception):  # ValidationError
            await registry.execute("scan", {})
        
        # Invalid argument type
        with pytest.raises(Exception):  # ValidationError
            await registry.execute("scan", {"image": 123})
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test that executing unknown tool raises error."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await registry.execute("nonexistent_tool", {})
    
    def test_tool_descriptions_are_informative(self):
        """Test that tool descriptions provide useful information."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        for tool_name in registry.list_tools():
            tool = registry.get_tool(tool_name)
            
            # Description should be at least 20 characters
            assert len(tool.description) >= 20, f"Tool '{tool_name}' has too short description"
            
            # Description should mention what the tool does
            description_lower = tool.description.lower()
            assert any(word in description_lower for word in ["extract", "generate", "classify", "convert", "create", "parse", "index", "query", "export"]), \
                f"Tool '{tool_name}' description doesn't clearly state what it does"
    
    def test_required_parameters_are_marked(self):
        """Test that required parameters are properly marked in schemas."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        # Scan tool should require 'image'
        scan_tool = registry.get_tool("scan")
        assert "required" in scan_tool.parameters
        assert "image" in scan_tool.parameters["required"]
        
        # Classify tool should require 'image'
        classify_tool = registry.get_tool("classify")
        assert "required" in classify_tool.parameters
        assert "image" in classify_tool.parameters["required"]
        
        # Variant tool should require 'variant_type'
        variant_tool = registry.get_tool("variant")
        assert "required" in variant_tool.parameters
        assert "variant_type" in variant_tool.parameters["required"]
        
        # Convert tool should require 'target_format'
        convert_tool = registry.get_tool("convert")
        assert "required" in convert_tool.parameters
        assert "target_format" in convert_tool.parameters["required"]
    
    def test_enum_parameters_have_valid_values(self):
        """Test that enum parameters define valid values."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        # Variant tool's variant_type should have enum values
        variant_tool = registry.get_tool("variant")
        variant_type_prop = variant_tool.parameters["properties"]["variant_type"]
        assert "enum" in variant_type_prop
        assert len(variant_type_prop["enum"]) > 0
        assert "numerical" in variant_type_prop["enum"]
        
        # Convert tool's target_format should have enum values
        convert_tool = registry.get_tool("convert")
        target_format_prop = convert_tool.parameters["properties"]["target_format"]
        assert "enum" in target_format_prop
        assert len(target_format_prop["enum"]) > 0
        assert "subjective" in target_format_prop["enum"]
