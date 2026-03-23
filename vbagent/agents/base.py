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


def _extract_reasoning(agent: "Agent") -> str:
    """Extract reasoning effort string from agent model settings."""
    if not agent.model_settings:
        return "none"
    settings = agent.model_settings
    if not hasattr(settings, 'reasoning') or not settings.reasoning:
        return "none"
    reasoning_obj = settings.reasoning
    if isinstance(reasoning_obj, dict):
        return reasoning_obj.get('effort', 'none')
    if hasattr(reasoning_obj, 'effort'):
        return reasoning_obj.effort or 'none'
    return "none"


def _input_has_image(input_text: str | list) -> bool:
    """Check if the input contains an image."""
    if not isinstance(input_text, list):
        return False
    for item in input_text:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("input_image", "image_url", "image"):
                    return True
    return False


def _extract_response_id(result) -> Optional[str]:
    """Extract the last response ID from raw_responses."""
    try:
        if result.raw_responses:
            last = result.raw_responses[-1]
            return getattr(last, "response_id", None)
    except (AttributeError, IndexError):
        pass
    return None


async def run_agent(agent: "Agent", input_text: str | list) -> Any:
    """Run an agent asynchronously and return the final output.
    
    Args:
        agent: The Agent instance to run
        input_text: The input text or message (can be string or list for images)
        
    Returns:
        The agent's final output (string or structured type)
    """
    import time
    from ..ui.logging import log_agent_input, log_agent_output, log_agent_error, log_agent_usage
    
    Runner = _get_runner_class()
    
    model = agent.model or "default"
    reasoning = _extract_reasoning(agent)
    has_image = _input_has_image(input_text)
    
    log_agent_input(agent.name, input_text, model)
    
    start_time = time.time()
    try:
        result = await Runner.run(agent, input=input_text)
        duration = time.time() - start_time
        
        # Extract usage and response ID
        usage = result.context_wrapper.usage if result.context_wrapper else None
        response_id = _extract_response_id(result)
        
        log_agent_usage(agent.name, model=model, duration=duration,
                        usage=usage, response_id=response_id,
                        has_image=has_image, reasoning=reasoning)
        log_agent_output(agent.name, result.final_output, duration)
        
        return result.final_output
    except Exception as e:
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
    import threading
    import time
    from ..ui.logging import log_agent_input, log_agent_output, log_agent_error, log_agent_usage, console, _log_lock
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    Runner = _get_runner_class()
    
    # Get agent info for display
    model = agent.model or "default"
    reasoning = _extract_reasoning(agent)
    has_image = _input_has_image(input_text)
    
    # Log input (before spinner starts)
    log_agent_input(agent.name, input_text, model)
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
    
    if show_spinner:
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
        # No spinner — call Runner.run_sync directly on the current thread.
        # This is critical for parallel pipelines: each worker thread gets its
        # own asyncio event loop and its own httpx connection, avoiding the
        # shared-http-client deadlock that occurs when multiple inner threads
        # all share the same global AsyncClient singleton.
        try:
            result_holder["result"] = Runner.run_sync(agent, input=input_text)
        except Exception as e:
            result_holder["error"] = e
        # Check timeout (approximate — we can't interrupt a blocking call,
        # but we can raise after it returns)
        if timeout and (time.time() - start_time) > timeout:
            raise TimeoutError(
                f"{agent.name} timed out after {timeout:.0f}s (model: {model})"
            )
    
    if result_holder["error"]:
        log_agent_error(agent.name, result_holder["error"])
        raise result_holder["error"]
    
    duration = time.time() - start_time
    run_result = result_holder["result"]
    final_output = run_result.final_output
    
    # Extract usage and response ID from RunResult
    usage = run_result.context_wrapper.usage if run_result.context_wrapper else None
    response_id = _extract_response_id(run_result)
    
    # Always show compact completion line with token usage
    log_agent_usage(agent.name, model=model, duration=duration,
                    usage=usage, response_id=response_id,
                    has_image=has_image, reasoning=reasoning)
    
    # Log full output
    log_agent_output(agent.name, final_output, duration)
    
    return final_output
