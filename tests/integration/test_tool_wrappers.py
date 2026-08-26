"""Tests for tool wrapper functions."""

import json
import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock
from vbagent.orchestrator.tools import ToolRegistry
from vbagent.orchestrator.tool_wrappers import (
    scan_tool,
    classify_tool,
    tikz_tool,
    variant_tool,
    convert_tool,
    generate_problem_tool,
    register_core_tools
)


class TestScanTool:
    """Tests for scan_tool wrapper."""
    
    @patch('vbagent.agents.classification.question_classifier.classify_primary_image')
    @patch('vbagent.agents.content_generation.scanner.scan')
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
    
    @patch('vbagent.agents.content_generation.scanner.scan_with_type')
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
    
    @patch('vbagent.agents.classification.question_classifier.classify_primary_image')
    @patch('vbagent.orchestrator.tool_wrappers.Path')
    def test_classify_tool_basic(self, mock_path, mock_classify):
        """Test basic classify tool execution."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_result = Mock()
        mock_result.subject = "physics"
        mock_result.question_type = "mcq_sc"
        mock_result.has_diagram = True
        mock_result.confidence = 0.95
        mock_result.model_dump_json = Mock(return_value='{}')
        mock_classify.return_value = mock_result
        
        # Execute
        result = classify_tool(image="test.png")
        
        # Verify
        assert result["question_type"] == "mcq_sc"
        assert result["subject"] == "physics"
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
    
    @patch('vbagent.agents.diagram.tikz.generate_tikz')
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
    
    @patch('vbagent.agents.diagram.tikz.generate_tikz')
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

    @staticmethod
    def _execution(candidates):
        return SimpleNamespace(
            plan=SimpleNamespace(plan_id="variant-run"),
            stats={"status": "completed", "accepted": len(candidates)},
            accepted_candidates=candidates,
            run_dir=Path("/tmp/authoring/runs/variant-run"),
            database_path=Path("/tmp/authoring/.vbagent_authoring.db"),
        )

    @patch('vbagent.authoring.api.execute_variants')
    def test_variant_tool_basic(self, execute_variants):
        execute_variants.return_value = self._execution(
            [{"final_latex": "\\item Variant problem"}]
        )

        result = variant_tool(
            parent_spec_id="parent-spec",
            variant_type="numerical",
            count=1
        )

        assert result["variant_type"] == "numerical"
        assert result["count"] == 1
        assert result["variants"][0] == "\\item Variant problem"
        assert result["parent_spec_id"] == "parent-spec"
        assert execute_variants.call_args.args[:2] == ("parent-spec", "agentic/authoring")
        assert execute_variants.call_args.kwargs["variant_families"] == {"numerical": 1.0}
    
    def test_variant_tool_invalid_type(self):
        """Test variant tool with invalid type."""
        with pytest.raises(ValueError, match="Invalid variant_type"):
            variant_tool(parent_spec_id="parent-spec", variant_type="invalid")

    @patch('vbagent.authoring.api.execute_variants')
    def test_variant_tool_multiple_variants(self, execute_variants):
        """Test generating multiple variants."""
        execute_variants.return_value = self._execution(
            [{"final_latex": f"\\item Variant {index}"} for index in range(1, 4)]
        )

        result = variant_tool(
            parent_spec_id="parent-spec",
            variant_type="context",
            count=3
        )

        assert result["count"] == 3
        assert len(result["variants"]) == 3
        assert execute_variants.call_args.kwargs["count"] == 3


class TestGenerateProblemTool:
    @staticmethod
    def _execution():
        candidate = {
            "problem_latex": r"\item Problem",
            "independent_solution_latex": r"\begin{solution}Work\end{solution}",
            "final_latex": r"\item Problem\begin{solution}Work\end{solution}",
            "idea_latex": "",
            "diagram_description": "",
        }
        request = SimpleNamespace(exam="jee_main", subject="physics")
        plan = SimpleNamespace(
            plan_id="author-run",
            request=request,
            catalog_version="2026.1",
            catalog_source_sha256="catalog-sha",
            allowed_question_types=(SimpleNamespace(value="mcq_sc"),),
            exam_pattern_description="Four-option single-correct MCQ.",
            exam_pattern_source_url="https://example.test/pattern.pdf",
            distributions={"topic": {"projectile_motion": 1}},
        )
        return SimpleNamespace(
            plan=plan,
            stats={"status": "completed", "accepted": 1},
            items=(
                {
                    "status": "accepted",
                    "last_candidate_json": json.dumps(candidate),
                    "artifact_dir": "/tmp/authoring/items/spec/attempts/attempt-1",
                },
            ),
            run_dir=Path("/tmp/authoring/runs/author-run"),
            database_path=Path("/tmp/authoring/.vbagent_authoring.db"),
        )

    @patch("vbagent.authoring.api.execute_authoring")
    def test_routes_exact_syllabus_identity_to_authoring(self, execute_authoring):
        execute_authoring.return_value = self._execution()

        result = generate_problem_tool(
            idea="projectile on an incline",
            topic="projectile_motion",
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            question_type="mcq_sc",
            with_diagram=False,
        )

        request = execute_authoring.call_args.args[0]
        assert request.exam == "jee_main"
        assert request.subject == "physics"
        assert request.chapter == "kinematics"
        assert request.topics == ["projectile_motion"]
        assert request.question_types == {"mcq_sc": 1.0}
        assert request.diagram_ratio == 0.0
        assert result["run_id"] == "author-run"
        assert result["final_latex"].startswith(r"\item Problem")

    def test_rejects_pipeline_bypass(self):
        with pytest.raises(ValueError, match="cannot be bypassed"):
            generate_problem_tool(
                idea="idea",
                topic="projectile_motion",
                exam="jee_main",
                subject="physics",
                chapter="kinematics",
                run_pipeline=False,
            )

    @patch("vbagent.authoring.api.execute_authoring")
    def test_defaults_to_exam_compatible_single_choice(self, execute_authoring):
        execute_authoring.return_value = self._execution()

        generate_problem_tool(
            idea="projectile on an incline",
            topic="projectile_motion",
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            with_diagram=False,
        )

        request = execute_authoring.call_args.args[0]
        assert request.question_types == {"mcq_sc": 1.0}

    @patch("vbagent.authoring.api.execute_authoring")
    def test_rejected_authoring_candidate_is_not_returned_as_usable(self, execute_authoring):
        execution = self._execution()
        execution.stats = {
            "status": "completed",
            "accepted": 0,
            "needs_review": 0,
            "rejected": 1,
            "failed": 0,
        }
        execution.items[0]["status"] = "rejected"
        execute_authoring.return_value = execution

        result = generate_problem_tool(
            idea="projectile on an incline",
            topic="projectile_motion",
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            with_diagram=False,
        )

        assert result["complete"] is False
        assert result["candidates"] == []
        assert "final_latex" not in result


class TestConvertTool:
    """Tests for convert_tool wrapper."""
    
    @patch('vbagent.agents.content_generation.converter.convert_format')
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
    
    @patch('vbagent.agents.content_generation.converter.convert_format')
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
        assert "parent_spec_id" in variant_tool_def.parameters["required"]

        generate_tool_def = registry.get_tool("generate_problem")
        assert generate_tool_def is not None
        assert {"idea", "topic", "exam", "subject", "chapter"}.issubset(
            generate_tool_def.parameters["required"]
        )
        
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
