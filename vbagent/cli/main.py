"""Main CLI entry point for VBAgent.

VBAgent - Physics question processing pipeline.

Uses lazy loading to speed up CLI startup time by deferring
heavy imports (openai, agents, mcp, etc.) until commands are actually invoked.
"""

import click


def _get_version():
    """Get version from package metadata."""
    try:
        from importlib.metadata import version
        return version("vbagent")
    except Exception:
        return "0.2.1"  # Fallback


class LazyGroup(click.Group):
    """A click Group that lazily loads subcommands.
    
    This dramatically improves CLI startup time by deferring imports
    of heavy dependencies (openai, agents, mcp, rich, etc.) until
    a specific command is actually invoked.
    """
    
    def __init__(self, *args, lazy_subcommands: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Map of command name -> module path
        self._lazy_subcommands = lazy_subcommands or {}
    
    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy
    
    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in self._lazy_subcommands:
            return self._lazy_load(cmd_name)
        return super().get_command(ctx, cmd_name)
    
    def _lazy_load(self, cmd_name: str) -> click.Command:
        # Import the module and get the command
        import importlib
        module_path = self._lazy_subcommands[cmd_name]
        module = importlib.import_module(module_path)
        return getattr(module, cmd_name)


# Define lazy subcommands: command_name -> module_path
LAZY_SUBCOMMANDS = {
    # Core commands
    "classify": "vbagent.cli.core.classify",
    "scan": "vbagent.cli.core.scan",
    "process": "vbagent.cli.core.process",
    "batch": "vbagent.cli.core.batch",
    "init": "vbagent.cli.core.init",
    # Generation commands
    "tikz": "vbagent.cli.generation.tikz",
    "fbd": "vbagent.cli.generation.fbd",
    "idea": "vbagent.cli.generation.idea",
    "alternate": "vbagent.cli.generation.alternate",
    "variant": "vbagent.cli.generation.variant",
    "convert": "vbagent.cli.generation.convert",
    # Quality commands
    "check": "vbagent.cli.quality.check",
    # Management commands
    "ref": "vbagent.cli.management.ref",
    "config": "vbagent.cli.management.config",
    "util": "vbagent.cli.management.util",
    "metadata": "vbagent.cli.management.metadata",
    "dpp": "vbagent.cli.management.dpp",
    "export": "vbagent.cli.management.export",
    "extans": "vbagent.cli.management.extans",
    "db": "vbagent.cli.management.db",
    # Interface commands
    "chat": "vbagent.cli.interfaces.chat",
    "mcp": "vbagent.cli.interfaces.mcp",
}


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(cls=LazyGroup, lazy_subcommands=LAZY_SUBCOMMANDS, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=_get_version(), prog_name="vbagent")
def main():
    """VBAgent - Physics question processing pipeline.
    
    A multi-agent CLI system for processing physics question images.
    Supports classification, scanning, diagram generation, variant creation,
    and format conversion.
    
    \b
    Commands:
        init      - Initialize workspace config (.vbagent.json)
        chat      - Interactive conversational interface
        mcp       - Start MCP server for external agents
        metadata  - Manage question bank metadata
        dpp       - Create Daily Practice Problem sets
        export    - Export LaTeX files in different formats
        extans    - Extract answers from LaTeX problem files
        db        - Database management for question bank
        process   - Full pipeline orchestration
        classify  - Stage 1: Classify question image
        scan      - Stage 2: Extract LaTeX from image
        tikz      - Generate TikZ code for diagrams
        fbd       - Generate Free Body Diagram TikZ code
        idea      - Extract concepts and ideas
        alternate - Generate alternative solutions
        variant   - Generate problem variants
        convert   - Convert between question formats
        batch     - Batch processing with resume capability
        check     - QA review with interactive approval
        ref       - Manage reference context files
        config    - Configure models and settings
        util      - File utilities (rename, count, clean)
    """
    # Disable tracing early (before agents SDK import) for non-OpenAI providers.
    # The SDK initializes tracing at import time, so the env var must be set first.
    from vbagent.config import get_config
    cfg = get_config()
    if cfg.base_url:
        import os
        os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"


if __name__ == "__main__":
    main()
