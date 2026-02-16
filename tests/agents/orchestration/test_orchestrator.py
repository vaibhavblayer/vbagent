"""Tests for the Conversational Orchestrator.

Tests cover:
- ConversationContext message management
- Tool call tracking
- Context truncation
- Conversation persistence
- Orchestrator initialization
- Provider adapter creation
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from vbagent.orchestrator import (
    Orchestrator,
    ConversationContext,
    Message,
    ToolCall,
    ProviderResponse,
    ToolRegistry,
    OpenAIAdapter,
    AnthropicAdapter,
    XAIAdapter,
    GoogleAdapter,
)


class TestMessage:
    """Tests for Message class."""
    
    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.tool_calls is None
    
    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(role="user", content="Hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Hello"
        assert "timestamp" in d
    
    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        d = {
            "role": "assistant",
            "content": "Hi there",
            "timestamp": datetime.now().isoformat(),
        }
        msg = Message.from_dict(d)
        assert msg.role == "assistant"
        assert msg.content == "Hi there"


class TestToolCall:
    """Tests for ToolCall class."""
    
    def test_tool_call_creation(self):
        """Test creating a tool call."""
        tc = ToolCall(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="success"
        )
        assert tc.tool_name == "test_tool"
        assert tc.arguments == {"arg": "value"}
        assert tc.result == "success"
        assert tc.success is True
        assert tc.error is None
    
    def test_tool_call_with_error(self):
        """Test creating a failed tool call."""
        tc = ToolCall(
            tool_name="test_tool",
            arguments={},
            result=None,
            success=False,
            error="Tool failed"
        )
        assert tc.success is False
        assert tc.error == "Tool failed"
    
    def test_tool_call_to_dict(self):
        """Test converting tool call to dictionary."""
        tc = ToolCall(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="success"
        )
        d = tc.to_dict()
        assert d["tool_name"] == "test_tool"
        assert d["arguments"] == {"arg": "value"}
        assert d["result"] == "success"
        assert d["success"] is True


class TestConversationContext:
    """Tests for ConversationContext class."""
    
    def test_context_initialization(self):
        """Test creating a conversation context."""
        context = ConversationContext()
        assert context.messages == []
        assert context.max_tokens == 100000
    
    def test_add_message(self):
        """Test adding messages to context."""
        context = ConversationContext()
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there")
        
        assert len(context.messages) == 2
        assert context.messages[0].role == "user"
        assert context.messages[0].content == "Hello"
        assert context.messages[1].role == "assistant"
        assert context.messages[1].content == "Hi there"
    
    def test_add_tool_call(self):
        """Test adding tool calls to context."""
        context = ConversationContext()
        context.add_message("assistant", "Let me help")
        
        context.add_tool_call(
            tool_name="test_tool",
            arguments={"arg": "value"},
            result="success"
        )
        
        assert len(context.messages) == 1
        assert context.messages[0].tool_calls is not None
        assert len(context.messages[0].tool_calls) == 1
        assert context.messages[0].tool_calls[0].tool_name == "test_tool"
    
    def test_get_messages_for_api(self):
        """Test formatting messages for API calls."""
        context = ConversationContext()
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi")
        
        messages = context.get_messages_for_api()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": "Hi"}
    
    def test_truncate_if_needed(self):
        """Test context truncation when exceeding token limit."""
        context = ConversationContext(max_tokens=100)
        
        # Add system message
        context.add_message("system", "You are a helpful assistant")
        
        # Add many messages to exceed limit
        for i in range(50):
            context.add_message("user", f"Message {i}" * 100)
            context.add_message("assistant", f"Response {i}" * 100)
        
        context.truncate_if_needed()
        
        # Should have kept system message and removed old messages
        assert len(context.messages) > 0
        assert context.messages[0].role == "system"
        
        # Estimate tokens should be under limit
        total_chars = sum(len(msg.content) for msg in context.messages)
        estimated_tokens = total_chars // 4
        assert estimated_tokens <= context.max_tokens
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading conversation history."""
        context = ConversationContext()
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there")
        
        # Save to file
        save_path = tmp_path / "conversation.json"
        context.save(save_path)
        
        assert save_path.exists()
        
        # Load from file
        loaded_context = ConversationContext.load(save_path)
        assert len(loaded_context.messages) == 2
        assert loaded_context.messages[0].content == "Hello"
        assert loaded_context.messages[1].content == "Hi there"


