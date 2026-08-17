"""Shared action prompts for interactive quality-check sessions."""

from vbagent.cli.common import _get_prompt


def prompt_checker_action(console) -> str:
    """Prompt user for action on TikZ generation/check result.

    Args:
        console: Rich console for output

    Returns:
        Action string: 'approve', 'edit', 'reject', 'skip', or 'quit'
    """
    console.print("\n[bold]Actions:[/bold]")
    console.print("  [green]a[/green]pprove - Apply this change")
    console.print("  [red]r[/red]eject  - Store for later, don't apply")
    console.print("  [blue]e[/blue]dit    - Edit in editor before applying")
    console.print("  [yellow]s[/yellow]kip    - Skip without storing")
    console.print("  [dim]q[/dim]uit    - Exit session")

    Prompt = _get_prompt()
    try:
        choice = Prompt.ask(
            "\nAction",
            choices=["a", "r", "e", "s", "q", "approve", "reject", "edit", "skip", "quit"],
            default="a"
        ).lower()
    except KeyboardInterrupt:
        return "quit"

    if choice in ["a", "approve"]:
        return "approve"
    elif choice in ["r", "reject"]:
        return "reject"
    elif choice in ["e", "edit"]:
        return "edit"
    elif choice in ["s", "skip"]:
        return "skip"
    else:
        return "quit"
