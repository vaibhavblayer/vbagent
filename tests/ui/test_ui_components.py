"""Tests for UI components module."""

import pytest
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich.syntax import Syntax
from rich.text import Text

from vbagent.ui import (
    create_table,
    create_result_table,
    create_category_table,
    add_category_row,
    create_panel,
    create_progress,
    create_code_block,
    create_status_line,
    create_badge,
    create_section_header,
    COLORS,
    TABLE_STYLES,
    VBAGENT_THEME,
    STATUS,
    CATEGORY_COLORS,
)


class TestStyles:
    """Tests for styles module."""

    def test_colors_defined(self):
        """Test that all required colors are defined."""
        required = ["primary", "secondary", "success", "warning", "error", "info", "muted", "header", "accent", "surface"]
        for color in required:
            assert color in COLORS
            assert COLORS[color].startswith("#")

    def test_table_styles_defined(self):
        """Test that all table styles are defined."""
        for style in ["simple", "minimal", "markdown"]:
            assert style in TABLE_STYLES
            assert "border_style" in TABLE_STYLES[style]
            assert "header_style" in TABLE_STYLES[style]
            assert "box" in TABLE_STYLES[style]

    def test_vbagent_theme_defined(self):
        """Test that VBAgent theme is defined."""
        assert VBAGENT_THEME is not None
        assert hasattr(VBAGENT_THEME, "styles")

    def test_status_indicators(self):
        """Test that status indicators are defined."""
        for key in ["success", "error", "warning", "info", "pending", "running", "skip"]:
            assert key in STATUS

    def test_category_colors(self):
        """Test that category colors are defined."""
        for key in ["classification", "content_generation", "diagram", "variants", "quality"]:
            assert key in CATEGORY_COLORS
            assert CATEGORY_COLORS[key].startswith("#")


class TestTables:
    """Tests for tables module."""

    def test_create_table_default(self):
        table = create_table()
        assert isinstance(table, Table)

    def test_create_table_with_title(self):
        table = create_table(title="Test Table")
        assert isinstance(table, Table)
        assert table.title == "Test Table"

    def test_create_table_styles(self):
        for style in ["simple", "minimal", "markdown"]:
            table = create_table(style=style)
            assert isinstance(table, Table)

    def test_create_table_with_caption(self):
        table = create_table(title="T", caption="some caption")
        assert isinstance(table, Table)

    def test_create_result_table(self):
        data = {"key1": "value1", "key2": "value2"}
        table = create_result_table("Results", data)
        assert isinstance(table, Table)
        assert table.title == "Results"

    def test_create_result_table_empty(self):
        table = create_result_table("Empty", {})
        assert isinstance(table, Table)

    def test_create_result_table_formats_values(self):
        data = {"none_val": None, "bool_val": True, "float_val": 3.14159, "list_val": [1, 2, 3]}
        table = create_result_table("Formatted", data)
        assert isinstance(table, Table)

    def test_create_category_table(self):
        table = create_category_table("Config", ["Category", "Agent", "Model"])
        assert isinstance(table, Table)
        assert table.title == "Config"

    def test_add_category_row(self):
        table = create_category_table("T", ["Category", "Agent", "Model"])
        add_category_row(table, "classification", ["scanner", "gpt-5"])
        add_category_row(table, "quality", ["reviewer", "gpt-5"], is_header=True)
        assert table.row_count == 2


class TestComponents:
    """Tests for components module."""

    def test_create_panel_default(self):
        panel = create_panel("Test content")
        assert isinstance(panel, Panel)

    def test_create_panel_with_title(self):
        panel = create_panel("Test content", title="Test Panel")
        assert isinstance(panel, Panel)
        assert panel.title == "Test Panel"

    def test_create_panel_with_subtitle(self):
        panel = create_panel("content", subtitle="v1.0")
        assert isinstance(panel, Panel)

    def test_create_progress(self):
        progress = create_progress()
        assert isinstance(progress, Progress)

    def test_create_progress_no_time(self):
        progress = create_progress(show_time=False)
        assert isinstance(progress, Progress)

    def test_create_code_block(self):
        code = "def hello():\n    print('Hello')"
        syntax = create_code_block(code, language="python")
        assert isinstance(syntax, Syntax)

    def test_create_code_block_with_line_numbers(self):
        syntax = create_code_block("print('test')", line_numbers=True)
        assert isinstance(syntax, Syntax)

    def test_create_status_line(self):
        line = create_status_line("Model", "gpt-5.2")
        assert isinstance(line, Text)

    def test_create_badge(self):
        for variant in ["success", "error", "warning", "info"]:
            badge = create_badge("OK", variant)
            assert isinstance(badge, str)

    def test_create_section_header(self):
        header = create_section_header("Classification")
        assert isinstance(header, Text)


