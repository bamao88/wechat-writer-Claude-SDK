"""OpenAI backend (OpenAI API and OpenAI-compatible endpoints)."""
import json
import os
from typing import Any, List, Optional

from openai import OpenAI

from src.agent.backends.base import (
    BackendResponse,
    LLMBackend,
    NormalizedMessage,
    ToolCall,
    ToolDef,
)


def _normalized_to_openai_messages(messages: List[NormalizedMessage]) -> List[dict]:
    """Convert normalized messages to OpenAI chat format (role + content or tool_calls)."""
    out: List[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        tool_calls = m.get("tool_calls")

        if role == "user":
            if isinstance(content, list):
                # Tool results: OpenAI uses multiple messages with role "tool"
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        out.append({
                            "role": "tool",
                            "tool_call_id": item.get("tool_use_id", ""),
                            "content": item.get("content", ""),
                        })
            else:
                out.append({"role": "user", "content": str(content) or ""})

        elif role == "assistant":
            msg: dict = {"role": "assistant", "content": (str(content) or "") if content else ""}
            if tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("input") or {}, ensure_ascii=False),
                        },
                    }
                    for tc in tool_calls
                ]
            out.append(msg)
    return out


def _tool_def_to_openai(tools: List[ToolDef]) -> List[dict]:
    """Convert normalized tool defs to OpenAI tools (type: function, function: name, description, parameters)."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {"type": "object", "properties": {}, "required": []}),
            },
        }
        for t in tools
    ]


class OpenAIBackend(LLMBackend):
    """OpenAI API backend (and OpenAI-compatible third-party endpoints)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        api_key = (api_key or os.getenv("WECHAT_WRITER_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        base_url = (base_url or os.getenv("WECHAT_WRITER_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").rstrip("/").strip()
        self.model = model or os.getenv("WECHAT_WRITER_OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o"

        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    def create(
        self,
        system: str,
        messages: List[NormalizedMessage],
        tools: List[ToolDef],
        max_tokens: int = 8192,
    ) -> BackendResponse:
        openai_messages: List[dict] = [{"role": "system", "content": system}]
        openai_messages.extend(_normalized_to_openai_messages(messages))
        openai_tools = _tool_def_to_openai(tools)

        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=openai_messages,
            tools=openai_tools,
        )

        choice = response.choices[0] if response.choices else None
        if not choice:
            return BackendResponse(content_text="", stop_reason="end_turn", tool_calls=[])

        msg = choice.message
        content_text = (msg.content or "").strip()
        finish = getattr(choice, "finish_reason", None) or ""

        tool_calls_list: List[ToolCall] = []
        for tc in getattr(msg, "tool_calls", None) or []:
            fid = getattr(tc, "id", "") or ""
            fn = getattr(tc, "function", None)
            name = getattr(fn, "name", "") if fn else ""
            args_str = getattr(fn, "arguments", "") if fn else "{}"
            try:
                inp = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                inp = {}
            tool_calls_list.append(ToolCall(id=fid, name=name, input=inp))

        stop_reason = "tool_use" if (finish == "tool_calls" and tool_calls_list) else "end_turn"
        return BackendResponse(
            content_text=content_text,
            stop_reason=stop_reason,
            tool_calls=tool_calls_list,
        )
