"""Base agent utilities using OpenAI Agents SDK."""

import asyncio
import base64
import contextlib
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, TypeVar

# Lazy import for heavy agents SDK - only import at runtime when needed
if TYPE_CHECKING:
    from agents import Agent, ModelSettings

from vbagent.config import apply_provider_config, get_model, get_model_settings

# Global lock to prevent concurrent spinners
_spinner_lock = threading.Lock()

# Limit actual model requests across nested pipeline thread pools.  The CLI can
# process several images concurrently and each image can fan out into scan,
# TikZ, and option calls.  Keeping the limit here covers library consumers too.
_max_concurrent_requests = max(
    1, int(os.environ.get("VBAGENT_MAX_CONCURRENT_REQUESTS", "6"))
)
_request_slots = threading.BoundedSemaphore(_max_concurrent_requests)

T = TypeVar("T")


@dataclass(frozen=True)
class PinnedRequestCredentials:
    """Credentials retained for a short server-managed response chain."""

    api_key: Optional[str]
    base_url: Optional[str]
    key_name: Optional[str]
    cache_domain: Optional[str] = None
    managed_profile: bool = False


@dataclass(frozen=True)
class ContinuedAgentResult:
    """Output and continuation metadata from a grouped agent request."""

    final_output: Any
    response_id: Optional[str]
    credentials: PinnedRequestCredentials


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


def create_cacheable_image_message(
    image_path: str,
    text: str,
    cache_boundary_text: str,
) -> list[dict[str, Any]]:
    """Create a vision input with a stable GPT-5.6 cache breakpoint.

    The developer message is rendered after the agent instructions and before
    the changing image. In explicit cache mode, its breakpoint therefore
    caches the reusable instructions without writing a new image-specific
    prefix for every request.
    """
    return [
        {
            "type": "message",
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": cache_boundary_text,
                    "prompt_cache_breakpoint": {"mode": "explicit"},
                }
            ],
        },
        *create_image_message(image_path, text),
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
    
    # API-key rotation is resolved inside run_agent/run_agent_sync.  Selecting
    # here would mutate process-global environment state while parallel agents
    # are being constructed and can attach the wrong key to another request.
    return Agent(
        name=name,
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        output_type=output_type,
        tools=tools or [],
    )


def _resolve_request_credentials(
    model: str,
    affinity_key: str | None = None,
    excluded_key_names: set[str] | None = None,
) -> PinnedRequestCredentials:
    """Resolve per-request credentials without relying on shared SDK clients.

    Managed-profile selection is fail-closed: once an API profile file is
    configured, disabled, exhausted, or cooling-down profiles cannot silently
    fall through to an unrelated environment key.
    """
    from vbagent.config import PROVIDERS, get_config

    config = get_config()
    api_key: Optional[str] = None
    key_name: Optional[str] = None

    if not config.base_url:
        from vbagent.api_keys import KeyManager

        manager = KeyManager.get_instance()
        if manager.is_configured():
            selected = manager.select_key_for_model(
                model,
                affinity_key=affinity_key,
                excluded_names=excluded_key_names or (),
                reserve=True,
            )
            return PinnedRequestCredentials(
                selected.api_key,
                None,
                selected.key_name,
                selected.cache_domain,
                True,
            )

    if api_key is None:
        api_key = config.api_key
        if api_key:
            key_name = "config.api_key"

    if api_key is None and config.base_url:
        for info in PROVIDERS.values():
            provider_url = info.get("base_url")
            if provider_url and config.base_url.rstrip("/") == provider_url.rstrip("/"):
                api_key = os.environ.get(info["env_key"])
                if api_key:
                    key_name = info["env_key"]
                break

    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            key_name = "OPENAI_API_KEY"

    return PinnedRequestCredentials(api_key, config.base_url, key_name)


def _create_request_provider(
    model: str,
    credentials: PinnedRequestCredentials | None = None,
    affinity_key: str | None = None,
    excluded_key_names: set[str] | None = None,
):
    """Create an SDK provider and HTTP client owned by one agent request."""
    from agents.models.openai_provider import OpenAIProvider
    from openai import AsyncOpenAI

    if credentials is None:
        pinned = _resolve_request_credentials(
            model,
            affinity_key=affinity_key,
            excluded_key_names=excluded_key_names,
        )
    else:
        pinned = credentials
    try:
        client = AsyncOpenAI(api_key=pinned.api_key, base_url=pinned.base_url)
        provider = OpenAIProvider(openai_client=client)
    except BaseException:
        if credentials is None and pinned.managed_profile:
            _release_managed_profile(pinned.key_name)
        raise
    return provider, client, pinned.key_name, pinned