class TestLogging:
    """Tests for logging module."""

    def test_log_functions_exist(self):
        from vbagent.ui.logging import log_agent_input, log_agent_output, log_agent_error
        assert callable(log_agent_input)
        assert callable(log_agent_output)
        assert callable(log_agent_error)

    def test_log_agent_input_no_debug(self, monkeypatch):
        from vbagent.ui.logging import log_agent_input
        from vbagent.config import VBAgentConfig
        import vbagent.config
        mock_config = VBAgentConfig(debug=False)
        monkeypatch.setattr(vbagent.config, "get_config", lambda: mock_config)
        log_agent_input("test_agent", "test input")

    def test_log_agent_output_no_debug(self, monkeypatch):
        from vbagent.ui.logging import log_agent_output
        from vbagent.config import VBAgentConfig
        import vbagent.config
        mock_config = VBAgentConfig(debug=False)
        monkeypatch.setattr(vbagent.config, "get_config", lambda: mock_config)
        log_agent_output("test_agent", "test output")

    def test_log_agent_error_no_debug(self, monkeypatch):
        from vbagent.ui.logging import log_agent_error
        from vbagent.config import VBAgentConfig
        import vbagent.config
        mock_config = VBAgentConfig(debug=False)
        monkeypatch.setattr(vbagent.config, "get_config", lambda: mock_config)
        log_agent_error("test_agent", ValueError("test error"))


class TestBase64Sanitization:
    """Tests for base64 sanitization in logging."""

    def test_sanitize_data_uri(self):
        from vbagent.ui.logging import _sanitize_base64
        data = "data:image/png;base64," + "A" * 500
        result = _sanitize_base64(data)
        assert "base64" in result.lower()
        assert "image/png" in result
        assert "KB" in result
        assert "A" * 100 not in result

    def test_sanitize_raw_base64(self):
        from vbagent.ui.logging import _sanitize_base64
        data = "prefix " + "A" * 300 + " suffix"
        result = _sanitize_base64(data)
        assert "base64 data" in result.lower()
        assert "A" * 200 not in result

    def test_sanitize_short_string_unchanged(self):
        from vbagent.ui.logging import _sanitize_base64
        data = "Hello world"
        assert _sanitize_base64(data) == data

    def test_sanitize_dict(self):
        from vbagent.ui.logging import _sanitize_dict
        data = {
            "text": "hello",
            "image_url": "data:image/jpeg;base64," + "B" * 500,
            "nested": {"deep": "data:image/png;base64," + "C" * 300},
        }
        result = _sanitize_dict(data)
        assert result["text"] == "hello"
        assert "KB" in result["image_url"]
        assert "B" * 100 not in result["image_url"]
        assert "KB" in result["nested"]["deep"]

    def test_extract_image_meta(self):
        from vbagent.ui.logging import _extract_image_meta
        url = "data:image/png;base64," + "A" * 1000
        meta = _extract_image_meta(url)
        assert "image/png" in meta
        assert "KB" in meta

    def test_format_message_list_with_image(self):
        from vbagent.ui.logging import _format_message_list
        messages = [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": "data:image/png;base64," + "X" * 500},
                {"type": "input_text", "text": "Classify this"},
            ]
        }]
        result = _format_message_list(messages)
        rendered = str(result)
        assert "X" * 100 not in rendered
        assert "Classify this" in rendered


class TestTruncation:
    """Tests for text truncation."""

    def test_truncate_short(self):
        from vbagent.ui.logging import _truncate
        assert _truncate("hello", 100) == "hello"

    def test_truncate_long(self):
        from vbagent.ui.logging import _truncate
        result = _truncate("a" * 1000, 50)
        assert len(result) < 200
        assert "chars total" in result

    def test_format_pydantic_model(self):
        from vbagent.ui.logging import _format_pydantic
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str = "test"
            score: float = 0.95
            tags: list[str] = ["a", "b"]

        result = _format_pydantic(TestModel())
        # Now returns Syntax (JSON) instead of Table
        from rich.syntax import Syntax
        assert isinstance(result, Syntax)
