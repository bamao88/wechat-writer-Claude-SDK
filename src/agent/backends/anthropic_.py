"""Anthropic backend (Anthropic native + MiniMax via Anthropic-compatible endpoint)."""
import os
from typing import Any, List, Optional

from anthropic import Anthropic

from src.agent.backends.base import (
    BackendResponse,
    LLMBackend,
    NormalizedMessage,
    ToolCall,
    ToolDef,
)


def _normalized_to_anthropic_messages(messages: List[NormalizedMessage]) -> List[dict]:
    """Convert normalized messages to Anthropic API format."""
    out: List[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        tool_calls = m.get("tool_calls")

        if role == "user":
            if isinstance(content, list):
                # Tool results: list of {type, tool_use_id, content}
                out.append({"role": "user", "content": content})
            else:
                out.append({"role": "user", "content": str(content) or ""})

        elif role == "assistant":
            blocks: List[dict] = []
            if content:
                blocks.append({"type": "text", "text": str(content)})
            if tool_calls:
                for tc in tool_calls:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "input": tc.get("input") or {},
                    })
            out.append({"role": "assistant", "content": blocks})
    return out


def _tool_def_to_anthropic(tools: List[ToolDef]) -> List[dict]:
    """Convert normalized tool defs to Anthropic tools (name, description, input_schema)."""
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("parameters", {"type": "object", "properties": {}, "required": []}),
        }
        for t in tools
    ]


class AnthropicBackend(LLMBackend):
    """Anthropic API backend. Also used for MiniMax (set base_url + api_key + model in env)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_bearer_auth: Optional[bool] = None,
    ):
        api_key = (api_key or os.getenv("WECHAT_WRITER_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
        base_url = (base_url or os.getenv("WECHAT_WRITER_ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL") or "").rstrip("/").strip()
        self.model = model or os.getenv("WECHAT_WRITER_ANTHROPIC_MODEL") or os.getenv("ANTHROPIC_MODEL") or "claude-haiku-4-5-20251001"
        # MiniMax Anthropic-compatible endpoint requires Authorization: Bearer
        if use_bearer_auth is None:
            use_bearer_auth = (
                os.getenv("MINIMAX_USE_BEARER_AUTH", "").strip().lower() in ("1", "true", "yes")
                or "minimax" in base_url.lower()
            )
        use_bearer_auth = bool(use_bearer_auth and api_key)

        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if use_bearer_auth and api_key:
            kwargs["default_headers"] = {"Authorization": f"Bearer {api_key}"}
        self._client = Anthropic(**kwargs)

    def create(
        self,
        system: str,
        messages: List[NormalizedMessage],
        tools: List[ToolDef],
        max_tokens: int = 8192,
    ) -> BackendResponse:
        anthropic_messages = _normalized_to_anthropic_messages(messages)
        anthropic_tools = _tool_def_to_anthropic(tools)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=anthropic_messages,
            tools=anthropic_tools,
        )

        content_text = ""
        tool_calls_list: List[ToolCall] = []
        for block in response.content:
            if getattr(block, "type", None) == "text" and hasattr(block, "text"):
                content_text += block.text or ""
            elif getattr(block, "type", None) == "tool_use":
                tool_calls_list.append(ToolCall(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    input=getattr(block, "input", None) or {},
                ))

        stop_reason = "tool_use" if response.stop_reason == "tool_use" else "end_turn"
        return BackendResponse(
            content_text=content_text,
            stop_reason=stop_reason,
            tool_calls=tool_calls_list,
        )
