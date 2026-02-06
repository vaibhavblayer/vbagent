"""CLI command for initializing workspace config.

Shortcut for `vbagent config init`.
"""

import click
import os

from vbagent.config import (
    init_workspace,
    SUBJECTS,
    MODELS,
    AGENT_TYPES,
    PROVIDERS,
    VBAgentConfig,
    AgentModelConfig,
    WORKSPACE_CONFIG_FILE,
)
from pathlib import Path


def _get_console():
    """Lazy import of rich Console."""
    from rich.console import Console
    return Console()


def _get_prompt():
    """Lazy import of rich Prompt."""
    from rich.prompt import Prompt, IntPrompt
    return Prompt, IntPrompt


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _select_from_list(console, title: str, options: list[str], default: str) -> str:
    """Interactive selection from a list of options.
    
    Args:
        console: Rich console instance
        title: Title to display
        options: List of options
        default: Default option
        
    Returns:
        Selected option
    """
    Prompt, IntPrompt = _get_prompt()
    
    default_idx = options.index(default) + 1 if default in options else 1
    
    console.print(f"\n[bold cyan]{title}[/bold cyan] [dim](default: {default})[/dim]")
    for i, opt in enumerate(options, 1):
        marker = "[green]→[/green]" if opt == default else " "
        console.print(f"  {marker} {i}. {opt.title()}")
    
    choice = Prompt.ask(
        "\n[dim]Enter number or press Enter for default[/dim]",
        default=str(default_idx),
    )
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass
    
    return default


def _select_model(console, agent_type: str, current: str) -> str:
    """Interactive model selection."""
    Prompt, _ = _get_prompt()
    
    model_list = list(MODELS.keys())
    default_idx = model_list.index(current) + 1 if current in model_list else 1
    
    console.print(f"\n[bold cyan]Model for {agent_type}[/bold cyan] [dim](default: {current})[/dim]")
    for i, model in enumerate(model_list, 1):
        marker = "[green]→[/green]" if model == current else " "
        console.print(f"  {marker} {i}. {model}")
    
    choice = Prompt.ask(
        "\n[dim]Enter number or press Enter for default[/dim]",
        default=str(default_idx),
    )
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(model_list):
            return model_list[idx]
    except ValueError:
        pass
    
    return current


def _select_reasoning(console, agent_type: str, current: str) -> str:
    """Interactive reasoning effort selection."""
    options = ["low", "medium", "high", "xhigh"]
    return _select_from_list(console, f"Reasoning effort for {agent_type}", options, current)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--force", "-f", is_flag=True, help="Overwrite existing workspace config")
