"""CLI command for the authoring-focused MCP server."""

from __future__ import annotations

import logging
import sys

import click
from rich.console import Console

from vbagent.mcp.server import MCPServer

console = Console(stderr=True)


@click.command()
@click.option(
    "--output",
    default="agentic/authoring",
    show_default=True,
    type=click.Path(file_okay=False),
    help="Server-controlled authoring workspace used by every MCP tool.",
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    show_default=True,
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", type=click.IntRange(1, 65535), default=8000, show_default=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logs on stderr.")
def mcp(output: str, transport: str, host: str, port: int, verbose: bool) -> None:
    """Serve durable problem authoring through Model Context Protocol.

    The MCP host supplies the natural-language model. VBAgent exposes typed
    catalog, plan, start, status, pagination, cancellation, review, variant,
    and artifact operations backed by the same ledger as ``vbagent author``.

    Stdio example for an MCP client configuration:

    \b
        {
          "mcpServers": {
            "vbagent-authoring": {
              "command": "vbagent",
              "args": ["mcp", "--output", "agentic/authoring"]
            }
          }
        }
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        server = MCPServer(
            output_root=output,
            host=host,
            port=port,
            log_level="DEBUG" if verbose else "INFO",
        )
        server.run(transport=transport)
    except KeyboardInterrupt:
        console.print("MCP server stopped.")
    except Exception as exc:
        logging.getLogger(__name__).exception("MCP server failed")
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    mcp()
