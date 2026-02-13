"""Base agent utilities using OpenAI Agents SDK."""

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

# Lazy import for heavy agents SDK - only import at runtime when needed
if TYPE_CHECKING:
    from agents import Agent, ModelSettings

from vbagent.config import get_model, get_model_settings, apply_provider_config


def _get_agent_class():
    """Lazy import of Agent class."""
    from agents import Agent
    return Agent


def _get_runner_class():
    """Lazy import of Runner class."""
    from agents import Runner
    return Runner


def _get_model_settings_class():
    """Lazy import of ModelSettings class."""
    from agents import ModelSettings
    return ModelSettings


def _truncate_text(text: str, max_chars: int = 500) -> str:
    """Truncate text intelligently: first 200, middle 100, last 200 chars."""
    if len(text) <= max_chars:
        return text
    
    first = 200
    middle = 100
    last = 200
    
    if len(text) <= first + last:
        return text
    
    start = text[:first]
    end = text[-last:]
    
    # Try to get middle section
    mid_start = (len(text) - middle) // 2
    mid_section = text[mid_start:mid_start + middle]
    
    return f"{start}\n\n... [truncated {len(text) - first - middle - last} chars] ...\n\n{mid_section}\n\n... [truncated] ...\n\n{end}"


def _print_debug_input(agent: "Agent", input_text: Any) -> None:
    """Print debug information about agent input."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    console = Console()
    
    # Get agent info
    model = agent.model or "default"
    reasoning = "unknown"
    if agent.model_settings:
        settings = agent.model_settings
        if hasattr(settings, 'reasoning') and settings.reasoning:
            reasoning_obj = settings.reasoning
            if isinstance(reasoning_obj, dict):
                reasoning = reasoning_obj.get('effort', 'unknown')
            elif hasattr(reasoning_obj, 'effort'):
                reasoning = reasoning_obj.effort or 'unknown'
    
    # Extract input text
    if isinstance(input_text, str):
        display_text = _truncate_text(input_text)
    elif isinstance(input_text, list):
        # Handle image messages
        has_image = any(
            isinstance(item, dict) and 
            item.get("type") == "message" and
            any(c.get("type") == "input_image" for c in item.get("content", []))
            for item in input_text
        )
        text_parts = []
        for item in input_text:
            if isinstance(item, dict) and item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "input_text":
                        text_parts.append(content.get("text", ""))
        
        display_text = "\n".join(text_parts)
        if has_image:
            display_text = "[Image attached]\n\n" + display_text
        display_text = _truncate_text(display_text)
    else:
        display_text = str(input_text)
    
    content = [
        f"Agent      : {agent.name}",
        f"Model      : {model}",
        f"Reasoning  : {reasoning}",
        "",
        display_text,
    ]
    
    console.print(Panel(
        "\n".join(content),
        title="[bold]DEBUG - INPUT[/bold]",
        border_style="yellow",
        padding=(0, 1)
    ))


def _print_debug_output(agent: "Agent", output: Any, duration: float) -> None:
    """Print debug information about agent output."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from pydantic import BaseModel
    
    console = Console()
    
    # Format output
    if isinstance(output, BaseModel):
        # Pydantic model - convert to JSON
        output_str = json.dumps(output.model_dump(), indent=2)
        syntax = Syntax(output_str, "json", theme="monokai", line_numbers=False)
        
        content = [
            f"Agent      : {agent.name}",
            f"Duration   : {duration:.2f}s",
            f"Status     : Success",
            "",
        ]
        
        console.print(Panel(
            "\n".join(content),
            title="[bold]DEBUG - OUTPUT[/bold]",
            border_style="green",
            padding=(0, 1)
        ))
        console.print(syntax)
        console.print()
    elif isinstance(output, (dict, list)):
        output_str = json.dumps(output, indent=2)
        syntax = Syntax(output_str, "json", theme="monokai", line_numbers=False)
        
        content = [
            f"Agent      : {agent.name}",
            f"Duration   : {duration:.2f}s",
            f"Status     : Success",
            "",
        ]
        
        console.print(Panel(
            "\n".join(content),
            title="[bold]DEBUG - OUTPUT[/bold]",
            border_style="green",
            padding=(0, 1)
        ))
        console.print(syntax)
        console.print()
    else:
        content = [
            f"Agent      : {agent.name}",
            f"Duration   : {duration:.2f}s",
            f"Status     : Success",
            "",
            str(output),
        ]
        
        console.print(Panel(
            "\n".join(content),
            title="[bold]DEBUG - OUTPUT[/bold]",
            border_style="green",
            padding=(0, 1)
        ))


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode an image file to base64.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (base64_data, media_type)
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    with open(path, "rb") as f:
        image_bytes = f.read()
    
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    
    suffix = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    
    return image_data, media_type


