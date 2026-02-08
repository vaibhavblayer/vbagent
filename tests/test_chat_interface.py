"""Unit tests for chat interface.

Tests the ChatInterface class for:
- Session start/stop
- Exit command handling
- Message display
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vbagent.orchestrator import Orchestrator, ToolRegistry
from vbagent.cli.chat import ChatInterface


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    orchestrator = MagicMock(spec=Orchestrator)
    orchestrator.send_message = AsyncMock(return_value="Test response")
    orchestrator.set_system_message = MagicMock()
    orchestrator.save_conversation = MagicMock()
    orchestrator.load_conversation = MagicMock()
    return orchestrator


@pytest.fixture
def chat_interface(mock_orchestrator):
    """Create a ChatInterface instance with mock orchestrator."""
    return ChatInterface(mock_orchestrator)


class TestChatInterface:
    """Test suite for ChatInterface class."""
    
    def test_initialization(self, mock_orchestrator):
        """Test that ChatInterface initializes correctly."""
        interface = ChatInterface(mock_orchestrator)
        
        assert interface.orchestrator == mock_orchestrator
        assert interface.console is not None
        assert interface.running is False
    
    def test_display_message_user(self, chat_interface):
        """Test displaying a user message."""
        with patch.object(chat_interface.console, 'print') as mock_print:
            chat_interface.display_message("user", "Hello!")
            
            # Verify print was called
            mock_print.assert_called_once()
            
            # Verify the panel has correct styling
            panel = mock_print.call_args[0][0]
            assert panel.title == "You"
            assert panel.border_style == "blue"
    
    def test_display_message_assistant(self, chat_interface):
        """Test displaying an assistant message."""
        with patch.object(chat_interface.console, 'print') as mock_print:
            chat_interface.display_message("assistant", "Hello back!")
            
            # Verify print was called
            mock_print.assert_called_once()
            
            # Verify the panel has correct styling
            panel = mock_print.call_args[0][0]
            assert panel.title == "Assistant"
            assert panel.border_style == "green"
    
    def test_display_message_system(self, chat_interface):
        """Test displaying a system message."""
        with patch.object(chat_interface.console, 'print') as mock_print:
            chat_interface.display_message("system", "System message")
            
            # Verify print was called
            mock_print.assert_called_once()
            
            # Verify the panel has correct styling
            panel = mock_print.call_args[0][0]
            assert panel.title == "System"
            assert panel.border_style == "yellow"
    
    def test_display_tool_execution_executing(self, chat_interface):
        """Test displaying tool execution in progress."""
        with patch.object(chat_interface.console, 'print') as mock_print:
            chat_interface.display_tool_execution("test_tool", "executing")
            
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "test_tool" in call_args
            assert "⚙" in call_args or "Executing" in call_args
    
    def test_display_tool_execution_success(self, chat_interface):
        """Test displaying successful tool execution."""
        with patch.object(chat_interface.console, 'print') as mock_print:
            chat_interface.display_tool_execution("test_tool", "success")
            
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "test_tool" in call_args
            assert "✓" in call_args or "completed" in call_args
    
    def test_display_tool_execution_error(self, chat_interface):
        """Test displaying failed tool execution."""
        with patch.object(chat_interface.console, 'print') as mock_print:
            chat_interface.display_tool_execution("test_tool", "error")
            
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "test_tool" in call_args
            assert "✗" in call_args or "failed" in call_args
    
    @pytest.mark.asyncio
    async def test_send_with_progress(self, chat_interface, mock_orchestrator):
        """Test sending message with progress indicator."""
        response = await chat_interface._send_with_progress("Test message")
        
        # Verify orchestrator was called
        mock_orchestrator.send_message.assert_called_once_with("Test message")
        
        # Verify response is returned
        assert response == "Test response"
    
    def test_get_user_input(self, chat_interface):
        """Test getting user input."""
        with patch('vbagent.cli.chat.Prompt.ask', return_value="User input"):
            user_input = chat_interface._get_user_input()
            
            assert user_input == "User input"
    
    @pytest.mark.asyncio
    async def test_input_loop_exit_command(self, chat_interface, mock_orchestrator):
        """Test that exit command terminates the input loop."""
        # Mock user input to return 'exit'
        with patch.object(chat_interface, '_get_user_input', return_value="exit"):
            chat_interface.running = True
            await chat_interface._input_loop()
            
            # Verify loop stopped
            assert chat_interface.running is False
            
            # Verify orchestrator was not called
            mock_orchestrator.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_loop_quit_command(self, chat_interface, mock_orchestrator):
        """Test that quit command terminates the input loop."""
        # Mock user input to return 'quit'
        with patch.object(chat_interface, '_get_user_input', return_value="quit"):
            chat_interface.running = True
            await chat_interface._input_loop()
            
            # Verify loop stopped
            assert chat_interface.running is False
            
            # Verify orchestrator was not called
            mock_orchestrator.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_loop_q_command(self, chat_interface, mock_orchestrator):
        """Test that 'q' command terminates the input loop."""
        # Mock user input to return 'q'
        with patch.object(chat_interface, '_get_user_input', return_value="q"):
            chat_interface.running = True
            await chat_interface._input_loop()
            
            # Verify loop stopped
            assert chat_interface.running is False
            
            # Verify orchestrator was not called
            mock_orchestrator.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_loop_empty_input(self, chat_interface, mock_orchestrator):
        """Test that empty input is skipped."""
        # Mock user input to return empty string then exit
        inputs = ["", "exit"]
        input_iter = iter(inputs)
        
        with patch.object(chat_interface, '_get_user_input', side_effect=lambda: next(input_iter)):
            chat_interface.running = True
            await chat_interface._input_loop()
            
            # Verify orchestrator was not called for empty input
            mock_orchestrator.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_input_loop_normal_message(self, chat_interface, mock_orchestrator):
        """Test processing a normal message."""
        # Mock user input to send a message then exit
        inputs = ["Hello", "exit"]
        input_iter = iter(inputs)
        
        with patch.object(chat_interface, '_get_user_input', side_effect=lambda: next(input_iter)):
            with patch.object(chat_interface, 'display_message'):
                chat_interface.running = True
                await chat_interface._input_loop()
                
                # Verify orchestrator was called with the message
                mock_orchestrator.send_message.assert_called_once_with("Hello")
    
    @pytest.mark.asyncio
    async def test_input_loop_eoferror(self, chat_interface, mock_orchestrator):
        """Test that EOFError (Ctrl+D) terminates the loop gracefully."""
        with patch.object(chat_interface, '_get_user_input', side_effect=EOFError):
            chat_interface.running = True
            await chat_interface._input_loop()
            
            # Verify loop stopped
            assert chat_interface.running is False
    
    @pytest.mark.asyncio
    async def test_input_loop_keyboard_interrupt(self, chat_interface, mock_orchestrator):
        """Test that KeyboardInterrupt (Ctrl+C) terminates the loop."""
        with patch.object(chat_interface, '_get_user_input', side_effect=KeyboardInterrupt):
            chat_interface.running = True
            
            with pytest.raises(KeyboardInterrupt):
                await chat_interface._input_loop()
            
            # Verify loop stopped
            assert chat_interface.running is False
    
    @pytest.mark.asyncio
    async def test_input_loop_error_handling(self, chat_interface, mock_orchestrator):
        """Test that errors during message processing are handled gracefully."""
        # Mock orchestrator to raise an error
        mock_orchestrator.send_message.side_effect = Exception("Test error")
        
        # Mock user input to send a message then exit
        inputs = ["Hello", "exit"]
        input_iter = iter(inputs)
        
        with patch.object(chat_interface, '_get_user_input', side_effect=lambda: next(input_iter)):
            with patch.object(chat_interface, 'display_message'):
                with patch.object(chat_interface.console, 'print'):
                    chat_interface.running = True
                    await chat_interface._input_loop()
                    
                    # Verify loop continued after error
                    assert chat_interface.running is False
    
    def test_start_sets_system_message(self, chat_interface, mock_orchestrator):
        """Test that start() sets a system message."""
        # Mock the input loop to exit immediately
        with patch.object(chat_interface, '_input_loop', new_callable=AsyncMock):
            with patch.object(chat_interface, '_display_welcome'):
                with patch.object(chat_interface, '_display_goodbye'):
                    chat_interface.start()
                    
                    # Verify system message was set
                    mock_orchestrator.set_system_message.assert_called_once()
                    call_args = mock_orchestrator.set_system_message.call_args[0][0]
                    assert "vbagent" in call_args.lower()
    
    def test_start_displays_welcome_and_goodbye(self, chat_interface, mock_orchestrator):
        """Test that start() displays welcome and goodbye messages."""
        with patch.object(chat_interface, '_input_loop', new_callable=AsyncMock):
            with patch.object(chat_interface, '_display_welcome') as mock_welcome:
                with patch.object(chat_interface, '_display_goodbye') as mock_goodbye:
                    chat_interface.start()
                    
                    # Verify welcome and goodbye were displayed
                    mock_welcome.assert_called_once()
                    mock_goodbye.assert_called_once()
    
    def test_start_handles_keyboard_interrupt(self, chat_interface, mock_orchestrator):
        """Test that start() handles KeyboardInterrupt gracefully."""
        with patch.object(chat_interface, '_input_loop', new_callable=AsyncMock, side_effect=KeyboardInterrupt):
            with patch.object(chat_interface, '_display_welcome'):
                with patch.object(chat_interface, '_display_goodbye'):
                    with patch.object(chat_interface.console, 'print'):
                        # Should not raise
                        chat_interface.start()