async def _execute_agent_run(
    agent: "Agent",
    input_text: str | list,
    timeout: float | None,
    group_id: str | None = None,
    previous_response_id: str | None = None,
    credentials: PinnedRequestCredentials | None = None,
    allow_cache_sharding: bool = True,
):
    """Execute one SDK run with cache routing, failover, and cancellation."""
    from agents import RunConfig

    from vbagent.agents.prompt_cache import prepare_prompt_cache

    Runner = _get_runner_class()
    model = str(agent.model or "default")
    cache_plan = prepare_prompt_cache(
        agent,
        input_text,
        group_id=group_id,
        previous_response_id=previous_response_id,
        allow_sharding=allow_cache_sharding,
    )
    queued_at = time.monotonic()
    acquired = False
    while not acquired:
        acquired = _request_slots.acquire(blocking=False)
        if not acquired:
            await asyncio.sleep(0.05)

    queue_duration = time.monotonic() - queued_at
    request_started = time.monotonic()
    key_name = None
    cache_domain = None
    excluded_key_names: set[str] = set()
    last_provider_error: BaseException | None = None
    failover_count = 0
    try:
        while True:
            client = None
            pinned = credentials
            try:
                try:
                    if credentials is None:
                        provider_kwargs = {"affinity_key": cache_plan.affinity_key}
                        if excluded_key_names:
                            provider_kwargs["excluded_key_names"] = excluded_key_names
                        created = _create_request_provider(model, **provider_kwargs)
                    else:
                        created = _create_request_provider(model, credentials)
                except Exception as selection_error:
                    if last_provider_error is not None:
                        raise last_provider_error from selection_error
                    raise

                provider, client, key_name = created[:3]
                pinned = (
                    created[3]
                    if len(created) > 3
                    else credentials or PinnedRequestCredentials(None, None, key_name)
                )
                cache_domain = pinned.cache_domain
                from ..ui.logging import log_agent_started

                log_agent_started(
                    agent.name,
                    model=model,
                    queue_duration=queue_duration if failover_count == 0 else 0.0,
                    key_name=key_name,
                    cache_domain=cache_domain,
                    cache_group_id=cache_plan.cache_group_id,
                    profile_attempt=failover_count + 1,
                    has_image=_input_has_image(cache_plan.input_data),
                    reasoning=_extract_reasoning(agent),
                )
                run = Runner.run(
                    agent,
                    input=cache_plan.input_data,
                    run_config=RunConfig(
                        model_provider=provider,
                        model_settings=cache_plan.model_settings,
                        group_id=cache_plan.trace_group_id,
                    ),
                    previous_response_id=previous_response_id,
                )
                if timeout is None:
                    result = await run
                else:
                    try:
                        remaining = timeout - (time.monotonic() - request_started)
                        if remaining <= 0:
                            raise TimeoutError
                        result = await asyncio.wait_for(run, timeout=remaining)
                    except TimeoutError as exc:
                        raise TimeoutError(
                            f"{agent.name} timed out after {timeout:.0f}s (model: {model})"
                        ) from exc

                usage = result.context_wrapper.usage if result.context_wrapper else None
                actual_model = _extract_actual_model(result) or model
                _track_usage(actual_model, usage, key_name)
                request_duration = time.monotonic() - request_started
                return (
                    result,
                    key_name,
                    cache_domain,
                    queue_duration,
                    request_duration,
                    pinned,
                    cache_plan.cache_group_id,
                )
            except BaseException as exc:
                status_code = _provider_status_code(exc)
                may_failover = (
                    credentials is None
                    and previous_response_id is None
                    and pinned is not None
                    and pinned.managed_profile
                    and bool(key_name)
                    and status_code in {401, 403, 429}
                )
                if may_failover:
                    from ..ui.logging import record_agent_event

                    cooldown = 60.0 if status_code == 429 else 300.0
                    _mark_profile_unavailable(key_name, cooldown)
                    excluded_key_names.add(key_name)
                    failover_count += 1
                    last_provider_error = exc
                    record_agent_event(
                        "profile_failover",
                        agent.name,
                        model=model,
                        key_name=key_name,
                        cache_domain=cache_domain,
                        cache_group_id=cache_plan.cache_group_id,
                        status_code=status_code,
                        next_attempt=failover_count + 1,
                    )
                    continue
                raise
            finally:
                # Cleanup and reservation release must not invalidate a valid
                # response or leak capacity after a failed provider attempt.
                if client is not None:
                    with contextlib.suppress(Exception):
                        await client.close()
                if credentials is None and pinned is not None and pinned.managed_profile:
                    _release_managed_profile(pinned.key_name)
    except BaseException as exc:
        with contextlib.suppress(Exception):
            exc._vbagent_metadata = {
                "model": model,
                "key_name": key_name,
                "cache_domain": cache_domain,
                "cache_group_id": cache_plan.cache_group_id,
                "profile_failovers": failover_count,
                "queue_duration": queue_duration,
                "request_duration": time.monotonic() - request_started,
            }
        raise
    finally:
        if acquired:
            _request_slots.release()


