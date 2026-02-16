"""Tests for UI components module."""

import pytest
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich.syntax import Syntax

from vbagent.ui import (
    create_table,
    create_result_table,
    create_panel,
    create_progress,
    create_code_block,
    COLORS,
    TABLE_STYLES,
    VBAGENT_THEME,
)


class TestStyles:
    """Tests for styles module."""
    
    def test_colors_defined(self):
        """Test that all required colors are defined."""
        required_colors = ["primary", "success", "warning", "error", "info", "muted", "header"]
        for color in required_colors:
            assert color in COLORS
            assert COLORS[color].startswith("#")
    
    def test_table_styles_defined(self):
        """Test that all table styles are defined."""
        required_styles = ["modern", "minimal", "clean"]
        for style in required_styles:
            assert style in TABLE_STYLES
            assert "border_style" in TABLE_STYLES[style]
            assert "header_style" in TABLE_STYLES[style]
            assert "box" in TABLE_STYLES[style]
    
    def test_vbagent_theme_defined(self):
        """Test that VBAgent theme is defined."""
        assert VBAGENT_THEME is not None
        assert hasattr(VBAGENT_THEME, "styles")


class TestTables:
    """Tests for tables module."""
    
    def test_create_table_default(self):
        """Test creating a table with default settings."""
        table = create_table()
        assert isinstance(table, Table)
    
    def test_create_table_with_title(self):
        """Test creating a table with a title."""
        table = create_table(title="Test Table")
        assert isinstance(table, Table)
        assert table.title == "Test Table"
    
    def test_create_table_styles(self):
        """Test creating tables with different styles."""
        for style in ["modern", "minimal", "clean"]:
            table = create_table(style=style)
            assert isinstance(table, Table)
    
    def test_create_result_table(self):
        """Test creating a result table."""
        data = {"key1": "value1", "key2": "value2"}
        table = create_result_table("Results", data)
        assert isinstance(table, Table)
        assert table.title == "Results"
    
    def test_create_result_table_empty(self):
        """Test creating a result table with empty data."""
        table = create_result_table("Empty", {})
        assert isinstance(table, Table)


class TestComponents:
    """Tests for components module."""
    
    def test_create_panel_default(self):
        """Test creating a panel with default settings."""
        panel = create_panel("Test content")
        assert isinstance(panel, Panel)
    
    def test_create_panel_with_title(self):
        """Test creating a panel with a title."""
        panel = create_panel("Test content", title="Test Panel")
        assert isinstance(panel, Panel)
        assert panel.title == "Test Panel"
    
    def test_create_progress(self):
        """Test creating a progress bar."""
        progress = create_progress()
        assert isinstance(progress, Progress)
    
    def test_create_code_block(self):
        """Test creating a code block."""
        code = "def hello():\n    print('Hello')"
        syntax = create_code_block(code, language="python")
        assert isinstance(syntax, Syntax)
    
    def test_create_code_block_with_line_numbers(self):
        """Test creating a code block with line numbers."""
        code = "print('test')"
        syntax = create_code_block(code, line_numbers=True)
        assert isinstance(syntax, Syntax)


class TestLogging:
    """Tests for logging module."""
    
    def test_log_functions_exist(self):
        """Test that logging functions are importable."""
        from vbagent.ui.logging import log_agent_input, log_agent_output, log_agent_error
        assert callable(log_agent_input)
        assert callable(log_agent_output)
        assert callable(log_agent_error)
    
    def test_log_agent_input_no_debug(self, monkeypatch):
        """Test that logging doesn't output when debug is False."""
        from vbagent.ui.logging import log_agent_input
        from vbagent.config import VBAgentConfig
        import vbagent.config
        
        # Mock config to return debug=False
        mock_config = VBAgentConfig(debug=False)
        monkeypatch.setattr(vbagent.config, "get_config", lambda: mock_config)
        
        # Should not raise any errors
        log_agent_input("test_agent", "test input")
    
    def test_log_agent_output_no_debug(self, monkeypatch):
        """Test that logging doesn't output when debug is False."""
        from vbagent.ui.logging import log_agent_output
        from vbagent.config import VBAgentConfig
        import vbagent.config
        
        # Mock config to return debug=False
        mock_config = VBAgentConfig(debug=False)
        monkeypatch.setattr(vbagent.config, "get_config", lambda: mock_config)
        
        # Should not raise any errors
        log_agent_output("test_agent", "test output")
    
    def test_log_agent_error_no_debug(self, monkeypatch):
        """Test that logging doesn't output when debug is False."""
        from vbagent.ui.logging import log_agent_error
        from vbagent.config import VBAgentConfig
        import vbagent.config
        
        # Mock config to return debug=False
        mock_config = VBAgentConfig(debug=False)
        monkeypatch.setattr(vbagent.config, "get_config", lambda: mock_config)
        
        # Should not raise any errors
        log_agent_error("test_agent", ValueError("test error"))