def create_image_message(image_path: str, text: str) -> list[dict[str, Any]]:
    """Create a message with image and text for the agent.
    
    Uses the OpenAI Responses API format for image input.
    
    Args:
        image_path: Path to the image file
        text: Text message to accompany the image
        
    Returns:
        List containing a single message dict in Responses API format
    """
    image_data, media_type = encode_image(image_path)
    # Responses API format: message with content list containing input_image and input_text
    return [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": f"data:{media_type};base64,{image_data}",
                    "detail": "auto"
                },
                {"type": "input_text", "text": text}
            ]
        }
    ]


def create_agent(
    name: str,
    instructions: str,
    model: Optional[str] = None,
    model_settings: Optional["ModelSettings"] = None,
    output_type: Optional[type] = None,
    tools: Optional[list] = None,
    agent_type: Optional[str] = None,
) -> "Agent":
    """Create an agent with default configuration.
    
    Args:
        name: Agent name
        instructions: System prompt / instructions
        model: Model to use (if None, uses config for agent_type)
        model_settings: Optional ModelSettings for temperature, max_tokens, etc.
        output_type: Optional Pydantic model for structured output
        tools: Optional list of tools (@function_tool decorated functions)
        agent_type: Agent type for config lookup (classifier, scanner, tikz, etc.)
        
    Returns:
        Configured Agent instance
    """
    Agent = _get_agent_class()
    
    # Apply provider config (base_url, api_key) before creating agent
    apply_provider_config()
    
    # Get model and settings from config if not explicitly provided
    if model is None:
        model = get_model(agent_type or "default")
    if model_settings is None:
        model_settings = get_model_settings(agent_type or "default")
    
    return Agent(
        name=name,
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        output_type=output_type,
        tools=tools or [],
    )


def _print_agent_info(agent: "Agent") -> None:
    """Print agent information when running (now uses spinner in run_agent_sync)."""
    # Deprecated - spinner is shown in run_agent_sync
    pass


async def run_agent(agent: "Agent", input_text: str | list) -> Any:
    """Run an agent asynchronously and return the final output.
    
    Args:
        agent: The Agent instance to run
        input_text: The input text or message (can be string or list for images)
        
    Returns:
        The agent's final output (string or structured type)
    """
    Runner = _get_runner_class()
    _print_agent_info(agent)
    result = await Runner.run(agent, input=input_text)
    return result.final_output


def run_agent_sync(agent: "Agent", input_text: str | list, show_spinner: bool = True) -> Any:
    """Run an agent synchronously and return the final output.
    
    Uses a thread to allow immediate Ctrl+C interruption.
    
    Args:
        agent: The Agent instance to run
        input_text: The input text or message (can be string or list for images)
        show_spinner: Whether to show animated spinner (default: True)
        
    Returns:
        The agent's final output (string or structured type)
        
    Raises:
        KeyboardInterrupt: If user presses Ctrl+C
    """
    import concurrent.futures
    import threading
    import time
    import json
    from ..config import get_config
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    Runner = _get_runner_class()
    
    # Get agent info for display
    model = agent.model or "default"
    reasoning = "unknown"
    if agent.model_settings:
        settings = agent.model_settings
        if hasattr(settings, 'reasoning') and settings.reasoning:
            reasoning_obj = settings.reasoning
            if isinstance(reasoning_obj, dict):
                reasoning = reasoning_obj.get('effort', 'unknown')
            elif hasattr(reasoning_obj, 'effort'):
                reasoning = reasoning_obj.effort or 'unknown'
    
    console = Console()
    config = get_config()
    
    # Debug mode: print input
    if config.debug:
        _print_debug_input(agent, input_text)
    
    # Show spinner during execution (if enabled)
    start_time = time.time()
    
    # Use a thread pool to run the agent, allowing Ctrl+C to interrupt
    result_holder = {"result": None, "error": None}
    
    def run_in_thread():
        try:
            result_holder["result"] = Runner.run_sync(agent, input=input_text)
        except Exception as e:
            result_holder["error"] = e
    
    if show_spinner:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            TextColumn("│"),
            TextColumn("[dim]{task.fields[model]}[/dim]"),
            TextColumn("│"),
            TextColumn("[dim]{task.fields[reasoning]} reasoning[/dim]"),
            console=console,
            transient=True
        )
        
        with progress:
            task = progress.add_task(
                agent.name,
                model=model,
                reasoning=reasoning,
                total=None
            )
            
            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()
            
            # Wait for thread with small intervals to allow Ctrl+C handling
            while thread.is_alive():
                thread.join(timeout=0.1)
    else:
        # No spinner - just run in thread
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        while thread.is_alive():
            thread.join(timeout=0.1)
    
    if result_holder["error"]:
        raise result_holder["error"]
    
    duration = time.time() - start_time
    final_output = result_holder["result"].final_output
    
    # Print completion (subtle) - only if spinner was shown
    if show_spinner:
        console.print(f"[dim]│ {agent.name} │ {model} │ {duration:.1f}s[/dim]")
    
    # Debug mode: print output
    if config.debug:
        _print_debug_output(agent, final_output, duration)
    
    return final_output
