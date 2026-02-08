"""Conversational Orchestrator for LLM-based tool execution.

This module provides the core orchestration system that manages conversations
with LLM APIs and coordinates tool execution. Supports multiple providers:
OpenAI, Anthropic, xAI, and Google.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from vbagent.orchestrator.tools import ToolRegistry


@dataclass
class Message:
    """A single message in a conversation.
    
    Attributes:
        role: Message role (user, assistant, system)
        content: Message content
        timestamp: When the message was created
        tool_calls: Optional list of tool calls made in this message
    """
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: Optional[list[ToolCall]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        d = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.tool_calls:
            d["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> Message:
        """Create from dictionary."""
        tool_calls = None
        if "tool_calls" in data:
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]
        
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool_calls=tool_calls,
        )


@dataclass
class ToolCall:
    """A tool call made by the LLM.
    
    Attributes:
        tool_name: Name of the tool that was called
        arguments: Arguments passed to the tool
        result: Result returned by the tool
        timestamp: When the tool was called
        success: Whether the tool execution succeeded
        error: Error message if execution failed
    """
    tool_name: str
    arguments: dict
    result: Any
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": str(self.result) if self.result is not None else None,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> ToolCall:
        """Create from dictionary."""
        return cls(
            tool_name=data["tool_name"],
            arguments=data["arguments"],
            result=data.get("result"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            success=data.get("success", True),
            error=data.get("error"),
        )


@dataclass
class ProviderResponse:
    """Response from an LLM provider.
    
    Attributes:
        content: Text content of the response
        tool_calls: List of tool calls requested by the LLM
        finish_reason: Reason the generation stopped
        usage: Token usage information
    """
    content: str
    tool_calls: list[dict]
    finish_reason: str
    usage: dict


class ConversationContext:
    """Manages conversation history and context.
    
    Handles message storage, token limit management, and persistence.
    """
    
    def __init__(self, max_tokens: int = 100000):
        """Initialize conversation context.
        
        Args:
            max_tokens: Maximum tokens to keep in history
        """
        self.messages: list[Message] = []
        self.max_tokens = max_tokens
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        message = Message(role=role, content=content)
        self.messages.append(message)
    
    def add_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        result: Any,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Add a tool call to the conversation history.
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments passed to the tool
            result: Result from the tool
            success: Whether execution succeeded
            error: Error message if failed
        """
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            error=error,
        )
        
        # Add to the last assistant message if it exists
        if self.messages and self.messages[-1].role == "assistant":
            if self.messages[-1].tool_calls is None:
                self.messages[-1].tool_calls = []
            self.messages[-1].tool_calls.append(tool_call)
        else:
            # Create a new assistant message with the tool call
            message = Message(
                role="assistant",
                content="",
                tool_calls=[tool_call]
            )
            self.messages.append(message)
    
    def get_messages_for_api(self) -> list[dict]:
        """Get messages formatted for API calls.
        
        Returns:
            List of message dictionaries
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
    
    def truncate_if_needed(self) -> None:
        """Truncate old messages if exceeding token limit.
        
        Preserves system message and recent context.
        """
        # Simple heuristic: ~4 chars per token
        total_chars = sum(len(msg.content) for msg in self.messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= self.max_tokens:
            return
        
        # Keep system message if present
        system_messages = [msg for msg in self.messages if msg.role == "system"]
        other_messages = [msg for msg in self.messages if msg.role != "system"]
        
        # Remove oldest messages until under limit
        while other_messages and estimated_tokens > self.max_tokens:
            removed = other_messages.pop(0)
            estimated_tokens -= len(removed.content) // 4
        
        # Reconstruct message list
        self.messages = system_messages + other_messages
    
    def save(self, path: Path) -> None:
        """Save conversation history to file.
        
        Args:
            path: Path to save the conversation
        """
        data = {
            "max_tokens": self.max_tokens,
            "messages": [msg.to_dict() for msg in self.messages],
        }
        path.write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, path: Path) -> ConversationContext:
        """Load conversation history from file.
        
        Args:
            path: Path to load from
            
        Returns:
            ConversationContext with loaded history
        """
        data = json.loads(path.read_text())
        context = cls(max_tokens=data.get("max_tokens", 100000))
        context.messages = [Message.from_dict(msg) for msg in data["messages"]]
        return context


class ProviderAdapter(ABC):
    """Abstract base class for LLM provider adapters."""
    
    def __init__(self, api_key: str, model: str):
        """Initialize provider adapter.
        
        Args:
            api_key: API key for the provider
            model: Model to use
        """
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def call_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        """Call LLM API with tool definitions.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions in provider format
            
        Returns:
            ProviderResponse with content and tool calls
        """
        pass


class OpenAIAdapter(ProviderAdapter):
    """Adapter for OpenAI API (GPT-5 series)."""
    
    async def call_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        """Call OpenAI API with function calling.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions in OpenAI format
            
        Returns:
            ProviderResponse with content and tool calls
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")
        
        client = AsyncOpenAI(api_key=self.api_key)
        
        # Call API with tools
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
        )
        
        message = response.choices[0].message
        
        # Extract tool calls if present
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        
        return ProviderResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        )


