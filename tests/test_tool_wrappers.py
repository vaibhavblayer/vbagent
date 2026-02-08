"""Tests for tool wrapper functions."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from vbagent.orchestrator.tools import ToolRegistry
from vbagent.orchestrator.tool_wrappers import (
    scan_tool,
    classify_tool,
    tikz_tool,
    variant_tool,
    convert_tool,
    register_core_tools
)


class TestScanTool:
    """Tests for scan_tool wrapper."""
    
    @patch('vbagent.agents.classifier.classify')
    @patch('vbagent.agents.scanner.scan')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_scan_tool_basic(self, mock_path, mock_scan, mock_classify):
        """Test basic scan tool execution."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_classification = Mock()
        mock_classification.question_type = "mcq_sc"
        mock_classify.return_value = mock_classification
        
        mock_result = Mock()
        mock_result.latex = "\\item Test question"
        mock_result.has_diagram = False
        mock_result.raw_diagram_description = None
        mock_scan.return_value = mock_result
        
        # Execute
        result = scan_tool(image="test.png")
        
        # Verify
        assert result["latex"] == "\\item Test question"
        assert result["has_diagram"] is False
        assert result["question_type"] == "mcq_sc"
        assert result["output_path"] is None
        mock_classify.assert_called_once_with("test.png")
        mock_scan.assert_called_once()
    
    @patch('vbagent.agents.scanner.scan_with_type')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_scan_tool_with_question_type(self, mock_path, mock_scan_with_type):
        """Test scan tool with explicit question type."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_result = Mock()
        mock_result.latex = "\\item Test question"
        mock_result.has_diagram = False
        mock_result.raw_diagram_description = None
        mock_scan_with_type.return_value = mock_result
        
        # Execute
        result = scan_tool(image="test.png", question_type="subjective")
        
        # Verify
        assert result["question_type"] == "subjective"
        mock_scan_with_type.assert_called_once_with("test.png", "subjective")
    
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_scan_tool_file_not_found(self, mock_path):
        """Test scan tool with non-existent file."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            scan_tool(image="nonexistent.png")


class TestClassifyTool:
    """Tests for classify_tool wrapper."""
    
    @patch('vbagent.agents.classifier.classify')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_classify_tool_basic(self, mock_path, mock_classify):
        """Test basic classify tool execution."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_result = Mock()
        mock_result.question_type = "mcq_sc"
        mock_result.difficulty = "medium"
        mock_result.topic = "mechanics"
        mock_result.subtopic = "kinematics"
        mock_result.has_diagram = True
        mock_result.diagram_type = "free_body"
        mock_result.num_options = 4
        mock_result.requires_calculus = False
        mock_result.confidence = 0.95
        mock_result.key_concepts = ["velocity", "acceleration"]
        mock_classify.return_value = mock_result
        
        # Execute
        result = classify_tool(image="test.png")
        
        # Verify
        assert result["question_type"] == "mcq_sc"
        assert result["difficulty"] == "medium"
        assert result["topic"] == "mechanics"
        assert result["has_diagram"] is True
        assert result["confidence"] == 0.95
        assert result["output_path"] is None
        mock_classify.assert_called_once_with("test.png")
    
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_classify_tool_file_not_found(self, mock_path):
        """Test classify tool with non-existent file."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            classify_tool(image="nonexistent.png")


