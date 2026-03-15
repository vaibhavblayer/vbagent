"""Rich UI components for VBAgent CLI.

Provides consistent, modern UI components for the VBAgent CLI
including tables, panels, progress bars, and debug logging.
"""

from vbagent.ui.styles import COLORS, TABLE_STYLES, VBAGENT_THEME, STATUS, CATEGORY_COLORS
from vbagent.ui.tables import create_table, create_result_table, create_category_table, add_category_row
from vbagent.ui.components import (
    create_panel,
    create_progress,
    create_code_block,
    create_status_line,
    create_badge,
    create_section_header,
)
from vbagent.ui.logging import log_agent_input, log_agent_output, log_agent_error

__all__ = [
    # Styles
    "COLORS",
    "TABLE_STYLES",
    "VBAGENT_THEME",
    "STATUS",
    "CATEGORY_COLORS",
    # Tables
    "create_table",
    "create_result_table",
    "create_category_table",
    "add_category_row",
    # Components
    "create_panel",
    "create_progress",
    "create_code_block",
    "create_status_line",
    "create_badge",
    "create_section_header",
    # Logging
    "log_agent_input",
    "log_agent_output",
    "log_agent_error",
]
