"""CLI commands for API key management."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from vbagent.api_keys import KeyManager


def _format_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def _resolve_key(manager: KeyManager, identifier: str) -> str:
    """Resolve a key identifier (name or 1-based serial number) to a key name.

    Args:
        manager: KeyManager instance
        identifier: Key name or serial number (e.g. "3" or "Vaibhav Blayer")

    Returns:
        Resolved key name

    Raises:
        click.BadParameter if not found
    """
    if not manager.is_enabled() or not manager.config:
        raise click.BadParameter("Key manager not configured")

    # Try as serial number first
    if identifier.isdigit():
        idx = int(identifier) - 1
        if 0 <= idx < len(manager.config.keys):
            return manager.config.keys[idx].name
        raise click.BadParameter(
            f"Serial number {identifier} out of range (1–{len(manager.config.keys)})"
        )

    # Try as name (case-insensitive partial match)
    identifier_lower = identifier.lower()
    matches = []
    for key in manager.config.keys:
        if key.name.lower() == identifier_lower:
            return key.name  # Exact match
        if identifier_lower in key.name.lower():
            matches.append(key.name)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise click.BadParameter(
            f"Ambiguous: '{identifier}' matches {', '.join(matches)}"
        )

    raise click.BadParameter(
        f"Key '{identifier}' not found. Use 'vbagent keys list' to see available keys."
    )


def _resolve_multiple(manager: KeyManager, identifiers: tuple[str, ...]) -> list[str]:
    """Resolve multiple key identifiers."""
    return [_resolve_key(manager, ident) for ident in identifiers]


@click.group()
def keys():
    """Manage API keys with usage tracking and rotation."""
    pass


@keys.command()
def list():
    """List all API keys with usage statistics."""
    console = Console()
    manager = KeyManager.get_instance()

    if not manager.is_enabled():
        console.print("[yellow]API key manager not configured.[/yellow]")
        console.print(f"\nTo enable, create: [cyan]{manager._config_path}[/cyan]")
        console.print("Or run: [cyan]vbagent keys init[/cyan]")
        return

    summary = manager.get_usage_summary()

    if not summary:
        console.print("[yellow]No API keys configured.[/yellow]")
        return

    # Calculate totals per category
    totals = {
        "standard": {"used": 0, "limit": 0},
        "mini": {"used": 0, "limit": 0},
    }

    for key_name, data in summary.items():
        if data["enabled"]:
            for category, stats in data["categories"].items():
                if category in totals:
                    totals[category]["used"] += stats["used"]
                    totals[category]["limit"] += stats["limit"]

    # Create table
    table = Table(title="API Key Usage", show_lines=True)
    table.add_column("#", style="dim", justify="right", width=3)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Used", justify="right")
    table.add_column("Limit", justify="right")
    table.add_column("Remaining", justify="right")
    table.add_column("Usage %", justify="right")
    table.add_column("Status", justify="center")

    for serial, (key_name, data) in enumerate(summary.items(), 1):
        enabled = data["enabled"]
        status = "[green]✓[/green]" if enabled else "[red]✗[/red]"

        for idx, (category, stats) in enumerate(data["categories"].items()):
            used = _format_tokens(stats["used"])
            limit = _format_tokens(stats["limit"])
            remaining = _format_tokens(stats["remaining"])
            percentage = stats["percentage"]

            if percentage >= 90:
                usage_color = "red"
            elif percentage >= 70:
                usage_color = "yellow"
            else:
                usage_color = "green"

            usage_str = f"[{usage_color}]{percentage:.1f}%[/{usage_color}]"

            serial_display = str(serial) if idx == 0 else ""
            key_display = key_name if idx == 0 else ""
            status_display = status if idx == 0 else ""

            table.add_row(
                serial_display, key_display, category,
                used, limit, remaining, usage_str, status_display,
            )

    # Totals
    table.add_section()
    for category in ["standard", "mini"]:
        total_used = totals[category]["used"]
        total_limit = totals[category]["limit"]
        total_remaining = total_limit - total_used
        total_percentage = (total_used / total_limit * 100) if total_limit > 0 else 0

        if total_percentage >= 90:
            usage_color = "red"
        elif total_percentage >= 70:
            usage_color = "yellow"
        else:
            usage_color = "green"

        usage_str = f"[{usage_color}]{total_percentage:.1f}%[/{usage_color}]"
        key_display = "[bold]TOTAL (enabled)[/bold]" if category == "standard" else ""

        table.add_row(
            "", key_display, category,
            _format_tokens(total_used), _format_tokens(total_limit),
            _format_tokens(total_remaining), usage_str, "",
        )

    console.print(table)

    if manager.config:
        console.print(f"\n[dim]Rotation strategy: {manager.config.rotation_strategy}[/dim]")
        console.print("[dim]Tip: Use serial # or partial name for enable/disable (e.g. 'vbagent keys enable 3')[/dim]")


@keys.command()
@click.option("--name", required=True, help="Friendly name for the key")
@click.option("--api-key", required=True, help="OpenAI API key")
@click.option("--standard-limit", type=int, default=1_000_000, help="Daily token limit for standard models")
@click.option("--mini-limit", type=int, default=2_000_000, help="Daily token limit for mini models")
def add(name: str, api_key: str, standard_limit: int, mini_limit: int):
    """Add a new API key."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        manager.add_key(name, api_key, standard_limit, mini_limit)
        console.print(f"[green]✓[/green] Added key '[cyan]{name}[/cyan]'")
        console.print(f"  Standard limit: {_format_tokens(standard_limit)} tokens/day")
        console.print(f"  Mini limit: {_format_tokens(mini_limit)} tokens/day")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("identifier")
