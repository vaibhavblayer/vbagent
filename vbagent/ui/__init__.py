"""Rich UI components for VBAgent CLI.

This module provides consistent, modern UI components for the VBAgent CLI
including tables, panels, progress bars, and debug logging.
"""

from vbagent.ui.styles import COLORS, TABLE_STYLES, VBAGENT_THEME
from vbagent.ui.tables import create_table, create_result_table
from vbagent.ui.components import create_panel, create_progress, create_code_block
from vbagent.ui.logging import log_agent_input, log_agent_output, log_agent_error

__all__ = [
    # Styles
    "COLORS",
    "TABLE_STYLES",
    "VBAGENT_THEME",
    # Tables
    "create_table",
    "create_result_table",
    # Components
    "create_panel",
    "create_progress",
    "create_code_block",
    # Logging
    "log_agent_input",
    "log_agent_output",
    "log_agent_error",
]