@click.option("--quick", "-q", is_flag=True, help="Quick mode - only ask for subject")
@click.option("--yes", "-y", is_flag=True, help="Non-interactive mode with defaults")
def init(force: bool, quick: bool, yes: bool):
    """Initialize workspace config interactively.
    
    Creates .vbagent.json in current directory with customized settings.
    
    \b
    Examples:
        vbagent init              # Interactive setup
        vbagent init --quick      # Only ask for subject
        vbagent init --yes        # Use all defaults (non-interactive)
        vbagent init --force      # Overwrite existing config
    
    \b
    The workspace config allows you to:
        - Use different models per workspace
        - Set subject-specific prompts (physics, chemistry, etc.)
        - Override reasoning effort and other settings
    
    \b
    Config hierarchy:
        1. Global config (~/.config/vbagent/models.json)
        2. Workspace config (.vbagent.json) - overrides global
    """
    console = _get_console()
    Prompt, _ = _get_prompt()
    
    # Check if config already exists
    workspace_config = Path.cwd() / WORKSPACE_CONFIG_FILE
    if workspace_config.exists() and not force:
        console.print(f"[yellow]⚠[/yellow] Workspace config already exists: {workspace_config}")
        if not yes:
            overwrite = Prompt.ask(
                "Overwrite?",
                choices=["y", "n"],
                default="n",
            )
            if overwrite.lower() != "y":
                console.print("[dim]Cancelled[/dim]")
                raise SystemExit(0)
    
    console.print("\n[bold]🚀 VBAgent Workspace Setup[/bold]\n")
    console.print("[dim]Configure your workspace settings. Press Enter to accept defaults.[/dim]")
    
    # Load global config as base
    config = VBAgentConfig.load_global()
    
    # === Subject Selection ===
    if yes:
        subject = "physics"
    else:
        subject = _select_from_list(
            console,
            "Select Subject",
            SUBJECTS,
            config.subject,
        )
    config.subject = subject
    console.print(f"[green]✓[/green] Subject: {subject}")
    
    if not quick and not yes:
        # === Provider Selection ===
        provider_names = list(PROVIDERS.keys())
        current_provider = "openai"
        if config.base_url:
            for name, info in PROVIDERS.items():
                if info["base_url"] and config.base_url.rstrip("/") == info["base_url"].rstrip("/"):
                    current_provider = name
                    break
        
        selected_provider = _select_from_list(
            console,
            "Select Provider",
            provider_names,
            current_provider,
        )
        config.base_url = PROVIDERS[selected_provider]["base_url"]
        console.print(f"[green]✓[/green] Provider: {selected_provider}")
        
        # Ask for API key if non-OpenAI provider
        if selected_provider != "openai":
            env_key = PROVIDERS[selected_provider]["env_key"]
            has_env = os.environ.get(env_key)
            
            if has_env:
                console.print(f"[dim]  Found {env_key} in environment[/dim]")
            else:
                Prompt, _ = _get_prompt()
                api_key = Prompt.ask(
                    f"\n[cyan]API key for {selected_provider}[/cyan] [dim](Enter to skip, set {env_key} env var)[/dim]",
                    default="",
                    password=True,
                )
                if api_key:
                    config.api_key = api_key
                    console.print(f"[green]✓[/green] API key set")
                else:
                    console.print(f"[yellow]  ⚠ No API key set. Set {env_key} in your environment[/yellow]")
        
        # === Default Model ===
        console.print("\n[bold]─── Default Settings ───[/bold]")
        
        config.default_model = _select_model(console, "default", config.default_model)
        console.print(f"[green]✓[/green] Default model: {config.default_model}")
        
        config.default_reasoning_effort = _select_reasoning(console, "default", config.default_reasoning_effort)
        console.print(f"[green]✓[/green] Default reasoning: {config.default_reasoning_effort}")
        
        # === Per-Agent Configuration ===
        customize_agents = Prompt.ask(
            "\n[cyan]Customize individual agent settings?[/cyan]",
            choices=["y", "n"],
            default="n",
        )
        
        if customize_agents.lower() == "y":
            console.print("\n[bold]─── Agent Settings ───[/bold]")
            console.print("[dim]Configure each agent or press Enter to use defaults[/dim]")
            
            for agent_type in AGENT_TYPES:
                agent_cfg = getattr(config, agent_type)
                
                console.print(f"\n[bold cyan]{agent_type.upper()}[/bold cyan]")
                
                # Model
                agent_cfg.model = _select_model(console, agent_type, agent_cfg.model)
                
                # Reasoning
                agent_cfg.reasoning_effort = _select_reasoning(console, agent_type, agent_cfg.reasoning_effort)
                
                console.print(f"[green]✓[/green] {agent_type}: {agent_cfg.model} ({agent_cfg.reasoning_effort})")
    
    # === Save Config ===
    config_path = config.save(workspace=True)
    
    console.print(f"\n[bold green]✓ Workspace initialized![/bold green]")
    console.print(f"  Config: {config_path}")
    console.print(f"  Subject: {config.subject}")
    console.print(f"  Default model: {config.default_model}")
    console.print(f"\n[dim]Edit .vbagent.json to further customize settings[/dim]")