@click.option("--standard-limit", type=int, help="New daily limit for standard models")
@click.option("--mini-limit", type=int, help="New daily limit for mini models")
def update(identifier: str, standard_limit: int, mini_limit: int):
    """Update limits for a key. Use name or serial number."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        name = _resolve_key(manager, identifier)
        manager.update_limits(name, standard_limit, mini_limit)
        console.print(f"[green]✓[/green] Updated limits for '[cyan]{name}[/cyan]'")
        if standard_limit:
            console.print(f"  Standard limit: {_format_tokens(standard_limit)} tokens/day")
        if mini_limit:
            console.print(f"  Mini limit: {_format_tokens(mini_limit)} tokens/day")
    except (ValueError, RuntimeError, click.BadParameter) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("identifiers", nargs=-1, required=False)
@click.option("--only", is_flag=True, help="Enable ONLY these keys, disable all others")
@click.option("--all", "enable_all", is_flag=True, help="Enable all keys")
def enable(identifiers: tuple[str, ...], only: bool, enable_all: bool):
    """Enable API key(s). Use name or serial number.

    \b
    Examples:
        vbagent keys enable 4                    # Enable key #4
        vbagent keys enable "Vaibhav Blayer"     # Enable by name
        vbagent keys enable vaibhav              # Partial name match
        vbagent keys enable 4 --only             # Enable #4, disable all others
        vbagent keys enable 1 3 --only           # Enable #1 and #3 only
        vbagent keys enable --all                # Enable all keys
    """
    console = Console()
    manager = KeyManager.get_instance()

    if not manager.is_enabled():
        console.print("[yellow]Key manager not configured.[/yellow]")
        return

    try:
        if enable_all:
            for key in manager.config.keys:
                manager.enable_key(key.name)
            console.print(f"[green]✓[/green] Enabled all {len(manager.config.keys)} keys")
            return

        if not identifiers:
            console.print("[red]Error:[/red] Provide key name(s)/number(s), or use --all")
            raise SystemExit(1)

        names = _resolve_multiple(manager, identifiers)

        if only:
            # Disable all first, then enable selected
            for key in manager.config.keys:
                if key.name not in names:
                    manager.disable_key(key.name)
                    console.print(f"  [dim]Disabled {key.name}[/dim]")

        for name in names:
            manager.enable_key(name)
            console.print(f"[green]✓[/green] Enabled '[cyan]{name}[/cyan]'")

    except (ValueError, RuntimeError, click.BadParameter) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("identifiers", nargs=-1, required=False)
@click.option("--all", "disable_all", is_flag=True, help="Disable all keys")
@click.option("--except", "except_ids", multiple=True, help="Disable all EXCEPT these (use with --all)")
def disable(identifiers: tuple[str, ...], disable_all: bool, except_ids: tuple[str, ...]):
    """Disable API key(s). Use name or serial number.

    \b
    Examples:
        vbagent keys disable 2                   # Disable key #2
        vbagent keys disable "Hash The Hash"     # Disable by name
        vbagent keys disable 1 2 3               # Disable multiple
        vbagent keys disable --all               # Disable all keys
        vbagent keys disable --all --except 4    # Disable all except #4
    """
    console = Console()
    manager = KeyManager.get_instance()

    if not manager.is_enabled():
        console.print("[yellow]Key manager not configured.[/yellow]")
        return

    try:
        if disable_all:
            except_names = set(_resolve_multiple(manager, except_ids)) if except_ids else set()

            for key in manager.config.keys:
                if key.name in except_names:
                    console.print(f"  [dim]Kept {key.name}[/dim]")
                else:
                    manager.disable_key(key.name)
                    console.print(f"[yellow]✓[/yellow] Disabled '[cyan]{key.name}[/cyan]'")
            return

        if not identifiers:
            console.print("[red]Error:[/red] Provide key name(s)/number(s), or use --all")
            raise SystemExit(1)

        names = _resolve_multiple(manager, identifiers)
        for name in names:
            manager.disable_key(name)
            console.print(f"[yellow]✓[/yellow] Disabled '[cyan]{name}[/cyan]'")

    except (ValueError, RuntimeError, click.BadParameter) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("identifier")
@click.confirmation_option(prompt="Are you sure you want to remove this key?")
def remove(identifier: str):
    """Remove an API key. Use name or serial number."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        name = _resolve_key(manager, identifier)
        manager.remove_key(name)
        console.print(f"[green]✓[/green] Removed key '[cyan]{name}[/cyan]'")
    except (ValueError, RuntimeError, click.BadParameter) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.confirmation_option(prompt="Reset all daily usage counters?")