class AnthropicAdapter(ProviderAdapter):
    """Adapter for Anthropic API (Claude)."""
    
    async def call_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        """Call Anthropic API with tool use.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions in Anthropic format
            
        Returns:
            ProviderResponse with content and tool calls
        """
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic package is required for Anthropic provider")
        
        client = AsyncAnthropic(api_key=self.api_key)
        
        # Anthropic requires system message separate
        system_message = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)
        
        # Call API with tools
        kwargs = {
            "model": self.model,
            "messages": user_messages,
            "max_tokens": 4096,
        }
        
        if system_message:
            kwargs["system"] = system_message
        
        if tools:
            kwargs["tools"] = tools
        
        response = await client.messages.create(**kwargs)
        
        # Extract content and tool calls
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })
        
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
        )


class XAIAdapter(ProviderAdapter):
    """Adapter for xAI API (Grok).
    
    xAI uses OpenAI-compatible API format.
    """
    
    def __init__(self, api_key: str, model: str):
        """Initialize xAI adapter.
        
        Args:
            api_key: xAI API key
            model: Grok model to use
        """
        super().__init__(api_key, model)
        self.base_url = "https://api.x.ai/v1"
    
    async def call_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        """Call xAI API with function calling.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions in OpenAI format
            
        Returns:
            ProviderResponse with content and tool calls
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package is required for xAI provider")
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Call API with tools
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
        )
        
        message = response.choices[0].message
        
        # Extract tool calls if present
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        
        return ProviderResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        )


class GoogleAdapter(ProviderAdapter):
    """Adapter for Google API (Gemini)."""
    
    def __init__(self, api_key: str, model: str):
        """Initialize Google adapter.
        
        Args:
            api_key: Google API key
            model: Gemini model to use
        """
        super().__init__(api_key, model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
    
    async def call_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> ProviderResponse:
        """Call Google API with function calling.
        
        Google uses OpenAI-compatible format via their OpenAI compatibility layer.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions in OpenAI format
            
        Returns:
            ProviderResponse with content and tool calls
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package is required for Google provider")
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Call API with tools
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
        )
        
        message = response.choices[0].message
        
        # Extract tool calls if present
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
        
        return ProviderResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        )