def _provider_status_code(error: BaseException) -> int | None:
    """Extract an HTTP status from OpenAI SDK and compatible errors."""
    value = getattr(error, "status_code", None)
    if isinstance(value, int):
        return value
    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _mark_profile_unavailable(key_name: str, cooldown_seconds: float) -> None:
    """Put one managed profile in a process-local provider cooldown."""
    from vbagent.api_keys import KeyManager

    KeyManager.get_instance().mark_profile_unavailable(key_name, cooldown_seconds)


def _release_managed_profile(key_name: str | None) -> None:
    """Release the request reservation held by one managed profile."""
    from vbagent.api_keys import KeyManager

    KeyManager.get_instance().release_profile(key_name)


def _run_coroutine_sync(factory: Callable[[], Awaitable[T]]) -> T:
    """Run an async operation from synchronous code, including async callers.

    Normal CLI/library calls execute on the current thread.  If a synchronous
    API is invoked from a thread that already owns a running event loop, use a
    helper thread rather than nesting event loops.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    holder: dict[str, Any] = {"result": None, "error": None}

    def worker() -> None:
        try:
            holder["result"] = asyncio.run(factory())
        except BaseException as exc:
            holder["error"] = exc

    thread = threading.Thread(target=worker, daemon=False)
    thread.start()
    thread.join()
    if holder["error"] is not None:
        raise holder["error"]
    return holder["result"]


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
        last_response_id = getattr(result, "last_response_id", None)
        if last_response_id:
            return last_response_id
        if result.raw_responses:
            last = result.raw_responses[-1]
            return getattr(last, "response_id", None)
    except (AttributeError, IndexError):
        pass
    return None


def _extract_actual_model(result) -> Optional[str]:
    """Extract the actual model used from raw_responses."""
    try:
        if result.raw_responses:
            last = result.raw_responses[-1]
            return getattr(last, "model", None)
    except (AttributeError, IndexError):
        pass
    return None


def _track_usage(model: str, usage, key_name: Optional[str]) -> None:
    """Attribute usage to the key selected for this specific request."""
    if not usage or not hasattr(usage, "total_tokens"):
        return
    try:
        from vbagent.api_keys import KeyManager
        from vbagent.config import get_config

        if get_config().base_url:
            return
        manager = KeyManager.get_instance()
        if manager.is_enabled():
            manager.track_usage(model, usage.total_tokens, key_name=key_name)
    except Exception:
        # Usage accounting must never invalidate a completed model response.
        return


async def run_agent(agent: "Agent", input_text: str | list) -> Any:
    """Run an agent asynchronously and return the final output.
    
    Args:
        agent: The Agent instance to run
        input_text: The input text or message (can be string or list for images)
        
    Returns:
        The agent's final output (string or structured type)
    """
    import time

    from ..ui.logging import (
        log_agent_error,
        log_agent_input,
        log_agent_output,
        log_agent_usage,
    )
    
    model = agent.model or "default"
    reasoning = _extract_reasoning(agent)
    has_image = _input_has_image(input_text)
    
    log_agent_input(agent.name, input_text, model)
    
    start_time = time.time()
    try:
        (
            result,
            key_name,
            cache_domain,
            queue_duration,
            request_duration,
            _,
            cache_group_id,
        ) = await _execute_agent_run(agent, input_text, timeout=None)
        duration = time.time() - start_time
        
        # Extract usage, response ID, and actual model
        usage = result.context_wrapper.usage if result.context_wrapper else None
        response_id = _extract_response_id(result)
        actual_model = _extract_actual_model(result) or model
        
        log_agent_usage(agent.name, model=actual_model, duration=duration,
                        usage=usage, response_id=response_id,
                        has_image=has_image, reasoning=reasoning,
                        queue_duration=queue_duration,
                        request_duration=request_duration,
                        key_name=key_name,
                        cache_domain=cache_domain,
                        cache_group_id=cache_group_id)
        log_agent_output(agent.name, result.final_output, duration)
        
        return result.final_output
    except Exception as e:
        log_agent_error(agent.name, e)
        raise


def _run_agent_sync_impl(
    agent: "Agent",
    input_text: str | list,
    show_spinner: bool,
    timeout: float | None,
    group_id: str | None,
    previous_response_id: str | None = None,
    credentials: PinnedRequestCredentials | None = None,
    return_continuation: bool = False,
) -> Any:
    """Run an agent synchronously and return the final output.
    
    Runs one cancellable async SDK task behind the synchronous API.
    
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
    import time

    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    from ..ui.logging import (
        get_agent_console,
        log_agent_error,
        log_agent_input,
        log_agent_output,
        log_agent_usage,
    )
    
    # Get agent info for display
    model = agent.model or "default"
    reasoning = _extract_reasoning(agent)
    has_image = _input_has_image(input_text)
    
    # Log input (before spinner starts)
    log_agent_input(agent.name, input_text, model)
    active_console = get_agent_console()
    active_console.file.flush()
    
    start_time = time.time()
    try:
        if show_spinner:
            with _spinner_lock:
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}[/bold cyan]"),
                    TextColumn("│"),
                    TextColumn("[dim]{task.fields[model]}[/dim]"),
                    TextColumn("│"),
                    TextColumn("[dim]{task.fields[reasoning]} reasoning[/dim]"),
                    TextColumn("│"),
                    TimeElapsedColumn(),
                    console=active_console,
                    transient=True,
                    refresh_per_second=10,
                )
                with progress:
                    progress.add_task(
                        agent.name,
                        model=model,
                        reasoning=reasoning,
                        total=None,
                    )
                    (
                        run_result,
                        key_name,
                        cache_domain,
                        queue_duration,
                        request_duration,
                        pinned,
                        effective_cache_group_id,
                    ) = _run_coroutine_sync(
                        lambda: _execute_agent_run(
                            agent,
                            input_text,
                            timeout,
                            group_id=group_id,
                            previous_response_id=previous_response_id,
                            credentials=credentials,
                            allow_cache_sharding=not return_continuation,
                        )
                    )
        else:
            (
                run_result,
                key_name,
                cache_domain,
                queue_duration,
                request_duration,
                pinned,
                effective_cache_group_id,
            ) = _run_coroutine_sync(
                lambda: _execute_agent_run(
                    agent,
                    input_text,
                    timeout,
                    group_id=group_id,
                    previous_response_id=previous_response_id,
                    credentials=credentials,
                    allow_cache_sharding=not return_continuation,
                )
            )
    except BaseException as exc:
        log_agent_error(agent.name, exc)
        raise
    
    duration = time.time() - start_time
    final_output = run_result.final_output
    
    # Extract usage and response ID from RunResult
    usage = run_result.context_wrapper.usage if run_result.context_wrapper else None
    response_id = _extract_response_id(run_result)
    
    # Get the actual model used (from API response)
    actual_model = _extract_actual_model(run_result) or model
    
    # Always show compact completion line with token usage
    log_agent_usage(agent.name, model=actual_model, duration=duration,
                    usage=usage, response_id=response_id,
                    has_image=has_image, reasoning=reasoning,
                    queue_duration=queue_duration,
                    request_duration=request_duration,
                    key_name=key_name,
                    cache_domain=cache_domain,
                    cache_group_id=effective_cache_group_id)
    
    # Log full output
    log_agent_output(agent.name, final_output, duration)
    
    if return_continuation:
        return ContinuedAgentResult(
            final_output=final_output,
            response_id=response_id,
            credentials=pinned,
        )
    return final_output


