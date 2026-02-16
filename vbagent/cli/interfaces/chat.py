"""Chat interface for conversational orchestrator.

Provides an interactive terminal-based chat interface using the Rich library
for formatted output and user interaction.
"""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text

from vbagent.orchestrator import (
    Orchestrator,
    ToolRegistry,
    create_orchestrator_from_config,
)


class ChatInterface:
    """Terminal chat interface with rich formatting.
    
    Provides an interactive chat session with:
    - Formatted message display (user/assistant/system panels)
    - Tool execution progress indicators
    - Exit command handling
    - Conversation history maintenance
    """
    
    def __init__(self, orchestrator: Orchestrator):
        """Initialize chat interface.
        
        Args:
            orchestrator: Orchestrator instance for handling conversations
        """
        self.orchestrator = orchestrator
        self.console = Console()
        self.running = False
    
    def start(self) -> None:
        """Start interactive chat session.
        
        Displays welcome message, enters input loop, and handles exit commands.
        """
        self.running = True
        
        # Display welcome message
        self._display_welcome()
        
        # Set system message for the orchestrator with clarification guidance
        self.orchestrator.set_system_message(
            "You are a helpful assistant for vbagent, a physics question processing system. "
            "You can help users with tasks like scanning questions, generating variants, "
            "creating DPPs, generating problems from ideas, and more.\n\n"
            "**Problem Generation Guidance:**\n"
            "When a user wants to generate a problem but doesn't provide all necessary details, "
            "ask clarifying questions ONE AT A TIME in a conversational manner:\n\n"
            "Required information:\n"
            "- idea: What the problem is about (e.g., 'double block friction system')\n"
            "- topic: Physics topic (e.g., 'Mechanics', 'Thermodynamics', 'Kinematics')\n\n"
            "Optional information (ask if not provided):\n"
            "- question_type: Type of question (mcq_sc, mcq_mc, passage, subjective, assertion_reason, match)\n"
            "  Default: passage\n"
            "- num_questions: Number of questions (for passage type, typically 2-4)\n"
            "  Default: 2\n"
            "- difficulty: Difficulty level (easy, medium, hard)\n"
            "  Default: medium\n"
            "- with_diagram: Whether to include diagrams (yes/no)\n"
            "  Default: yes\n"
            "- concepts: Specific concepts to cover (optional list)\n\n"
            "Examples of good clarification:\n"
            "User: 'Create a problem on friction'\n"
            "You: 'I can help you generate a problem on friction! What topic is this for? "
            "(e.g., Mechanics, Dynamics)'\n\n"
            "User: 'Mechanics'\n"
            "You: 'Great! What type of question would you like? "
            "(mcq_sc for single correct MCQ, passage for comprehension with multiple questions, or subjective)'\n\n"
            "User: 'passage'\n"
            "You: 'Perfect! How many questions should the passage have? (typically 2-4)'\n\n"
            "After collecting all information, call the generate_problem tool with the parameters.\n\n"
            "Use the available tools to accomplish user requests."
        )
        
        # Enter input loop
        try:
            asyncio.run(self._input_loop())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Chat session interrupted.[/yellow]")
        finally:
            self._display_goodbye()
    
    def _display_welcome(self) -> None:
        """Display welcome message."""
        welcome_text = Text()
        welcome_text.append("Welcome to VBAgent Chat!\n\n", style="bold cyan")
        welcome_text.append("I can help you with:\n", style="bold")
        welcome_text.append("  • Scanning question images to LaTeX\n")
        welcome_text.append("  • Generating problems from ideas\n", style="green")
        welcome_text.append("  • Creating TikZ diagrams\n")
        welcome_text.append("  • Generating variants and alternates\n")
        welcome_text.append("  • Creating DPP sets\n")
        welcome_text.append("  • And more!\n\n")
        welcome_text.append("Type your questions or commands in natural language.\n")
        welcome_text.append("Type ", style="dim")
        welcome_text.append("exit", style="bold")
        welcome_text.append(" or ", style="dim")
        welcome_text.append("quit", style="bold")
        welcome_text.append(" to end the session.\n", style="dim")
        
        panel = Panel(
            welcome_text,
            title="VBAgent Conversational Interface",
            border_style="cyan",
        )
        self.console.print(panel)
        self.console.print()
    
    def _display_goodbye(self) -> None:
        """Display goodbye message."""
        self.console.print()
        self.console.print(
            Panel(
                "[cyan]Thank you for using VBAgent Chat![/cyan]",
                border_style="cyan"
            )
        )
    
    async def _input_loop(self) -> None:
        """Main input loop for chat session."""
        while self.running:
            try:
                # Get user input
                user_input = self._get_user_input()
                
                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "q"]:
                    self.running = False
                    break
                
                # Skip empty input
                if not user_input.strip():
                    continue
                
                # Display user message
                self.display_message("user", user_input)
                
                # Send message to orchestrator with progress indicator
                response = await self._send_with_progress(user_input)
                
                # Display assistant response
                self.display_message("assistant", response)
                
            except EOFError:
                # Handle Ctrl+D
                self.running = False
                break
            except KeyboardInterrupt:
                # Handle Ctrl+C
                self.running = False
                raise
            except Exception as e:
                # Display error and continue
                self.console.print(f"[red]Error: {str(e)}[/red]")
    
    def _get_user_input(self) -> str:
        """Get input from user with prompt.
        
        Returns:
            User input string
        """
        return Prompt.ask("[bold blue]You[/bold blue]")
    
    async def _send_with_progress(self, message: str) -> str:
        """Send message to orchestrator with progress indicator.
        
        Args:
            message: User message to send
            
        Returns:
            Assistant response
        """
        # Create a spinner for progress indication
        spinner = Spinner("dots", text="Thinking...")
        
        with Live(spinner, console=self.console, transient=True):
            response = await self.orchestrator.send_message(message)
        
        return response
    
    def display_message(self, role: str, content: str) -> None:
        """Display a formatted message.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        if role == "user":
            panel = Panel(
                content,
                title="You",
                border_style="blue",
                title_align="left",
            )
        elif role == "assistant":
            panel = Panel(
                content,
                title="Assistant",
                border_style="green",
                title_align="left",
            )
        elif role == "system":
            panel = Panel(
                content,
                title="System",
                border_style="yellow",
                title_align="left",
            )
        else:
            # Unknown role, use default
            panel = Panel(
                content,
                title=role.capitalize(),
                border_style="white",
                title_align="left",
            )
        
        self.console.print(panel)
    
    def display_tool_execution(self, tool_name: str, status: str) -> None:
        """Display tool execution progress.
        
        Args:
            tool_name: Name of the tool being executed
            status: Status (executing, success, error)
        """
        if status == "executing":
            self.console.print(f"[yellow]⚙ Executing tool: {tool_name}...[/yellow]")
        elif status == "success":
            self.console.print(f"[green]✓ Tool completed: {tool_name}[/green]")
        elif status == "error":
            self.console.print(f"[red]✗ Tool failed: {tool_name}[/red]")


@click.command()
@click.option(
    '--model',
    help='Override orchestrator model (e.g., gpt-4, claude-3-opus)',
    default=None
)
@click.option(
    '--history',
    type=click.Path(exists=True, path_type=Path),
    help='Load conversation history from file',
    default=None
)
@click.option(
    '--save-history',
    type=click.Path(path_type=Path),
    help='Save conversation history to file on exit',
    default=None
)
def chat(
    model: Optional[str],
    history: Optional[Path],
    save_history: Optional[Path]
):
    """Start interactive chat session.
    
    Provides a conversational interface to vbagent functionality.
    The assistant can help with tasks like scanning questions,
    generating variants, creating DPPs, and more.
    
    Examples:
    
        # Start a chat session
        vbagent chat
        
        # Use a specific model
        vbagent chat --model gpt-4
        
        # Load previous conversation
        vbagent chat --history conversation.json
        
        # Save conversation on exit
        vbagent chat --save-history conversation.json
    """
    console = Console()
    
    try:
        # Create tool registry (empty for now, will be populated in future tasks)
        tool_registry = ToolRegistry()
        
        # Create orchestrator from config
        try:
            orchestrator = create_orchestrator_from_config(tool_registry)
        except ValueError as e:
            console.print(f"[red]Configuration error: {str(e)}[/red]")
            console.print("\n[yellow]Please ensure you have:")
            console.print("1. Set up your API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)")
            console.print("2. Configured vbagent with 'vbagent config'[/yellow]")
            raise click.Abort()
        
        # Override model if specified
        if model:
            orchestrator.model = model
        
        # Load conversation history if specified
        if history:
            try:
                orchestrator.load_conversation(history)
                console.print(f"[green]Loaded conversation from {history}[/green]\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load history: {str(e)}[/yellow]\n")
        
        # Create and start chat interface
        interface = ChatInterface(orchestrator)
        interface.start()
        
        # Save conversation history if specified
        if save_history:
            try:
                orchestrator.save_conversation(save_history)
                console.print(f"\n[green]Conversation saved to {save_history}[/green]")
            except Exception as e:
                console.print(f"\n[yellow]Warning: Could not save history: {str(e)}[/yellow]")
        
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        raise click.Abort()