class Orchestrator:
    """LLM-based conversation orchestrator.
    
    Manages conversations with LLM APIs and coordinates tool execution.
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider: str,
        model: str,
        api_key: str,
    ):
        """Initialize orchestrator.
        
        Args:
            tool_registry: Registry of available tools
            provider: Provider name (openai, anthropic, xai, google)
            model: Model to use
            api_key: API key for the provider
        """
        self.tool_registry = tool_registry
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.context = ConversationContext()
        
        # Create provider adapter
        self.adapter = self._create_adapter()
    
    def _create_adapter(self) -> ProviderAdapter:
        """Create the appropriate provider adapter.
        
        Returns:
            ProviderAdapter instance
            
        Raises:
            ValueError: If provider is not supported
        """
        if self.provider == "openai":
            return OpenAIAdapter(self.api_key, self.model)
        elif self.provider == "anthropic":
            return AnthropicAdapter(self.api_key, self.model)
        elif self.provider == "xai":
            return XAIAdapter(self.api_key, self.model)
        elif self.provider == "google":
            return GoogleAdapter(self.api_key, self.model)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _format_tools_for_provider(self) -> list[dict]:
        """Format tool definitions for the configured provider.
        
        Returns:
            List of tool definitions in provider format
        """
        if self.provider == "openai":
            return self.tool_registry.get_tool_definitions_openai()
        elif self.provider == "anthropic":
            return self.tool_registry.get_tool_definitions_anthropic()
        elif self.provider == "xai":
            return self.tool_registry.get_tool_definitions_xai()
        elif self.provider == "google":
            return self.tool_registry.get_tool_definitions_google()
        else:
            return []
    
    async def send_message(self, message: str) -> str:
        """Send a user message and get response.
        
        Handles tool calls automatically in a loop until the LLM
        provides a final text response.
        
        Args:
            message: User message
            
        Returns:
            Final assistant response
        """
        # Add user message to context
        self.context.add_message("user", message)
        
        # Truncate if needed
        self.context.truncate_if_needed()
        
        # Get tool definitions
        tools = self._format_tools_for_provider()
        
        # Loop until we get a final response (no more tool calls)
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get messages for API
            messages = self.context.get_messages_for_api()
            
            try:
                # Call LLM API
                response = await self.adapter.call_with_tools(messages, tools)
                
                # If there are tool calls, execute them
                if response.tool_calls:
                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        arguments = tool_call["arguments"]
                        
                        try:
                            # Execute tool
                            result = await self.execute_tool_call(tool_name, arguments)
                            
                            # Add tool call to context
                            self.context.add_tool_call(
                                tool_name=tool_name,
                                arguments=arguments,
                                result=result,
                                success=True
                            )
                            
                            # Add tool result as a user message for the next iteration
                            result_str = json.dumps(result) if not isinstance(result, str) else result
                            self.context.add_message(
                                "user",
                                f"Tool '{tool_name}' returned: {result_str}"
                            )
                            
                        except Exception as e:
                            # Add failed tool call to context
                            error_msg = str(e)
                            self.context.add_tool_call(
                                tool_name=tool_name,
                                arguments=arguments,
                                result=None,
                                success=False,
                                error=error_msg
                            )
                            
                            # Add error as a user message
                            self.context.add_message(
                                "user",
                                f"Tool '{tool_name}' failed with error: {error_msg}"
                            )
                    
                    # Continue loop to get next response
                    continue
                
                # No tool calls, we have a final response
                if response.content:
                    self.context.add_message("assistant", response.content)
                    return response.content
                else:
                    # Empty response, shouldn't happen but handle it
                    return ""
                    
            except Exception as e:
                # API call failed
                error_msg = f"API call failed: {str(e)}"
                self.context.add_message("assistant", error_msg)
                return error_msg
        
        # Max iterations reached
        error_msg = "Maximum tool call iterations reached"
        self.context.add_message("assistant", error_msg)
        return error_msg
    
    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: dict
    ) -> Any:
        """Execute a tool call and return result.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
            
        Raises:
            Exception: If tool execution fails
        """
        return await self.tool_registry.execute(tool_name, arguments)
    
    def set_system_message(self, message: str) -> None:
        """Set or update the system message.
        
        Args:
            message: System message content
        """
        # Remove existing system messages
        self.context.messages = [
            msg for msg in self.context.messages
            if msg.role != "system"
        ]
        
        # Add new system message at the beginning
        system_msg = Message(role="system", content=message)
        self.context.messages.insert(0, system_msg)
    
    def save_conversation(self, path: Path) -> None:
        """Save conversation history to file.
        
        Args:
            path: Path to save the conversation
        """
        self.context.save(path)
    
    def load_conversation(self, path: Path) -> None:
        """Load conversation history from file.
        
        Args:
            path: Path to load from
        """
        self.context = ConversationContext.load(path)



def create_orchestrator_from_config(
    tool_registry: ToolRegistry,
    agent_type: str = "default",
) -> Orchestrator:
    """Create an orchestrator using vbagent configuration.
    
    Reads provider, model, and API key from vbagent config system.
    
    Args:
        tool_registry: Registry of available tools
        agent_type: Agent type for config lookup (default uses orchestrator settings)
        
    Returns:
        Configured Orchestrator instance
        
    Raises:
        ValueError: If configuration is invalid or API key is missing
    """
    from vbagent.config import get_config, PROVIDERS
    
    config = get_config()
    
    # Determine provider from base_url
    provider = "openai"  # Default
    if config.base_url:
        for name, info in PROVIDERS.items():
            if info["base_url"] and config.base_url.rstrip("/") == info["base_url"].rstrip("/"):
                provider = name
                break
    
    # Get model for agent type
    model = config.get_model(agent_type)
    
    # Get API key - priority: config.api_key > provider env var > OPENAI_API_KEY
    api_key = config.api_key
    if not api_key:
        # Try provider-specific env var
        if provider in PROVIDERS:
            env_key = PROVIDERS[provider]["env_key"]
            api_key = os.environ.get(env_key)
        
        # Fallback to OPENAI_API_KEY
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            f"No API key found for provider '{provider}'. "
            f"Set {PROVIDERS.get(provider, {}).get('env_key', 'OPENAI_API_KEY')} environment variable "
            "or configure api_key in vbagent config."
        )
    
    return Orchestrator(
        tool_registry=tool_registry,
        provider=provider,
        model=model,
        api_key=api_key,
    )
