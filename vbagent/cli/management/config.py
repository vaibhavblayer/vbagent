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
    MODELS,
    MODEL_GROUPS,
    AGENT_GROUPS,
    AGENT_TYPES,
    SUBJECTS,
    PROVIDERS,
    CONFIG_FILE,
    WORKSPACE_CONFIG_FILE,
)
from ..common import _get_console, _get_table


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def config():
    """Configure models, providers, and pipeline settings.

    \b
    Quick Start:
        vbagent config show                  View current config
        vbagent config set tikz -m gpt-5.4   Set model for an agent
        vbagent config provider xai           Switch provider
        vbagent config subject chemistry      Change subject

    \b
    Config Files:
        Global:    ~/.config/vbagent/models.json
        Workspace: .vbagent.json (overrides global)

    \b
    Agent Groups:
        Classification   classifier, diagram_analyzer, ...
        Extraction       scanner, converter
        Diagram          tikz, fbd, circuit, graph, optics, ...
        Generation       idea, alternate, variant, solution
        Quality          reviewer, solution_checker, format_checker, ...

    \b
    Use -w/--workspace on any set/provider/subject command to save
    to .vbagent.json instead of the global config.
    """
    pass


@config.command()
@click.option("--compact", "-c", is_flag=True, help="Compact one-line-per-group summary")
def show(compact):
    """Show current model configuration for all agents.

    \b
    Examples:
        vbagent config show            Full grouped table
        vbagent config show --compact  One-line summary per group
    """
    console = _get_console()
    cfg = get_config()

    # Show config source
    workspace_path = get_workspace_config_path()
    if workspace_path:
        console.print(f"[#6b7280]workspace: {workspace_path}[/]")
    else:
        console.print(f"[#6b7280]global: {CONFIG_FILE}[/]")

    console.print(f"[dim]subject={cfg.subject}  provider={get_provider_name()}  "
                  f"default_model={cfg.default_model}  reasoning={cfg.default_reasoning_effort}  "
                  f"debug={'on' if cfg.debug else 'off'}[/dim]")
    if cfg.single_model:
        console.print(f"[bold cyan]single_model={cfg.single_model}[/bold cyan] (all agents use this model)")
    console.print()

    if compact:
        # Compact: one line per group showing model(s) used
        for group_name, agent_names in AGENT_GROUPS.items():
            models_in_group = set()
            for name in agent_names:
                ac = cfg.get_agent_config(name)
                models_in_group.add(f"{ac.model}/{ac.reasoning_effort}")
            models_str = ", ".join(sorted(models_in_group))
            console.print(f"  [cyan]{group_name:<22}[/cyan] {models_str}")
        return

    # Full grouped table
    for group_name, agent_names in AGENT_GROUPS.items():
        table = _get_table(title=group_name)
        table.add_column("Agent", style="cyan", min_width=22)
        table.add_column("Model", style="green")
        table.add_column("Reasoning", style="yellow")
        table.add_column("Max Tokens", style="magenta")

        for name in agent_names:
            ac = cfg.get_agent_config(name)
            # Dim rows that match defaults exactly
            is_default = (ac.model == cfg.default_model and
                          ac.reasoning_effort == cfg.default_reasoning_effort and
                          ac.max_tokens is None)
            style = "dim" if is_default else ""
            table.add_row(
                name, ac.model, ac.reasoning_effort,
                str(ac.max_tokens) if ac.max_tokens else "-",
                style=style,
            )
        console.print(table)

    # Extra info
    if cfg.base_url:
        console.print(f"\n[bold #5eead4]Base URL:[/] {cfg.base_url}")
    if cfg.api_key:
        masked = cfg.api_key[:8] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 12 else "***"
        console.print(f"[bold #5eead4]API Key:[/] {masked}")