def run_agent_sync(agent: "Agent", input_text: str | list, show_spinner: bool = True, timeout: float | None = None) -> Any:
    """Run an agent synchronously and return the final output."""
    return _run_agent_sync_impl(
        agent,
        input_text,
        show_spinner=show_spinner,
        timeout=timeout,
        group_id=None,
    )


def run_agent_sync_grouped(
    agent: "Agent",
    input_text: str | list,
    group_id: str,
    *,
    show_spinner: bool = True,
    timeout: float | None = None,
) -> Any:
    """Run an agent with a stable SDK grouping ID for prompt-cache reuse.

    This is intentionally separate from :func:`run_agent_sync` so existing
    library consumers keep the same public call signature. Official OpenAI
    Responses requests derive a stable prompt cache key from ``group_id``;
    compatible third-party providers continue to run without that optimization.
    """
    return _run_agent_sync_impl(
        agent,
        input_text,
        show_spinner=show_spinner,
        timeout=timeout,
        group_id=group_id,
    )


def run_agent_sync_continued(
    agent: "Agent",
    input_text: str | list,
    group_id: str,
    *,
    previous_response_id: str | None = None,
    credentials: PinnedRequestCredentials | None = None,
    show_spinner: bool = True,
    timeout: float | None = None,
) -> ContinuedAgentResult:
    """Run one grouped Responses turn and return state for the next turn."""
    if previous_response_id is not None and credentials is None:
        raise ValueError(
            "credentials from the previous ContinuedAgentResult are required "
            "when previous_response_id is supplied"
        )
    return _run_agent_sync_impl(
        agent,
        input_text,
        show_spinner=show_spinner,
        timeout=timeout,
        group_id=group_id,
        previous_response_id=previous_response_id,
        credentials=credentials,
        return_continuation=True,
    )