class TestOrchestrator:
    """Tests for Orchestrator class."""
    
    def test_orchestrator_initialization(self):
        """Test creating an orchestrator."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        
        assert orchestrator.provider == "openai"
        assert orchestrator.model == "gpt-5.2"
        assert orchestrator.api_key == "test-key"
        assert isinstance(orchestrator.adapter, OpenAIAdapter)
    
    def test_create_adapter_openai(self):
        """Test creating OpenAI adapter."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        assert isinstance(orchestrator.adapter, OpenAIAdapter)
    
    def test_create_adapter_anthropic(self):
        """Test creating Anthropic adapter."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-key"
        )
        assert isinstance(orchestrator.adapter, AnthropicAdapter)
    
    def test_create_adapter_xai(self):
        """Test creating xAI adapter."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="xai",
            model="grok-4",
            api_key="test-key"
        )
        assert isinstance(orchestrator.adapter, XAIAdapter)
    
    def test_create_adapter_google(self):
        """Test creating Google adapter."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="google",
            model="gemini-2.5-pro",
            api_key="test-key"
        )
        assert isinstance(orchestrator.adapter, GoogleAdapter)
    
    def test_create_adapter_invalid_provider(self):
        """Test error on invalid provider."""
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="Unsupported provider"):
            Orchestrator(
                tool_registry=registry,
                provider="invalid",
                model="test",
                api_key="test-key"
            )
    
    def test_format_tools_for_provider(self):
        """Test formatting tools for different providers."""
        registry = ToolRegistry()
        registry.register(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: "test"
        )
        
        # Test OpenAI format
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        tools = orchestrator._format_tools_for_provider()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "test_tool"
    
    def test_set_system_message(self):
        """Test setting system message."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        
        orchestrator.set_system_message("You are a helpful assistant")
        
        assert len(orchestrator.context.messages) == 1
        assert orchestrator.context.messages[0].role == "system"
        assert orchestrator.context.messages[0].content == "You are a helpful assistant"
    
    def test_save_and_load_conversation(self, tmp_path):
        """Test saving and loading conversation."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        
        orchestrator.context.add_message("user", "Hello")
        orchestrator.context.add_message("assistant", "Hi")
        
        # Save conversation
        save_path = tmp_path / "conversation.json"
        orchestrator.save_conversation(save_path)
        
        assert save_path.exists()
        
        # Load conversation
        orchestrator.load_conversation(save_path)
        assert len(orchestrator.context.messages) == 2
    
    @pytest.mark.asyncio
    async def test_execute_tool_call(self):
        """Test executing a tool call."""
        registry = ToolRegistry()
        
        # Register a test tool
        async def test_tool(arg: str) -> str:
            return f"Result: {arg}"
        
        registry.register(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg": {"type": "string"}
                },
                "required": ["arg"]
            },
            function=test_tool
        )
        
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        
        result = await orchestrator.execute_tool_call(
            "test_tool",
            {"arg": "test"}
        )
        
        assert result == "Result: test"
    
    @pytest.mark.asyncio
    async def test_send_message_with_mock_adapter(self):
        """Test sending a message with mocked adapter."""
        registry = ToolRegistry()
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        
        # Mock the adapter
        mock_response = ProviderResponse(
            content="Hello! How can I help you?",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}
        )
        
        orchestrator.adapter.call_with_tools = AsyncMock(return_value=mock_response)
        
        response = await orchestrator.send_message("Hi")
        
        assert response == "Hello! How can I help you?"
        assert len(orchestrator.context.messages) == 2
        assert orchestrator.context.messages[0].role == "user"
        assert orchestrator.context.messages[1].role == "assistant"
    
    @pytest.mark.asyncio
    async def test_send_message_with_tool_calls(self):
        """Test sending a message that triggers tool calls."""
        registry = ToolRegistry()
        
        # Register a test tool
        async def test_tool(query: str) -> str:
            return f"Search result for: {query}"
        
        registry.register(
            name="search",
            description="Search for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
            function=test_tool
        )
        
        orchestrator = Orchestrator(
            tool_registry=registry,
            provider="openai",
            model="gpt-5.2",
            api_key="test-key"
        )
        
        # Mock the adapter to return tool call first, then final response
        tool_call_response = ProviderResponse(
            content="",
            tool_calls=[{
                "id": "call_123",
                "name": "search",
                "arguments": {"query": "Python"}
            }],
            finish_reason="tool_calls",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        
        final_response = ProviderResponse(
            content="Based on the search results, Python is a programming language.",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 20, "completion_tokens": 12, "total_tokens": 32}
        )
        
        orchestrator.adapter.call_with_tools = AsyncMock(
            side_effect=[tool_call_response, final_response]
        )
        
        response = await orchestrator.send_message("Tell me about Python")
        
        assert "Python is a programming language" in response
        # Should have user message, tool result message, and assistant response
        assert len(orchestrator.context.messages) >= 3


class TestProviderAdapters:
    """Tests for provider adapter initialization."""
    
    def test_openai_adapter_init(self):
        """Test OpenAI adapter initialization."""
        adapter = OpenAIAdapter(api_key="test-key", model="gpt-5.2")
        assert adapter.api_key == "test-key"
        assert adapter.model == "gpt-5.2"
    
    def test_anthropic_adapter_init(self):
        """Test Anthropic adapter initialization."""
        adapter = AnthropicAdapter(api_key="test-key", model="claude-3-opus")
        assert adapter.api_key == "test-key"
        assert adapter.model == "claude-3-opus"
    
    def test_xai_adapter_init(self):
        """Test xAI adapter initialization."""
        adapter = XAIAdapter(api_key="test-key", model="grok-4")
        assert adapter.api_key == "test-key"
        assert adapter.model == "grok-4"
        assert adapter.base_url == "https://api.x.ai/v1"
    
    def test_google_adapter_init(self):
        """Test Google adapter initialization."""
        adapter = GoogleAdapter(api_key="test-key", model="gemini-2.5-pro")
        assert adapter.api_key == "test-key"
        assert adapter.model == "gemini-2.5-pro"
        assert adapter.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
