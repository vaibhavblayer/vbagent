"""CLI commands for configuring vbagent models.

Provides commands to view and set model configurations for different agents.
"""

import click

from vbagent.config import (
    get_config,
    save_config,
    reset_config,
    init_workspace,
    has_workspace_config,
    get_workspace_config_path,
    get_provider_name,
    apply_model_group,
    AGENT_TYPES,
    MODELS,
    MODEL_GROUPS,
    SUBJECTS,
    PROVIDERS,
    CONFIG_FILE,
    WORKSPACE_CONFIG_FILE,
)


def _get_console():
    """Lazy import of rich Console."""
    from rich.console import Console
    return Console()


def _get_table(*args, **kwargs):
    """Lazy import of rich Table."""
    from rich.table import Table
    return Table(*args, **kwargs)


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def config():
    """Configure vbagent models and settings.
    
    View and modify model configurations for different agent types.
    
    \b
    Agent Types:
        classifier  - Image classification
        scanner     - LaTeX extraction from images
        tikz        - TikZ diagram generation
        idea        - Concept extraction
        alternate   - Alternate solution generation
        variant     - Problem variant generation
        converter   - Format conversion
    
    \b
    Examples:
        vbagent config show
        vbagent config models
        vbagent config set scanner --model gpt-4o
        vbagent config set scanner -m gpt-4o
        vbagent config set variant --model o1-mini --reasoning medium
        vbagent config reset
    """
    pass