@config.command("set")
@click.argument("agent_type")
@click.option("--model", "-m", help="Model to use (e.g., gpt-5.4, gpt-5.4-mini)")
@click.option(
    "--reasoning", "-r",
    type=click.Choice(["low", "medium", "high", "xhigh"]),
    help="Reasoning effort level"
)
@click.option("--max-tokens", type=int, help="Maximum tokens")
@click.option("--workspace", "-w", is_flag=True, help="Save to workspace config instead of global")
def set_agent(agent_type: str, model: str, reasoning: str, max_tokens: int, workspace: bool):
    """Set model configuration for an agent type.
    
    \b
    Arguments:
        AGENT_TYPE  Agent to configure (or 'default' for global defaults)
    
    \b
    Agent Types (by group):
        Classification:  classifier, diagram_analyzer, taxonomy_classifier, ...
        Extraction:      scanner, converter
        Diagram:         tikz, fbd, circuit, graph, optics, organic_structure, ...
        Generation:      idea, alternate, variant, solution
        Quality:         reviewer, solution_checker, format_checker, ...
    
    \b
    Examples:
        vbagent config set default -m gpt-5.4-mini          Global default
        vbagent config set classifier -m gpt-5.4-mini -r low   Classification
        vbagent config set scanner -m gpt-5.4-mini -r medium   Extraction
        vbagent config set tikz -m gpt-5.4 -r high             Diagram
        vbagent config set circuit -m gpt-5.4 -r high          Diagram (specialist)
        vbagent config set idea -m gpt-5.4 -r high             Generation
        vbagent config set alternate -m gpt-5.4 -r high        Generation
        vbagent config set solution -m gpt-5.4 -r high         Generation
        vbagent config set variant -m gpt-5.4 -r high          Generation
        vbagent config set format_checker -m gpt-5.4-mini      Quality
        vbagent config set scanner -m gpt-5.4 -w               Save to workspace
    """
    from vbagent.cli.interfaces.ui import print_status
    from vbagent.config import AgentModelConfig
    console = _get_console()
    cfg = get_config()
    
    if agent_type == "default":
        if model:
            cfg.default_model = model
        if reasoning:
            cfg.default_reasoning_effort = reasoning
        print_status(console, "Updated default configuration", "success")
    else:
        # Get or create agent config
        if agent_type not in cfg.agents:
            cfg.agents[agent_type] = AgentModelConfig(
                model=cfg.default_model,
                reasoning_effort=cfg.default_reasoning_effort
            )
        
        agent_cfg = cfg.agents[agent_type]
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
        agent_cfg = cfg.agents[agent_type]
        console.print(f"  Model: {agent_cfg.model}")
        console.print(f"  Reasoning: {agent_cfg.reasoning_effort}")
        if agent_cfg.max_tokens:
            console.print(f"  Max Tokens: {agent_cfg.max_tokens}")
    
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
    """List available models and agent types.

    \b
    Examples:
        vbagent config models
    """
    console = _get_console()

    # Group models by provider
    gpt_models = [m for m in MODELS.keys() if m.startswith("gpt")]
    grok_models = [m for m in MODELS.keys() if m.startswith("grok")]
    gemini_models = [m for m in MODELS.keys() if m.startswith("gemini")]

    console.print("[bold]Models[/bold]\n")
    if gpt_models:
        console.print("[cyan]OpenAI:[/cyan]  " + ", ".join(gpt_models))
    if grok_models:
        console.print("[cyan]xAI:[/cyan]     " + ", ".join(grok_models))
    if gemini_models:
        console.print("[cyan]Google:[/cyan]  " + ", ".join(gemini_models))

    console.print("\n[bold]Agent Types[/bold]\n")
    for group_name, agents in AGENT_GROUPS.items():
        console.print(f"  [cyan]{group_name}:[/cyan] {', '.join(agents)}")

    console.print(f"\n[dim]Providers: {', '.join(PROVIDERS.keys())}  |  "
                  f"Model groups: {', '.join(MODEL_GROUPS.keys())}[/dim]")



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


@config.command("set-model")
@click.argument("model")
@click.option("--workspace", "-w", is_flag=True, help="Save to workspace config")
def set_model(model: str, workspace: bool):
    """Set a single model for ALL agents, or revert to auto (two-tier).

    In single-model mode every agent uses the same model while
    per-category reasoning effort tiers are preserved (low for
    classifiers, medium for scanner, high for diagrams/solutions).

    Use 'auto' to clear single-model mode and revert to the normal
    two-tier split (mini for classification/QA, full for generation).

    \b
    Examples:
        vbagent config set-model gpt-5.4       # Everything uses gpt-5.4
        vbagent config set-model gpt-5.4-mini  # Everything uses mini
        vbagent config set-model auto           # Revert to two-tier
        vbagent config set-model gpt-5.4 -w    # Workspace only
    """
    from vbagent.config import AgentModelConfig, set_config, AGENT_GROUPS
    console = _get_console()
    cfg = get_config()

    if model.lower() == "auto":
        cfg.single_model = None
        config_path = save_config(workspace=workspace)
        console.print("[green]✓[/green] Single-model mode [bold]off[/bold] — using two-tier defaults")
        heavy = cfg.default_model.replace("-mini", "") if "-mini" in cfg.default_model else cfg.default_model
        console.print(f"  light: {cfg.default_model}  heavy: {heavy}")
    else:
        cfg.single_model = model
        # Re-apply reasoning tiers with the new single model so
        # agents dict reflects the change immediately.
        cfg.agents.clear()
        cfg._apply_reasoning_tiers(light=model, heavy=model)
        config_path = save_config(workspace=workspace)
        console.print(f"[green]✓[/green] Single-model mode [bold]on[/bold] — all agents use [cyan]{model}[/cyan]")
        # Show reasoning tiers
        tiers: dict[str, list[str]] = {}
        for group_name, agent_names in AGENT_GROUPS.items():
            for name in agent_names:
                ac = cfg.get_agent_config(name)
                tiers.setdefault(ac.reasoning_effort, []).append(name)
        for effort in ["low", "medium", "high"]:
            if effort in tiers:
                console.print(f"  {effort}: {', '.join(tiers[effort][:6])}"
                              + (f" +{len(tiers[effort])-6} more" if len(tiers[effort]) > 6 else ""))

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
        for agent_type, agent_cfg in cfg.agents.items():
            table.add_row(agent_type, agent_cfg.model)
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
            for agent_type, model in group.items():
                if agent_type != "default_model":
                    table.add_row(agent_type, model)
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
    for agent_type, agent_cfg in cfg.agents.items():
        table.add_row(agent_type, agent_cfg.model)
    console.print(table)
    console.print(f"[dim]Saved to: {config_path}[/dim]")
