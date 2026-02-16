"""Integration tests for chat CLI command.

Tests the chat command integration with the CLI system.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from vbagent.cli.interfaces.chat import chat


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = MagicMock()
    orchestrator.send_message = AsyncMock(return_value="Test response")
    orchestrator.set_system_message = MagicMock()
    orchestrator.save_conversation = MagicMock()
    orchestrator.load_conversation = MagicMock()
    orchestrator.model = "gpt-4"
    return orchestrator


class TestChatCLI:
    """Test suite for chat CLI command."""
    
    def test_chat_command_help(self, runner):
        """Test that chat command help works."""
        result = runner.invoke(chat, ['--help'])
        
        assert result.exit_code == 0
        assert "Start interactive chat session" in result.output
        assert "--model" in result.output
        assert "--history" in result.output
        assert "--save-history" in result.output
    
    def test_chat_command_missing_api_key(self, runner):
        """Test that chat command fails gracefully without API key."""
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config') as mock_create:
            mock_create.side_effect = ValueError("No API key found")
            
            result = runner.invoke(chat, [])
            
            # Should abort with error message
            assert result.exit_code != 0
            assert "Configuration error" in result.output or "API key" in result.output
    
    def test_chat_command_with_model_override(self, runner, mock_orchestrator):
        """Test chat command with model override."""
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config', return_value=mock_orchestrator):
            with patch('vbagent.cli.interfaces.chat.ChatInterface') as mock_interface_class:
                mock_interface = MagicMock()
                mock_interface_class.return_value = mock_interface
                
                # Simulate immediate exit
                mock_interface.start = MagicMock()
                
                result = runner.invoke(chat, ['--model', 'gpt-4-turbo'])
                
                # Verify model was overridden
                assert mock_orchestrator.model == 'gpt-4-turbo'
    
    def test_chat_command_with_history_load(self, runner, mock_orchestrator, tmp_path):
        """Test chat command with history loading."""
        # Create a temporary history file
        history_file = tmp_path / "history.json"
        history_file.write_text('{"max_tokens": 100000, "messages": []}')
        
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config', return_value=mock_orchestrator):
            with patch('vbagent.cli.interfaces.chat.ChatInterface') as mock_interface_class:
                mock_interface = MagicMock()
                mock_interface_class.return_value = mock_interface
                mock_interface.start = MagicMock()
                
                result = runner.invoke(chat, ['--history', str(history_file)])
                
                # Verify history was loaded
                mock_orchestrator.load_conversation.assert_called_once()
    
    def test_chat_command_with_history_save(self, runner, mock_orchestrator, tmp_path):
        """Test chat command with history saving."""
        save_file = tmp_path / "save.json"
        
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config', return_value=mock_orchestrator):
            with patch('vbagent.cli.interfaces.chat.ChatInterface') as mock_interface_class:
                mock_interface = MagicMock()
                mock_interface_class.return_value = mock_interface
                mock_interface.start = MagicMock()
                
                result = runner.invoke(chat, ['--save-history', str(save_file)])
                
                # Verify history was saved
                mock_orchestrator.save_conversation.assert_called_once()
    
    def test_chat_command_handles_load_error(self, runner, mock_orchestrator, tmp_path):
        """Test that chat command handles history load errors gracefully."""
        # Create a file with invalid JSON
        history_file = tmp_path / "invalid.json"
        history_file.write_text('invalid json')
        
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config', return_value=mock_orchestrator):
            with patch('vbagent.cli.interfaces.chat.ChatInterface') as mock_interface_class:
                mock_interface = MagicMock()
                mock_interface_class.return_value = mock_interface
                mock_interface.start = MagicMock()
                
                # Mock load_conversation to raise an error
                mock_orchestrator.load_conversation.side_effect = Exception("Invalid JSON")
                
                result = runner.invoke(chat, ['--history', str(history_file)])
                
                # Should continue despite error (warning displayed)
                assert "Warning" in result.output or result.exit_code == 0
    
    def test_chat_command_handles_save_error(self, runner, mock_orchestrator, tmp_path):
        """Test that chat command handles history save errors gracefully."""
        save_file = tmp_path / "readonly" / "save.json"
        
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config', return_value=mock_orchestrator):
            with patch('vbagent.cli.interfaces.chat.ChatInterface') as mock_interface_class:
                mock_interface = MagicMock()
                mock_interface_class.return_value = mock_interface
                mock_interface.start = MagicMock()
                
                # Mock save_conversation to raise an error
                mock_orchestrator.save_conversation.side_effect = Exception("Cannot write")
                
                result = runner.invoke(chat, ['--save-history', str(save_file)])
                
                # Should complete despite error (warning displayed)
                assert "Warning" in result.output or result.exit_code == 0
    
    def test_chat_command_creates_interface(self, runner, mock_orchestrator):
        """Test that chat command creates ChatInterface and starts it."""
        with patch('vbagent.cli.interfaces.chat.create_orchestrator_from_config', return_value=mock_orchestrator):
            with patch('vbagent.cli.interfaces.chat.ChatInterface') as mock_interface_class:
                mock_interface = MagicMock()
                mock_interface_class.return_value = mock_interface
                mock_interface.start = MagicMock()
                
                result = runner.invoke(chat, [])
                
                # Verify interface was created with orchestrator
                mock_interface_class.assert_called_once_with(mock_orchestrator)
                
                # Verify start was called
                mock_interface.start.assert_called_once()
