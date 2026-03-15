"""CLI command for managing screenshot save location.

Provides utilities for managing where screenshots are saved.
On macOS, uses system defaults to change actual screenshot location.
On other OS, stores preference in config file.
"""

import json
import platform
import subprocess
from pathlib import Path

import click

from ..common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _is_macos():
    """Check if running on macOS."""
    return platform.system() == "Darwin"


def _is_linux():
    """Check if running on Linux."""
    return platform.system() == "Linux"


def _has_gsettings():
    """Check if gsettings is available (GNOME/Ubuntu)."""
    try:
        result = subprocess.run(
            ["which", "gsettings"],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_config_file():
    """Get the config file path."""
    config_dir = Path.home() / ".config" / "vbagent"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "screenshot.json"


def _load_config():
    """Load screenshot config."""
    config_file = _get_config_file()
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except Exception:
            return {}
    return {}


def _save_config(config: dict):
    """Save screenshot config."""
    config_file = _get_config_file()
    config_file.write_text(json.dumps(config, indent=2))


def _run_command(cmd: list[str]) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


@click.group(context_settings=CONTEXT_SETTINGS)
def screenshot():
    """Manage screenshot save location.
    
    On macOS, changes system screenshot location.
    On other OS, stores preference in config.
    
    \b
    Examples:
        vbagent screenshot get
        vbagent screenshot set ~/Documents/screenshots
        vbagent screenshot reset
    """
    pass


@screenshot.command()
def get():
    """Get current screenshot save location."""
    console = _get_console()
    
    if _is_macos():
        # Read from macOS defaults
        success, output = _run_command([
            "defaults", "read", "com.apple.screencapture", "location"
        ])
        
        if success and output:
            console.print(f"[green]Screenshot location:[/green] {output}")
        else:
            home = Path.home()
            console.print(f"[yellow]Using default location:[/yellow] {home}/Desktop")
    elif _is_linux() and _has_gsettings():
        # Read from GNOME gsettings
        success, output = _run_command([
            "gsettings", "get", "org.gnome.gnome-screenshot", "auto-save-directory"
        ])
        
        if success and output and output != "''":
            # Remove quotes and file:// prefix
            location = output.strip("'\"")
            if location.startswith("file://"):
                location = location[7:]
            console.print(f"[green]Screenshot location:[/green] {location}")
        else:
            # Check XDG_PICTURES_DIR
            pictures_dir = Path.home() / "Pictures"
            console.print(f"[yellow]Using default location:[/yellow] {pictures_dir}")
    else:
        # Read from config file for other systems
        config = _load_config()
        location = config.get("location")
        
        if location:
            console.print(f"[green]Screenshot location:[/green] {location}")
        else:
            home = Path.home()
            console.print(f"[yellow]No custom location set. Using default:[/yellow] {home}/Desktop")


@screenshot.command()
@click.argument("path", type=click.Path())
def set(path: str):
    """Set screenshot save location.
    
    \b
    Args:
        path: Directory path where screenshots will be saved
    
    \b
    Example:
        vbagent screenshot set ~/Documents/screenshots
    """
    console = _get_console()
    
    # Expand user path
    expanded_path = Path(path).expanduser().resolve()
    
    # Check if path exists
    if not expanded_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {expanded_path}")
        console.print(f"[yellow]Tip:[/yellow] Create the directory first with: mkdir -p {path}")
        raise SystemExit(1)
    
    if not expanded_path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {expanded_path}")
        raise SystemExit(1)
    
    if _is_macos():
        # Set macOS system screenshot location
        success, _ = _run_command([
            "defaults", "write", "com.apple.screencapture", "location", str(expanded_path)
        ])
        
        if not success:
            console.print("[red]Error:[/red] Failed to set screenshot location")
            raise SystemExit(1)
        
        # Restart SystemUIServer to apply changes
        _run_command(["killall", "SystemUIServer"])
        
        console.print(f"[green]✓ Screenshot location updated:[/green] {expanded_path}")
        console.print("[dim]Note: SystemUIServer was restarted to apply changes[/dim]")
    elif _is_linux() and _has_gsettings():
        # Set GNOME screenshot location using gsettings
        file_uri = f"file://{expanded_path}"
        success, _ = _run_command([
            "gsettings", "set", "org.gnome.gnome-screenshot", "auto-save-directory", file_uri
        ])
        
        if not success:
            console.print("[red]Error:[/red] Failed to set screenshot location")
            raise SystemExit(1)
        
        console.print(f"[green]✓ Screenshot location updated:[/green] {expanded_path}")
        console.print("[dim]Note: This sets the GNOME screenshot tool location[/dim]")
    else:
        # Save to config file for other systems
        config = _load_config()
        config["location"] = str(expanded_path)
        _save_config(config)
        
        console.print(f"[green]✓ Screenshot location saved:[/green] {expanded_path}")
        console.print("[yellow]Note:[/yellow] This only stores the preference. Your OS may not use this location.")


@screenshot.command()
def reset():
    """Reset screenshot location to default."""
    console = _get_console()
    
    if _is_macos():
        # Delete macOS system screenshot location setting
        _run_command([
            "defaults", "delete", "com.apple.screencapture", "location"
        ])
        
        # Restart SystemUIServer to apply changes
        _run_command(["killall", "SystemUIServer"])
        
        home = Path.home()
        console.print(f"[green]✓ Reset to default location:[/green] {home}/Desktop")
        console.print("[dim]Note: SystemUIServer was restarted to apply changes[/dim]")
    elif _is_linux() and _has_gsettings():
        # Reset GNOME screenshot location to default
        _run_command([
            "gsettings", "reset", "org.gnome.gnome-screenshot", "auto-save-directory"
        ])
        
        pictures_dir = Path.home() / "Pictures"
        console.print(f"[green]✓ Reset to default location:[/green] {pictures_dir}")
        console.print("[dim]Note: GNOME screenshot tool reset to default[/dim]")
    else:
        # Clear config file for other systems
        config = _load_config()
        if "location" in config:
            del config["location"]
            _save_config(config)
        
        home = Path.home()
        console.print(f"[green]✓ Reset to default location:[/green] {home}/Desktop")

