"""Main CLI entry point for VBAgent.

VBAgent - Multi-subject question processing pipeline.

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
        return "0.3.0"  # Fallback


# Command sections for grouped --help output
COMMAND_SECTIONS = {
    "Core Pipeline": [
        "run", "scan", "classify", "batch",
    ],
    "Generate": [
        "generate", "regenerate", "combine", "ideas", "tikz", "fbd", "idea", "concepts", "alternate", "variant", "convert", "animate",
    ],
    "Quality": [
        "check", "compile",
    ],
    "Manage": [
        "init", "config", "ref", "cache", "db", "metadata",
        "export", "archive", "dpp", "util", "keys",
    ],
    "Analysis": [
        "analysis",
    ],
    "Interfaces": [
        "chat", "mcp",
    ],
    "Paper": [
        "paper",
    ],
    "Utilities": [
        "extans", "screenshot",
    ],
}

# Flat lookup: command_name → section
_CMD_TO_SECTION = {}
for _section, _cmds in COMMAND_SECTIONS.items():
    for _cmd in _cmds:
        _CMD_TO_SECTION[_cmd] = _section


class SectionedGroup(click.Group):
    """A click Group with lazy loading and sectioned --help output.

    Lazy-loads subcommands for fast startup. Groups commands into
    labelled sections in --help output for discoverability.
    """

    def __init__(self, *args, lazy_subcommands: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
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
        import importlib
        module_path = self._lazy_subcommands[cmd_name]
        module = importlib.import_module(module_path)
        return getattr(module, cmd_name)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Override to group commands by section."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            help_text = cmd.get_short_help_str(limit=formatter.width)
            commands.append((subcommand, help_text))

        if not commands:
            return

        # Build section → [(name, help)] mapping
        sectioned: dict[str, list[tuple[str, str]]] = {}
        unsectioned: list[tuple[str, str]] = []

        for name, help_text in commands:
            section = _CMD_TO_SECTION.get(name)
            if section:
                sectioned.setdefault(section, []).append((name, help_text))
            else:
                unsectioned.append((name, help_text))

        # Write sections in defined order
        for section_name, section_cmds in COMMAND_SECTIONS.items():
            items = sectioned.get(section_name, [])
            if items:
                # Sort by the order defined in COMMAND_SECTIONS
                order = {cmd: i for i, cmd in enumerate(section_cmds)}
                items.sort(key=lambda x: order.get(x[0], 999))
                with formatter.section(section_name):
                    formatter.write_dl(items)

        if unsectioned:
            with formatter.section("Other"):
                formatter.write_dl(unsectioned)


# Define lazy subcommands: command_name -> module_path
LAZY_SUBCOMMANDS = {
    # Core pipeline
    "run": "vbagent.cli.core.process",
    "scan": "vbagent.cli.core.scan",
    "classify": "vbagent.cli.core.classify",
    "batch": "vbagent.cli.core.batch",
    # Generate
    "generate": "vbagent.cli.generation.generate",
    "regenerate": "vbagent.cli.generation.regenerate",
    "combine": "vbagent.cli.generation.combine",
    "ideas": "vbagent.cli.generation.ideas",
    "tikz": "vbagent.cli.generation.tikz",
    "fbd": "vbagent.cli.generation.fbd",
    "idea": "vbagent.cli.generation.idea",
    "concepts": "vbagent.cli.generation.concepts",
    "alternate": "vbagent.cli.generation.alternate",
    "variant": "vbagent.cli.generation.variant",
    "convert": "vbagent.cli.generation.convert",
    "animate": "vbagent.cli.generation.animate",
    # Quality
    "check": "vbagent.cli.quality.check",
    "compile": "vbagent.cli.compilation.compile_main",
    # Manage
    "init": "vbagent.cli.core.init",
    "config": "vbagent.cli.management.config",
    "ref": "vbagent.cli.management.ref",
    "cache": "vbagent.cli.cache.cache_commands",
    "db": "vbagent.cli.management.db",
    "metadata": "vbagent.cli.management.metadata",
    "export": "vbagent.cli.management.export",
    "archive": "vbagent.cli.management.archive",
    "dpp": "vbagent.cli.management.dpp",
    "util": "vbagent.cli.management.util",
    "keys": "vbagent.cli.keys",
    # Analysis
    "analysis": "vbagent.cli.analysis.main",
    # Interfaces
    "chat": "vbagent.cli.interfaces.chat",
    "mcp": "vbagent.cli.interfaces.mcp",
    # Paper
    "paper": "vbagent.cli.paper.paper_commands",
    # Utilities
    "extans": "vbagent.cli.management.extans",
    "screenshot": "vbagent.cli.management.screenshot",
}


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(cls=SectionedGroup, lazy_subcommands=LAZY_SUBCOMMANDS, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=_get_version(), prog_name="vbagent")
def main():
    """VBAgent - Multi-subject question processing pipeline.

    Process question images across physics, chemistry, and mathematics
    with AI-powered classification, scanning, diagram generation,
    solution orchestration, and variant creation.

    \b
    Quick Start:
        vbagent run -i question.png          # Full pipeline
        vbagent scan -i question.png         # Extract LaTeX only
        vbagent classify -i question.png     # Classify only
        vbagent batch init -i ./images       # Batch processing
    """
    # Disable tracing early (before agents SDK import) for non-OpenAI providers.
    from vbagent.config import get_config
    cfg = get_config()
    if cfg.base_url:
        import os
        os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"


if __name__ == "__main__":
    main()