class TestTikzTool:
    """Tests for tikz_tool wrapper."""
    
    @patch('vbagent.agents.tikz.generate_tikz')
    def test_tikz_tool_with_description(self, mock_generate):
        """Test tikz tool with description."""
        mock_generate.return_value = "\\begin{tikzpicture}...\\end{tikzpicture}"
        
        result = tikz_tool(description="Free body diagram")
        
        assert "tikz_code" in result
        assert result["tikz_code"] == "\\begin{tikzpicture}...\\end{tikzpicture}"
        assert result["output_path"] is None
        mock_generate.assert_called_once()
    
    def test_tikz_tool_no_input(self):
        """Test tikz tool with no input raises error."""
        with pytest.raises(ValueError, match="At least one of"):
            tikz_tool()
    
    @patch('vbagent.agents.tikz.generate_tikz')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_tikz_tool_with_image(self, mock_path, mock_generate):
        """Test tikz tool with image."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_generate.return_value = "\\begin{tikzpicture}...\\end{tikzpicture}"
        
        result = tikz_tool(image="diagram.png", description="Test")
        
        assert "tikz_code" in result
        mock_generate.assert_called_once()


class TestVariantTool:
    """Tests for variant_tool wrapper."""
    
    @patch('vbagent.agents.variant.generate_variant')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_variant_tool_basic(self, mock_path, mock_gen_variant):
        """Test basic variant tool execution."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.read_text.return_value = "\\item Original problem"
        mock_path.return_value = mock_path_instance
        
        mock_gen_variant.return_value = "\\item Variant problem"
        
        result = variant_tool(
            variant_type="numerical",
            tex="problem.tex",
            count=1
        )
        
        assert result["variant_type"] == "numerical"
        assert result["count"] == 1
        assert len(result["variants"]) == 1
        assert result["variants"][0] == "\\item Variant problem"
        assert result["output_path"] is None
    
    def test_variant_tool_invalid_type(self):
        """Test variant tool with invalid type."""
        with pytest.raises(ValueError, match="Invalid variant_type"):
            variant_tool(variant_type="invalid", tex="problem.tex")
    
    def test_variant_tool_no_input(self):
        """Test variant tool with no input raises error."""
        with pytest.raises(ValueError, match="Either 'image' or 'tex'"):
            variant_tool(variant_type="numerical")
    
    @patch('vbagent.agents.variant.generate_variant')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_variant_tool_multiple_variants(self, mock_path, mock_gen_variant):
        """Test generating multiple variants."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.read_text.return_value = "\\item Original"
        mock_path.return_value = mock_path_instance
        
        mock_gen_variant.side_effect = ["\\item Variant 1", "\\item Variant 2", "\\item Variant 3"]
        
        result = variant_tool(
            variant_type="context",
            tex="problem.tex",
            count=3
        )
        
        assert result["count"] == 3
        assert len(result["variants"]) == 3
        assert mock_gen_variant.call_count == 3


class TestConvertTool:
    """Tests for convert_tool wrapper."""
    
    @patch('vbagent.agents.converter.convert_format')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_convert_tool_basic(self, mock_path, mock_convert):
        """Test basic convert tool execution."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.read_text.return_value = "\\item MCQ question"
        mock_path.return_value = mock_path_instance
        
        mock_convert.return_value = "\\item Subjective question"
        
        result = convert_tool(
            target_format="subjective",
            tex="mcq.tex",
            source_format="mcq_sc"
        )
        
        assert result["converted_latex"] == "\\item Subjective question"
        assert result["source_format"] == "mcq_sc"
        assert result["target_format"] == "subjective"
        assert result["output_path"] is None
        mock_convert.assert_called_once()
    
    def test_convert_tool_invalid_target_format(self):
        """Test convert tool with invalid target format."""
        with pytest.raises(ValueError, match="Invalid target_format"):
            convert_tool(target_format="invalid", tex="problem.tex")
    
    def test_convert_tool_no_input(self):
        """Test convert tool with no input raises error."""
        with pytest.raises(ValueError, match="Either 'image' or 'tex'"):
            convert_tool(target_format="subjective")
    
    @patch('vbagent.agents.converter.convert_format')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_convert_tool_auto_detect_format(self, mock_path, mock_convert):
        """Test convert tool with auto-detected source format."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.read_text.return_value = "\\begin{tasks}(4)\\task Option A\\end{tasks}"
        mock_path.return_value = mock_path_instance
        
        mock_convert.return_value = "\\item Converted"
        
        result = convert_tool(
            target_format="subjective",
            tex="mcq.tex"
        )
        
        # Should auto-detect as mcq_sc
        assert result["source_format"] == "mcq_sc"


class TestRegisterCoreTools:
    """Tests for register_core_tools function."""
    
    def test_register_core_tools(self):
        """Test that all core tools are registered."""
        registry = ToolRegistry()
        
        register_core_tools(registry)
        
        # Verify all tools are registered
        tools = registry.list_tools()
        assert "scan" in tools
        assert "classify" in tools
        assert "tikz" in tools
        assert "variant" in tools
        assert "convert" in tools
        assert "extract_subitems" in tools
        assert "parse_latex_project" in tools
        assert "extract_from_directory" in tools
        assert "index_metadata" in tools
        assert "query_metadata" in tools
        assert "create_dpp" in tools
        
        # Verify tool definitions have required fields
        scan_tool_def = registry.get_tool("scan")
        assert scan_tool_def is not None
        assert scan_tool_def.name == "scan"
        assert scan_tool_def.description != ""
        assert "properties" in scan_tool_def.parameters
        assert "image" in scan_tool_def.parameters["properties"]
        
        classify_tool_def = registry.get_tool("classify")
        assert classify_tool_def is not None
        assert "image" in classify_tool_def.parameters["properties"]
        
        tikz_tool_def = registry.get_tool("tikz")
        assert tikz_tool_def is not None
        assert "description" in tikz_tool_def.parameters["properties"]
        
        variant_tool_def = registry.get_tool("variant")
        assert variant_tool_def is not None
        assert "variant_type" in variant_tool_def.parameters["properties"]
        
        convert_tool_def = registry.get_tool("convert")
        assert convert_tool_def is not None
        assert "target_format" in convert_tool_def.parameters["properties"]
        
        # Verify LaTeX extraction tools
        extract_subitems_def = registry.get_tool("extract_subitems")
        assert extract_subitems_def is not None
        assert "tex" in extract_subitems_def.parameters["properties"] or "content" in extract_subitems_def.parameters["properties"]
        
        parse_project_def = registry.get_tool("parse_latex_project")
        assert parse_project_def is not None
        assert "main_tex" in parse_project_def.parameters["properties"]
        
        extract_dir_def = registry.get_tool("extract_from_directory")
        assert extract_dir_def is not None
        assert "directory" in extract_dir_def.parameters["properties"]
    
    def test_tool_schemas_valid(self):
        """Test that all tool schemas are valid JSON schemas."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        for tool_name in registry.list_tools():
            tool = registry.get_tool(tool_name)
            assert tool is not None
            
            # Check schema structure
            schema = tool.parameters
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            
            # Verify properties are defined
            assert len(schema["properties"]) > 0
    
    def test_tool_format_conversions(self):
        """Test that tools can be converted to different provider formats."""
        registry = ToolRegistry()
        register_core_tools(registry)
        
        # Get the actual count of registered tools
        tool_count = len(registry.list_tools())
        
        # Test OpenAI format
        openai_tools = registry.get_tool_definitions_openai()
        assert len(openai_tools) == tool_count
        assert all("type" in tool for tool in openai_tools)
        assert all(tool["type"] == "function" for tool in openai_tools)
        
        # Test Anthropic format
        anthropic_tools = registry.get_tool_definitions_anthropic()
        assert len(anthropic_tools) == tool_count
        assert all("name" in tool for tool in anthropic_tools)
        assert all("input_schema" in tool for tool in anthropic_tools)
        
        # Test MCP format
        mcp_tools = registry.get_tool_definitions_mcp()
        assert len(mcp_tools) == tool_count
        assert all("name" in tool for tool in mcp_tools)
        assert all("inputSchema" in tool for tool in mcp_tools)
        
        # Test Google format
        google_tools = registry.get_tool_definitions_google()
        assert len(google_tools) == tool_count
        assert all("name" in tool for tool in google_tools)
        assert all("parameters" in tool for tool in google_tools)
