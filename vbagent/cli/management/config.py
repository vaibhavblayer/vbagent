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
from ..common import _get_console, _get_table


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
        console.print(f"[#6b7280]Using workspace config: {workspace_path}[/]\n")
    else:
        console.print(f"[#6b7280]Using global config: {CONFIG_FILE}[/]\n")

    # Create table using new category table helper
    from vbagent.ui.tables import create_category_table, add_category_row

    table = create_category_table(
        title="Agent Model Configuration",
        columns=["Category", "Agent", "Model", "Reasoning", "Max Tokens"],
        caption=f"subject={cfg.subject}  provider={get_provider_name()}  debug={'on' if cfg.debug else 'off'}",
    )

    # Global default
    add_category_row(table, "global", [
        "[bold]default[/]",
        cfg.default_model,
        cfg.default_reasoning_effort,
        "-",
    ], is_header=True)

    # Agent categories
    categories = [
        ("classification", ["image_classifier", "diagram_analyzer", "difficulty_assessor", "latex_classifier", "taxonomy_classifier"]),
        ("content_generation", ["scanner", "idea", "alternate", "converter"]),
        ("diagram", ["tikz", "fbd", "tikz_checker"]),
        ("variants", ["variant", "multi_context"]),
        ("quality", ["reviewer", "solution_checker", "grammar_checker", "clarity_checker", "latex_fixer"]),
    ]

    for cat_key, agent_names in categories:
        cat_cfg = getattr(cfg, cat_key, None)
        if not cat_cfg:
            continue
        first = True
        for agent_name in agent_names:
            agent_cfg = getattr(cat_cfg, agent_name, None)
            if agent_cfg:
                add_category_row(table, cat_key, [
                    agent_name,
                    agent_cfg.model,
                    agent_cfg.reasoning_effort,
                    str(agent_cfg.max_tokens) if agent_cfg.max_tokens else "-",
                ], is_header=first)
                first = False

    console.print(table)

    # Extra info
    if cfg.base_url:
        console.print(f"\n[bold #5eead4]Base URL:[/] {cfg.base_url}")
    if cfg.api_key:
        masked = cfg.api_key[:8] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 12 else "***"
        console.print(f"[bold #5eead4]API Key:[/] {masked}")

    console.print(f"\n[#6b7280]Models: {', '.join(MODELS.keys())}[/]")
    console.print(f"[#6b7280]Subjects: {', '.join(SUBJECTS)}  |  Providers: {', '.join(PROVIDERS.keys())}  |  Groups: {', '.join(MODEL_GROUPS.keys())}[/]")
    console.print(f"[#6b7280]Tip: Use paths like 'content_generation.scanner' or flat 'scanner'[/]")


