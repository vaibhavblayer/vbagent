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
        console.print("\nExample configuration:")
        console.print("""
{
  "keys": [
    {
      "name": "key1",
      "api_key": "sk-...",
      "limits": {
        "standard": {"daily_limit": 1000000},
        "mini": {"daily_limit": 2000000}
      },
      "enabled": true
    }
  ],
  "rotation_strategy": "least_used"
}
""")
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
        if data["enabled"]:  # Only count enabled keys
            for category, stats in data["categories"].items():
                if category in totals:
                    totals[category]["used"] += stats["used"]
                    totals[category]["limit"] += stats["limit"]

    # Create table
    table = Table(title="API Key Usage", show_lines=True)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Used", justify="right")
    table.add_column("Limit", justify="right")
    table.add_column("Remaining", justify="right")
    table.add_column("Usage %", justify="right")
    table.add_column("Status", justify="center")

    for key_name, data in summary.items():
        enabled = data["enabled"]
        status = "[green]✓[/green]" if enabled else "[red]✗[/red]"

        for idx, (category, stats) in enumerate(data["categories"].items()):
            used = _format_tokens(stats["used"])
            limit = _format_tokens(stats["limit"])
            remaining = _format_tokens(stats["remaining"])
            percentage = stats["percentage"]

            # Color code based on usage
            if percentage >= 90:
                usage_color = "red"
            elif percentage >= 70:
                usage_color = "yellow"
            else:
                usage_color = "green"

            usage_str = f"[{usage_color}]{percentage:.1f}%[/{usage_color}]"

            # Only show key name on first row
            key_display = key_name if idx == 0 else ""
            status_display = status if idx == 0 else ""

            table.add_row(
                key_display,
                category,
                used,
                limit,
                remaining,
                usage_str,
                status_display,
            )

    # Add separator and total rows
    table.add_section()
    
    for category in ["standard", "mini"]:
        total_used = totals[category]["used"]
        total_limit = totals[category]["limit"]
        total_remaining = total_limit - total_used
        total_percentage = (total_used / total_limit * 100) if total_limit > 0 else 0
        
        # Color code total percentage
        if total_percentage >= 90:
            usage_color = "red"
        elif total_percentage >= 70:
            usage_color = "yellow"
        else:
            usage_color = "green"
        
        usage_str = f"[{usage_color}]{total_percentage:.1f}%[/{usage_color}]"
        
        # Show "TOTAL" only on first category row
        key_display = "[bold]TOTAL (enabled)[/bold]" if category == "standard" else ""
        
        table.add_row(
            key_display,
            category,
            _format_tokens(total_used),
            _format_tokens(total_limit),
            _format_tokens(total_remaining),
            usage_str,
            "",
        )

    console.print(table)

    # Show rotation strategy
    if manager.config:
        console.print(f"\n[dim]Rotation strategy: {manager.config.rotation_strategy}[/dim]")


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
@click.argument("name")
@click.option("--standard-limit", type=int, help="New daily limit for standard models")
@click.option("--mini-limit", type=int, help="New daily limit for mini models")
def update(name: str, standard_limit: int, mini_limit: int):
    """Update limits for an existing key."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        manager.update_limits(name, standard_limit, mini_limit)
        console.print(f"[green]✓[/green] Updated limits for '[cyan]{name}[/cyan]'")
        if standard_limit:
            console.print(f"  Standard limit: {_format_tokens(standard_limit)} tokens/day")
        if mini_limit:
            console.print(f"  Mini limit: {_format_tokens(mini_limit)} tokens/day")
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("name")
def enable(name: str):
    """Enable an API key."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        manager.enable_key(name)
        console.print(f"[green]✓[/green] Enabled key '[cyan]{name}[/cyan]'")
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("name")
def disable(name: str):
    """Disable an API key."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        manager.disable_key(name)
        console.print(f"[yellow]✓[/yellow] Disabled key '[cyan]{name}[/cyan]'")
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@keys.command()
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to remove this key?")
def remove(name: str):
    """Remove an API key."""
    console = Console()
    manager = KeyManager.get_instance()

    try:
        manager.remove_key(name)
        console.print(f"[green]✓[/green] Removed key '[cyan]{name}[/cyan]'")
    except (ValueError, RuntimeError) as e:
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

    # Create example config
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
    console.print("3. Adjust daily limits as needed")
    console.print("4. Run 'vbagent keys list' to verify")