def reset():
    """Reset all daily usage counters."""
    console = Console()
    manager = KeyManager.get_instance()

    if not manager.is_enabled():
        console.print("[yellow]API key manager not configured.[/yellow]")
        return

    manager.reset_daily_usage()
    console.print("[green]✓[/green] Reset all daily usage counters")


@keys.command()
def init():
    """Initialize API key configuration with example."""
    console = Console()
    manager = KeyManager.get_instance()

    if manager._config_path.exists():
        console.print(f"[yellow]Configuration already exists:[/yellow] {manager._config_path}")
        if not click.confirm("Overwrite?"):
            return

    example_config = {
        "keys": [
            {
                "name": "key1",
                "api_key": "sk-YOUR-API-KEY-HERE",
                "limits": {
                    "standard": {"daily_limit": 1000000, "used_today": 0},
                    "mini": {"daily_limit": 2000000, "used_today": 0},
                },
                "enabled": True,
            }
        ],
        "rotation_strategy": "least_used",
        "model_categories": {
            "standard": ["gpt-5.4", "gpt-4o", "gpt-4-turbo", "gpt-4"],
            "mini": ["gpt-5.4-mini", "gpt-4o-mini", "gpt-3.5-turbo"],
        },
        "last_used_index": 0,
    }

    manager._config_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(manager._config_path, "w") as f:
        json.dump(example_config, f, indent=2)

    console.print(f"[green]✓[/green] Created configuration: [cyan]{manager._config_path}[/cyan]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Edit the file and replace 'sk-YOUR-API-KEY-HERE' with your actual API key")
    console.print("2. Add more keys if needed")
    console.print("3. Run 'vbagent keys list' to verify")