@config.command()
@click.argument("agent_type")
@click.option("--model", "-m", help="Model to use (e.g., gpt-4o, o1-mini)")
@click.option(
    "--reasoning", "-r",
    type=click.Choice(["low", "medium", "high", "xhigh"]),
    help="Reasoning effort level"
)
@click.option("--max-tokens", type=int, help="Maximum tokens")
@click.option("--workspace", "-w", is_flag=True, help="Save to workspace config instead of global")
def set(agent_type: str, model: str, reasoning: str, max_tokens: int, workspace: bool):
    """Set model configuration for an agent type.
    
    Supports both flat and hierarchical paths:
    - Flat: scanner, tikz, reviewer
    - Hierarchical: content_generation.scanner, diagram.tikz, quality.reviewer
    
    \b
    Arguments:
        AGENT_TYPE  Agent to configure (supports hierarchical paths)
    
    \b
    Examples:
        vbagent config set scanner --model gpt-4o
        vbagent config set content_generation.scanner --model gpt-4o
        vbagent config set diagram.tikz --model o1-mini --reasoning medium
        vbagent config set default --model gpt-4.1
        vbagent config set scanner -m gpt-4o --workspace  # Save to .vbagent.json
    """
    from vbagent.cli.interfaces.ui import print_status
    console = _get_console()
    cfg = get_config()
    
    if agent_type == "default":
        if model:
            cfg.default_model = model
        if reasoning:
            cfg.default_reasoning_effort = reasoning
        print_status(console, "Updated default configuration", "success")
    else:
        # Support hierarchical paths (e.g., "content_generation.scanner")
        if "." in agent_type:
            category, agent_name = agent_type.split(".", 1)
            category_config = getattr(cfg, category, None)
            if not category_config:
                console.print(f"[red]Error:[/red] Unknown category '{category}'")
                console.print(f"[dim]Valid categories: classification, content_generation, diagram, variants, quality[/dim]")
                return
            agent_cfg = getattr(category_config, agent_name, None)
            if not agent_cfg:
                console.print(f"[red]Error:[/red] Unknown agent '{agent_name}' in category '{category}'")
                return
        else:
            # Flat path (backward compatibility)
            agent_cfg = getattr(cfg, agent_type, None)
            if not agent_cfg or not isinstance(agent_cfg, type(cfg.scanner)):
                console.print(f"[red]Error:[/red] Unknown agent type '{agent_type}'")
                console.print(f"[dim]Valid flat paths: {', '.join(AGENT_TYPES)}[/dim]")
                console.print(f"[dim]Or use hierarchical paths like 'content_generation.scanner'[/dim]")
                return
            
            # Also update hierarchical config for consistency
            # Map flat names to hierarchical paths
            hierarchical_map = {
                # Classification
                "classifier": ("classification", "image_classifier"),
                "taxonomy_classifier": ("classification", "taxonomy_classifier"),
                "difficulty_assessor": ("classification", "difficulty_assessor"),
                # Content Generation
                "scanner": ("content_generation", "scanner"),
                "idea": ("content_generation", "idea"),
                "alternate": ("content_generation", "alternate"),
                "converter": ("content_generation", "converter"),
                # Diagram
                "tikz": ("diagram", "tikz"),
                "fbd": ("diagram", "fbd"),
                "tikz_checker": ("diagram", "tikz_checker"),
                # Variants
                "variant": ("variants", "variant"),
                # Quality
                "reviewer": ("quality", "reviewer"),
                "solution_checker": ("quality", "solution_checker"),
                "grammar_checker": ("quality", "grammar_checker"),
                "clarity_checker": ("quality", "clarity_checker"),
                "latex_fixer": ("quality", "latex_fixer"),
                "format_checker": ("quality", "format_checker"),
            }
            
            if agent_type in hierarchical_map:
                category, agent_name = hierarchical_map[agent_type]
                category_config = getattr(cfg, category, None)
                if category_config:
                    hierarchical_agent_cfg = getattr(category_config, agent_name, None)
                    if hierarchical_agent_cfg:
                        # Update both flat and hierarchical configs
                        if model:
                            agent_cfg.model = model
                            hierarchical_agent_cfg.model = model
                        if reasoning:
                            agent_cfg.reasoning_effort = reasoning
                            hierarchical_agent_cfg.reasoning_effort = reasoning
                        if max_tokens is not None:
                            agent_cfg.max_tokens = max_tokens
                            hierarchical_agent_cfg.max_tokens = max_tokens
                        print_status(console, f"Updated {agent_type} configuration", "success")
                        # Skip the normal update below
                        agent_cfg = None
        
        # Normal update (for hierarchical paths or if flat path didn't match)
        if agent_cfg:
            if model:
                agent_cfg.model = model
            if reasoning:
                agent_cfg.reasoning_effort = reasoning
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
        # Get the config to display (prefer hierarchical if available)
        display_cfg = agent_cfg
        if not display_cfg and "." not in agent_type:
            # For flat paths that were synced, get from hierarchical
            hierarchical_map = {
                "classifier": ("classification", "image_classifier"),
                "taxonomy_classifier": ("classification", "taxonomy_classifier"),
                "difficulty_assessor": ("classification", "difficulty_assessor"),
                "scanner": ("content_generation", "scanner"),
                "idea": ("content_generation", "idea"),
                "alternate": ("content_generation", "alternate"),
                "converter": ("content_generation", "converter"),
                "tikz": ("diagram", "tikz"),
                "fbd": ("diagram", "fbd"),
                "tikz_checker": ("diagram", "tikz_checker"),
                "variant": ("variants", "variant"),
                "reviewer": ("quality", "reviewer"),
                "solution_checker": ("quality", "solution_checker"),
                "grammar_checker": ("quality", "grammar_checker"),
                "clarity_checker": ("quality", "clarity_checker"),
                "latex_fixer": ("quality", "latex_fixer"),
                "format_checker": ("quality", "format_checker"),
            }
            if agent_type in hierarchical_map:
                category, agent_name = hierarchical_map[agent_type]
                category_config = getattr(cfg, category, None)
                if category_config:
                    display_cfg = getattr(category_config, agent_name, None)
        
        if display_cfg:
            console.print(f"  Model: {display_cfg.model}")
            console.print(f"  Reasoning: {display_cfg.reasoning_effort}")
            if display_cfg.max_tokens:
                console.print(f"  Max Tokens: {display_cfg.max_tokens}")
    
    console.print(f"\n[dim]Saved to: {config_path}[/dim]")


@config.command()
@click.option("--workspace", "-w", is_flag=True, help="Reset workspace config instead of global")
def reset(workspace: bool):
    """Reset configuration to defaults."""
    from vbagent.cli.interfaces.ui import print_status
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
    from vbagent.cli.interfaces.ui import print_status
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


@config.command("log-level")
@click.argument("level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "status"], case_sensitive=False))
@click.option("-w", "--workspace", is_flag=True, help="Save to workspace config")
def log_level(level: str, workspace: bool):
    """Set logging level for agent operations.
    
    Controls the verbosity of logging output.
    
    \b
    Levels:
        DEBUG    - Detailed debug information
        INFO     - General informational messages (default)
        WARNING  - Warning messages only
        ERROR    - Error messages only
        CRITICAL - Critical errors only
    
    \b
    Examples:
        vbagent config log-level DEBUG       # Enable debug logging
        vbagent config log-level INFO        # Set to info level
        vbagent config log-level status      # Show current level
        vbagent config log-level DEBUG -w    # Set in workspace config
    """
    from vbagent.cli.interfaces.ui import print_status
    console = _get_console()
    
    if level.lower() == "status":
        cfg = get_config()
        config_type = "workspace" if has_workspace_config() else "global"
        console.print(f"Log level: [cyan]{cfg.log_level}[/] ({config_type} config)")
        return
    
    cfg = get_config()
    cfg.log_level = level.upper()
    save_config(workspace=workspace)
    
    config_type = "workspace" if workspace else "global"
    print_status(console, f"Log level set to {level.upper()} ({config_type} config)", "success")


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
