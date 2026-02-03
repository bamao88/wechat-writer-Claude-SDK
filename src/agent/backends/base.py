"""LLM backend abstraction: unified interface for Anthropic, OpenAI, etc."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Literal

# Normalized tool: name, description, parameters (JSON Schema)
ToolDef = Dict[str, Any]

# Normalized message: user / assistant (with optional tool_calls) / user with tool_result list
NormalizedMessage = Dict[str, Any]

# Single tool call: id, name, input (parsed dict)
@dataclass
class ToolCall:
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class BackendResponse:
    """Unified response from any backend."""
    content_text: str
    stop_reason: Literal["end_turn", "tool_use"]
    tool_calls: List[ToolCall]


class LLMBackend(ABC):
    """Abstract LLM backend: create(system, messages, tools) -> BackendResponse."""

    @abstractmethod
    def create(
        self,
        system: str,
        messages: List[NormalizedMessage],
        tools: List[ToolDef],
        max_tokens: int = 8192,
    ) -> BackendResponse:
        """Call the model; return normalized content, stop_reason, and tool_calls."""
        pass
