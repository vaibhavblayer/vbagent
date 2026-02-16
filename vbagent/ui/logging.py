"""Structured logging for agent I/O."""

from typing import Any, Optional
import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def log_agent_input(
    agent_name: str,
    input_data: Any,
    model: Optional[str] = None,
) -> None:
    """Log agent input in debug mode.
    
    Args:
        agent_name: Name of the agent
        input_data: Input data (text, dict, etc.)
        model: Model being used
    """
    from vbagent.config import get_config
    
    if not get_config().debug:
        return
    
    # Format input
    if isinstance(input_data, dict):
        formatted = json.dumps(input_data, indent=2)
        syntax = Syntax(formatted, "json", theme="monokai")
    elif isinstance(input_data, str):
        formatted = input_data[:500] + "..." if len(input_data) > 500 else input_data
        syntax = formatted
    else:
        syntax = str(input_data)
    
    title = f"🔵 {agent_name} Input"
    if model:
        title += f" ({model})"
    
    panel = Panel(
        syntax,
        title=title,
        border_style="blue",
        padding=(1, 2),
    )
    
    console.print(panel)


def log_agent_output(
    agent_name: str,
    output_data: Any,
    duration: Optional[float] = None,
) -> None:
    """Log agent output in debug mode.
    
    Args:
        agent_name: Name of the agent
        output_data: Output data
        duration: Execution duration in seconds
    """
    from vbagent.config import get_config
    
    if not get_config().debug:
        return
    
    # Format output
    if isinstance(output_data, dict):
        formatted = json.dumps(output_data, indent=2)
        syntax = Syntax(formatted, "json", theme="monokai")
    elif isinstance(output_data, str):
        formatted = output_data[:500] + "..." if len(output_data) > 500 else output_data
        syntax = formatted
    else:
        syntax = str(output_data)
    
    title = f"🟢 {agent_name} Output"
    if duration:
        title += f" ({duration:.2f}s)"
    
    panel = Panel(
        syntax,
        title=title,
        border_style="green",
        padding=(1, 2),
    )
    
    console.print(panel)


def log_agent_error(
    agent_name: str,
    error: Exception,
) -> None:
    """Log agent error in debug mode.
    
    Args:
        agent_name: Name of the agent
        error: Exception that occurred
    """
    from vbagent.config import get_config
    
    if not get_config().debug:
        return
    
    panel = Panel(
        f"[bold red]{type(error).__name__}:[/bold red] {str(error)}",
        title=f"🔴 {agent_name} Error",
        border_style="red",
        padding=(1, 2),
    )
    
    console.print(panel)