@config.command()
def show():
    """Show current model configuration for all agents."""
    console = _get_console()
    cfg = get_config()
    
    # Show config source
    workspace_path = get_workspace_config_path()
    if workspace_path:
        console.print(f"[dim]Using workspace config: {workspace_path}[/dim]\n")
    else:
        console.print(f"[dim]Using global config: {CONFIG_FILE}[/dim]\n")
    
    # Create table
    table = _get_table(title="Agent Model Configuration")
    table.add_column("Agent", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Reasoning", style="yellow")
    table.add_column("Temperature")
    table.add_column("Max Tokens")
    
    # Add default row
    table.add_row(
        "[bold]default[/bold]",
        cfg.default_model,
        cfg.default_reasoning_effort,
        "-",
        "-",
        style="dim"
    )
    
    # Add each agent
    for agent_type in AGENT_TYPES:
        agent_cfg = getattr(cfg, agent_type)
        table.add_row(
            agent_type,
            agent_cfg.model,
            agent_cfg.reasoning_effort,
            str(agent_cfg.temperature) if agent_cfg.temperature else "-",
            str(agent_cfg.max_tokens) if agent_cfg.max_tokens else "-",
        )
    
    console.print(table)
    
    # Show subject and provider
    console.print(f"\n[bold]Subject:[/bold] {cfg.subject}")
    console.print(f"[bold]Provider:[/bold] {get_provider_name()}")
    if cfg.base_url:
        console.print(f"[bold]Base URL:[/bold] {cfg.base_url}")
    if cfg.api_key:
        # Mask the API key
        masked = cfg.api_key[:8] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 12 else "***"
        console.print(f"[bold]API Key:[/bold] {masked}")
    
    # Show available models
    console.print(f"\n[dim]Available models: {', '.join(MODELS.keys())}[/dim]")
    console.print(f"[dim]Available subjects: {', '.join(SUBJECTS)}[/dim]")
    console.print(f"[dim]Known providers: {', '.join(PROVIDERS.keys())}[/dim]")
    console.print(f"[dim]Model groups: {', '.join(MODEL_GROUPS.keys())}[/dim]")


@config.command()
@click.argument("agent_type", type=click.Choice(AGENT_TYPES + ["default"]))
@click.option("--model", "-m", help="Model to use (e.g., gpt-4o, o1-mini)")
@click.option(
    "--reasoning", "-r",
    type=click.Choice(["low", "medium", "high", "xhigh"]),
    help="Reasoning effort level"
)
@click.option("--temperature", "-t", type=float, help="Temperature (0.0-2.0)")
@click.option("--max-tokens", type=int, help="Maximum tokens")
@click.option("--workspace", "-w", is_flag=True, help="Save to workspace config instead of global")
def set(agent_type: str, model: str, reasoning: str, temperature: float, max_tokens: int, workspace: bool):
    """Set model configuration for an agent type.
    
    \b
    Arguments:
        AGENT_TYPE  Agent to configure (classifier, scanner, tikz, etc.)
    
    \b
    Examples:
        vbagent config set scanner --model gpt-4o
        vbagent config set variant --model o1-mini --reasoning medium
        vbagent config set default --model gpt-4.1
        vbagent config set scanner -m gpt-4o --workspace  # Save to .vbagent.json
    """
    from .common import print_status
    console = _get_console()
    cfg = get_config()
    
    if agent_type == "default":
        if model:
            cfg.default_model = model
        if reasoning:
            cfg.default_reasoning_effort = reasoning
        print_status(console, "Updated default configuration", "success")
    else:
        agent_cfg = getattr(cfg, agent_type)
        if model:
            agent_cfg.model = model
        if reasoning:
            agent_cfg.reasoning_effort = reasoning
        if temperature is not None:
            agent_cfg.temperature = temperature
        if max_tokens is not None:
            agent_cfg.max_tokens = max_tokens
        print_status(console, f"Updated {agent_type} configuration", "success")
    
    # Save to file
    config_path = save_config(workspace=workspace)
    
    # Show updated config
    if agent_type == "default":
        console.print(f"  Model: {cfg.default_model}")
        console.print(f"  Reasoning: {cfg.default_reasoning_effort}")
    else:
        agent_cfg = getattr(cfg, agent_type)
        console.print(f"  Model: {agent_cfg.model}")
        console.print(f"  Reasoning: {agent_cfg.reasoning_effort}")
        if agent_cfg.temperature:
            console.print(f"  Temperature: {agent_cfg.temperature}")
        if agent_cfg.max_tokens:
            console.print(f"  Max Tokens: {agent_cfg.max_tokens}")
    
    console.print(f"\n[dim]Saved to: {config_path}[/dim]")


@config.command()
@click.option("--workspace", "-w", is_flag=True, help="Reset workspace config instead of global")
def reset(workspace: bool):
    """Reset configuration to defaults."""
    from .common import print_status
    console = _get_console()
    reset_config(workspace=workspace)
    if workspace:
        print_status(console, "Workspace configuration removed", "success")
    else:
        print_status(console, "Global configuration reset to defaults", "success")


@config.command()
@click.argument("mode", type=click.Choice(["on", "off", "status"]))
@click.option("-w", "--workspace", is_flag=True, help="Save to workspace config")
def debug(mode: str, workspace: bool):
    """Enable or disable debug mode.
    
    Debug mode prints detailed input/output for all agent calls.
    
    \b
    Examples:
        vbagent config debug on          # Enable debug mode
        vbagent config debug off         # Disable debug mode
        vbagent config debug status      # Show current status
        vbagent config debug on -w       # Enable in workspace config
    """
    from .common import print_status
    console = _get_console()
    
    if mode == "status":
        cfg = get_config()
        status = "ON" if cfg.debug else "OFF"
        config_type = "workspace" if has_workspace_config() else "global"
        console.print(f"Debug mode: [{'green' if cfg.debug else 'red'}]{status}[/] ({config_type} config)")
        return
    
    cfg = get_config()
    cfg.debug = (mode == "on")
    save_config(workspace=workspace)
    
    status = "enabled" if cfg.debug else "disabled"
    config_type = "workspace" if workspace else "global"
    print_status(console, f"Debug mode {status} ({config_type} config)", "success")


@config.command()
def models():
    """List available models."""
    console = _get_console()
    console.print("[bold]Available Models:[/bold]\n")
    
    # Group models by provider
    gpt_models = [m for m in MODELS.keys() if m.startswith("gpt")]
    grok_models = [m for m in MODELS.keys() if m.startswith("grok")]
    gemini_models = [m for m in MODELS.keys() if m.startswith("gemini")]
    
    if gpt_models:
        console.print("[cyan]OpenAI:[/cyan]")
        for m in gpt_models:
            console.print(f"  • {m}")
    
    if grok_models:
        console.print("\n[cyan]xAI Grok:[/cyan]")
        for m in grok_models:
            console.print(f"  • {m}")
    
    if gemini_models:
        console.print("\n[cyan]Google Gemini:[/cyan]")
        for m in gemini_models:
            console.print(f"  • {m}")
    
    console.print(f"\n[dim]Model groups available: {', '.join(MODEL_GROUPS.keys())}[/dim]")
    console.print("[dim]Use 'vbagent config model-group' to view/apply groups[/dim]")



@config.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing workspace config")
@click.option("--quick", "-q", is_flag=True, help="Quick mode - only ask for subject")
@click.option("--yes", "-y", is_flag=True, help="Non-interactive mode with defaults")
@click.pass_context
def init(ctx, force: bool, quick: bool, yes: bool):
    """Initialize workspace config interactively.
    
    Creates .vbagent.json in current directory with customized settings.
    This is an alias for `vbagent init`.
    
    \b
    Examples:
        vbagent config init              # Interactive setup
        vbagent config init --quick      # Only ask for subject
        vbagent config init --yes        # Use all defaults
        vbagent config init --force      # Overwrite existing
    """
    # Import and invoke the main init command
    from vbagent.cli.init import init as main_init
    ctx.invoke(main_init, force=force, quick=quick, yes=yes)


@config.command()
@click.argument("subject", type=click.Choice(SUBJECTS))
@click.option("--workspace", "-w", is_flag=True, help="Set in workspace config")
def subject(subject: str, workspace: bool):
    """Set the subject for prompts.
    
    \b
    Subjects:
        physics      - Physics problems (default)
        chemistry    - Chemistry problems
        mathematics  - Mathematics problems
        biology      - Biology problems
    
    \b
    Examples:
        vbagent config subject chemistry
        vbagent config subject physics --workspace
    """
    console = _get_console()
    cfg = get_config()
    cfg.subject = subject
    config_path = save_config(workspace=workspace)
    console.print(f"[green]✓[/green] Subject set to: {subject}")
    console.print(f"[dim]Saved to: {config_path}[/dim]")



@config.command()
@click.argument("provider", required=False)
@click.option("--base-url", "-b", help="Custom base URL")
@click.option("--api-key", "-k", help="API key for the provider")
@click.option("--no-models", is_flag=True, help="Don't auto-switch agent models")
@click.option("--workspace", "-w", is_flag=True, help="Save to workspace config")
def provider(provider: str, base_url: str, api_key: str, no_models: bool, workspace: bool):
    """Set the API provider (openai, xai, google, or custom URL).
    
    Switching providers auto-applies the matching model group so every
    agent gets the right model. Use --no-models to skip this.
    
    \b
    Known Providers:
        openai  - OpenAI (default, no base_url needed)
        xai     - xAI Grok (https://api.x.ai/v1)
        google  - Google Gemini (OpenAI-compatible endpoint)
    
    \b
    Examples:
        vbagent config provider openai
        vbagent config provider xai --api-key xai-xxx
        vbagent config provider xai --workspace
        vbagent config provider xai --no-models   # keep current models
        vbagent config provider --base-url https://custom.api/v1
    """
    console = _get_console()
    cfg = get_config()
    
    resolved_provider = None
    
    if provider and provider in PROVIDERS:
        cfg.base_url = PROVIDERS[provider]["base_url"]
        resolved_provider = provider
        console.print(f"[green]✓[/green] Provider: {provider}")
        if PROVIDERS[provider]["base_url"]:
            console.print(f"  Base URL: {PROVIDERS[provider]['base_url']}")
            env_key = PROVIDERS[provider]["env_key"]
            console.print(f"  API key env var: {env_key}")
        else:
            console.print("  Base URL: [dim]default (OpenAI)[/dim]")
    elif base_url:
        cfg.base_url = base_url
        # Try to detect provider from custom URL
        from vbagent.config import _provider_from_base_url
        resolved_provider = _provider_from_base_url(base_url)
        console.print(f"[green]✓[/green] Base URL: {base_url}")
    elif provider:
        console.print(f"[yellow]Unknown provider '{provider}'[/yellow]")
        console.print(f"[dim]Known: {', '.join(PROVIDERS.keys())}[/dim]")
        console.print("[dim]Or use --base-url for custom endpoints[/dim]")
        return
    
    if api_key:
        cfg.api_key = api_key
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        console.print(f"[green]✓[/green] API Key: {masked}")
    
    # Auto-apply model group when switching providers
    if resolved_provider and not no_models and resolved_provider in MODEL_GROUPS:
        apply_model_group(cfg, resolved_provider)
        console.print(f"[green]✓[/green] Applied [bold]{resolved_provider}[/bold] model group")
        # Show the models that were set
        table = _get_table(title=f"Model Group: {resolved_provider}")
        table.add_column("Agent", style="cyan")
        table.add_column("Model", style="green")
        table.add_row("[bold]default[/bold]", cfg.default_model, style="dim")
        for agent_type in AGENT_TYPES:
            table.add_row(agent_type, getattr(cfg, agent_type).model)
        console.print(table)
    
    if not provider and not base_url and not api_key:
        # Show current provider info
        console.print(f"[bold]Current provider:[/bold] {get_provider_name()}")
        if cfg.base_url:
            console.print(f"  Base URL: {cfg.base_url}")
        if cfg.api_key:
            masked = cfg.api_key[:8] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 12 else "***"
            console.print(f"  API Key: {masked}")
        console.print(f"\n[dim]Known providers: {', '.join(PROVIDERS.keys())}[/dim]")
        console.print(f"[dim]Model groups: {', '.join(MODEL_GROUPS.keys())}[/dim]")
        return
    
    config_path = save_config(workspace=workspace)
    console.print(f"[dim]Saved to: {config_path}[/dim]")


@config.command("model-group")
@click.argument("group_name", required=False, type=click.Choice(list(MODEL_GROUPS.keys())))
@click.option("--workspace", "-w", is_flag=True, help="Save to workspace config")
def model_group(group_name: str, workspace: bool):
    """View or apply a model group.
    
    Model groups are pre-configured sets of models for each agent,
    optimized per provider. Switching providers auto-applies the
    matching group, but you can also apply one manually.
    
    \b
    Examples:
        vbagent config model-group              # List all groups
        vbagent config model-group openai       # Apply OpenAI group
        vbagent config model-group xai          # Apply xAI group
        vbagent config model-group google -w    # Apply Google group to workspace
    """
    console = _get_console()
    
    if not group_name:
        # Show all model groups
        for name, group in MODEL_GROUPS.items():
            table = _get_table(title=f"Model Group: {name}")
            table.add_column("Agent", style="cyan")
            table.add_column("Model", style="green")
            table.add_row("[bold]default[/bold]", group["default_model"], style="dim")
            for agent_type in AGENT_TYPES:
                if agent_type in group:
                    table.add_row(agent_type, group[agent_type])
            console.print(table)
            console.print()
        return
    
    cfg = get_config()
    apply_model_group(cfg, group_name)
    config_path = save_config(workspace=workspace)
    
    console.print(f"[green]✓[/green] Applied [bold]{group_name}[/bold] model group")
    if cfg.base_url:
        console.print(f"  Base URL: {cfg.base_url}")
    else:
        console.print("  Base URL: [dim]default (OpenAI)[/dim]")
    table = _get_table(title=f"Model Group: {group_name}")
    table.add_column("Agent", style="cyan")
    table.add_column("Model", style="green")
    table.add_row("[bold]default[/bold]", cfg.default_model, style="dim")
    for agent_type in AGENT_TYPES:
        table.add_row(agent_type, getattr(cfg, agent_type).model)
    console.print(table)
    console.print(f"[dim]Saved to: {config_path}[/dim]")
