"""CLI command for running vbagent as an MCP server."""

import asyncio
import logging

import click
from rich.console import Console

from vbagent.mcp.server import MCPServer
from vbagent.orchestrator.tools import ToolRegistry
from vbagent.orchestrator.tool_wrappers import register_core_tools


console = Console()


@click.command()
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
def mcp(verbose: bool):
    """Run vbagent as an MCP (Model Context Protocol) server.
    
    This starts vbagent in MCP server mode, exposing all tools via the
    Model Context Protocol for integration with external agents like
    Kiro, Cursor, and Claude Desktop.
    
    The server uses stdio transport and communicates via stdin/stdout.
    
    Example:
        vbagent mcp
        vbagent mcp --verbose
    
    Configuration:
        Add to your MCP client configuration (e.g., Kiro's mcp.json):
        
        {
          "mcpServers": {
            "vbagent": {
              "command": "vbagent",
              "args": ["mcp"],
              "env": {}
            }
          }
        }
    """
    # Configure logging
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )
    
    try:
        # Create tool registry and register all tools
        registry = ToolRegistry()
        register_core_tools(registry)
        
        # Create and run MCP server
        server = MCPServer(registry)
        
        # Run the async server
        asyncio.run(server.run())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]MCP server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


if __name__ == '__main__':
    mcp()
