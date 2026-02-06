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
    AGENT_TYPES,
    MODELS,
    SUBJECTS,
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
    
    # Show subject
    console.print(f"\n[bold]Subject:[/bold] {cfg.subject}")
    
    # Show available models
    console.print(f"\n[dim]Available models: {', '.join(MODELS.keys())}[/dim]")
    console.print(f"[dim]Available subjects: {', '.join(SUBJECTS)}[/dim]")


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
    console = _get_console()
    cfg = get_config()
    
    if agent_type == "default":
        if model:
            cfg.default_model = model
        if reasoning:
            cfg.default_reasoning_effort = reasoning
        console.print(f"[green]✓[/green] Updated default configuration")
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
        console.print(f"[green]✓[/green] Updated {agent_type} configuration")
    
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
    console = _get_console()
    reset_config(workspace=workspace)
    if workspace:
        console.print("[green]✓[/green] Workspace configuration removed")
    else:
        console.print("[green]✓[/green] Global configuration reset to defaults")


@config.command()
def models():
    """List available models."""
    console = _get_console()
    console.print("[bold]Available Models:[/bold]\n")
    
    # Group models
    gpt_models = [m for m in MODELS.keys() if m.startswith("gpt")]
    o_models = [m for m in MODELS.keys() if m.startswith("o")]
    
    console.print("[cyan]GPT Models:[/cyan]")
    for m in gpt_models:
        console.print(f"  • {m}")
    
    console.print("\n[cyan]Reasoning Models (o-series):[/cyan]")
    for m in o_models:
        console.print(f"  • {m}")



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
