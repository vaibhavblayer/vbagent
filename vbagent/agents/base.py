"""Base agent utilities using OpenAI Agents SDK."""

import base64
import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

# Lazy import for heavy agents SDK - only import at runtime when needed
if TYPE_CHECKING:
    from agents import Agent, ModelSettings

from vbagent.config import get_model, get_model_settings, apply_provider_config

# Global lock to prevent concurrent spinners
_spinner_lock = threading.Lock()


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
    import time
    from ..ui.logging import log_agent_input, log_agent_output, log_agent_error
    
    Runner = _get_runner_class()
    _print_agent_info(agent)
    
    # Log input in debug mode
    model = agent.model or "default"
    log_agent_input(agent.name, input_text, model)
    
    start_time = time.time()
    try:
        result = await Runner.run(agent, input=input_text)
        duration = time.time() - start_time
        
        # Log output in debug mode
        log_agent_output(agent.name, result.final_output, duration)
        
        return result.final_output
    except Exception as e:
        # Log error in debug mode
        log_agent_error(agent.name, e)
        raise


def run_agent_sync(agent: "Agent", input_text: str | list, show_spinner: bool = True, timeout: float | None = None) -> Any:
    """Run an agent synchronously and return the final output.
    
    Uses a thread to allow immediate Ctrl+C interruption.
    
    Args:
        agent: The Agent instance to run
        input_text: The input text or message (can be string or list for images)
        show_spinner: Whether to show animated spinner (default: True)
        timeout: Maximum seconds to wait for the agent (default: None = no limit).
                 If exceeded, raises TimeoutError.
        
    Returns:
        The agent's final output (string or structured type)
        
    Raises:
        KeyboardInterrupt: If user presses Ctrl+C
        TimeoutError: If timeout is exceeded
    """
    import concurrent.futures
    import threading
    import time
    import json
    from ..config import get_config
    from ..ui.logging import log_agent_input, log_agent_output, log_agent_error, console, _log_lock
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    Runner = _get_runner_class()
    
    # Get agent info for display
    model = agent.model or "default"
    reasoning = "none"  # Default for models without reasoning support
    if agent.model_settings:
        settings = agent.model_settings
        if hasattr(settings, 'reasoning') and settings.reasoning:
            reasoning_obj = settings.reasoning
            if isinstance(reasoning_obj, dict):
                reasoning = reasoning_obj.get('effort', 'none')
            elif hasattr(reasoning_obj, 'effort'):
                reasoning = reasoning_obj.effort or 'none'
    
    config = get_config()
    is_debug = config.debug
    
    # Debug mode: log input using UI module (before spinner starts)
    # Flush to ensure debug panel is fully rendered before spinner
    log_agent_input(agent.name, input_text, model)
    if is_debug:
        console.file.flush()
    
    # Show spinner during execution (if enabled)
    start_time = time.time()
    
    # Use a thread pool to run the agent, allowing Ctrl+C to interrupt
    result_holder = {"result": None, "error": None}
    
    def run_in_thread():
        try:
            result_holder["result"] = Runner.run_sync(agent, input=input_text)
        except Exception as e:
            result_holder["error"] = e
    
    # In debug mode, skip the spinner entirely to prevent overlap with debug Panels
    use_spinner = show_spinner and not is_debug
    
    if use_spinner:
        # Use global lock to prevent concurrent spinners
        with _spinner_lock:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}[/bold cyan]"),
                TextColumn("│"),
                TextColumn("[dim]{task.fields[model]}[/dim]"),
                TextColumn("│"),
                TextColumn("[dim]{task.fields[reasoning]} reasoning[/dim]"),
                console=console,
                transient=True,
                refresh_per_second=10
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
                
                while thread.is_alive():
                    thread.join(timeout=0.1)
                    if timeout and (time.time() - start_time) > timeout:
                        progress.stop()
                        raise TimeoutError(
                            f"{agent.name} timed out after {timeout:.0f}s (model: {model})"
                        )
    else:
        # No spinner — debug mode or show_spinner=False
        # Always log model and reasoning info when spinner is disabled
        if show_spinner:
            console.print(f"[dim]⏳ {agent.name} running ({model}, {reasoning} reasoning)...[/dim]")
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        while thread.is_alive():
            thread.join(timeout=0.1)
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"{agent.name} timed out after {timeout:.0f}s (model: {model})"
                )
    
    if result_holder["error"]:
        # Debug mode: log error using UI module
        log_agent_error(agent.name, result_holder["error"])
        raise result_holder["error"]
    
    duration = time.time() - start_time
    final_output = result_holder["result"].final_output
    
    # Print completion (subtle) - show model and reasoning info
    if use_spinner:
        console.print(f"[dim]✓ {agent.name} completed in {duration:.1f}s ({model}, {reasoning} reasoning)[/dim]")
    elif show_spinner:
        # No spinner but show_spinner=True (debug mode) - show completion
        console.print(f"[dim]✓ {agent.name} completed in {duration:.1f}s ({model}, {reasoning} reasoning)[/dim]")
    
    # Debug mode: log output using UI module
    log_agent_output(agent.name, final_output, duration)
    
    return final_output
