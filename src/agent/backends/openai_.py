"""OpenAI backend (OpenAI API, OpenAI-compatible endpoints, Azure Responses API)."""
import json
import os
from typing import Any, List, Optional
from urllib.parse import urlparse, parse_qs, urlunparse

from openai import OpenAI

from src.agent.backends.base import (
    BackendResponse,
    LLMBackend,
    NormalizedMessage,
    ToolCall,
    ToolDef,
)


def _is_azure_responses_url(base_url: str) -> bool:
    """True 表示 Azure Responses API（/openai/responses），需用 responses.create()。"""
    return bool(base_url and "/openai/responses" in base_url)


def _is_continuation_with_tool_results(messages: List[NormalizedMessage]) -> bool:
    """是否为「上一轮 tool_use 后的续传」：至少 3 条，最后一条是 user 且含 tool_result。"""
    if len(messages) < 3:
        return False
    last = messages[-1]
    if last.get("role") != "user":
        return False
    content = last.get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(it, dict) and it.get("type") == "tool_result" for it in content)


def _responses_input_tool_outputs_only(messages: List[NormalizedMessage]) -> List[dict]:
    """从最后一条 user（tool_result）消息中抽出 function_call_output 列表。"""
    out: List[dict] = []
    last = messages[-1] if messages else {}
    content = last.get("content") if isinstance(last.get("content"), list) else []
    for it in content:
        if isinstance(it, dict) and it.get("type") == "tool_result":
            out.append({
                "type": "function_call_output",
                "call_id": it.get("tool_use_id", ""),
                "output": it.get("content", ""),
            })
    return out


def _normalized_to_responses_input(messages: List[NormalizedMessage]) -> Any:
    """归一化消息 → Azure Responses API 的 input（首轮单条用户消息用字符串，多轮用数组）。"""
    if not messages:
        return None
    if len(messages) == 1 and messages[0].get("role") == "user":
        c = messages[0].get("content", "")
        if isinstance(c, str):
            return c
    items: List[dict] = []
    for m in messages:
        role, content, tool_calls = m.get("role"), m.get("content"), m.get("tool_calls")
        if role == "user":
            if isinstance(content, list):
                for it in content:
                    if isinstance(it, dict) and it.get("type") == "tool_result":
                        items.append({
                            "type": "function_call_output",
                            "call_id": it.get("tool_use_id", ""),
                            "output": it.get("content", ""),
                        })
            else:
                items.append({"role": "user", "content": str(content) or ""})
        elif role == "assistant":
            # 多轮 input 里 assistant 只允许 output_text 等类型，不能带 function_call（API 会 400）
            parts = []
            if content:
                parts.append({"type": "output_text", "text": str(content)})
            if not parts:
                parts = [{"type": "output_text", "text": ""}]
            items.append({
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": parts,
            })
    return items if items else None


def _parse_responses_output(response: Any) -> BackendResponse:
    """解析 responses.create() 返回。output 为扁平列表，含 type=reasoning、type=function_call 等。"""
    content_text = ""
    tool_calls_list: List[ToolCall] = []
    output = getattr(response, "output", None) or []

    def _get(o: Any, key: str, default: Any = None) -> Any:
        if isinstance(o, dict):
            return o.get(key, default)
        return getattr(o, key, default)

    def _to_dict(o: Any) -> dict:
        if isinstance(o, dict):
            return o
        if hasattr(o, "model_dump"):
            try:
                return o.model_dump()
            except Exception:
                pass
        return {}

    for item in output:
        item = _to_dict(item)
        if not item:
            continue
        typ = _get(item, "type", "")
        if typ == "function_call":
            args_raw = _get(item, "arguments") or "{}"
            if not isinstance(args_raw, str):
                args_raw = json.dumps(args_raw) if args_raw else "{}"
            try:
                inp = json.loads(args_raw)
            except json.JSONDecodeError:
                inp = {}
            tool_calls_list.append(ToolCall(
                id=_get(item, "call_id") or _get(item, "id") or "",
                name=_get(item, "name") or "",
                input=inp,
            ))
            continue
        if typ == "reasoning":
            continue
        if typ != "message" or _get(item, "role") != "assistant":
            continue
        content = _get(item, "content") or []
        if not isinstance(content, list):
            content = [content] if content else []
        for block in content:
            block = _to_dict(block)
            if not block:
                continue
            btyp = _get(block, "type", "")
            if btyp == "output_text":
                content_text += (_get(block, "text") or "") or ""
            elif btyp == "function_call":
                args_raw = _get(block, "arguments") or "{}"
                if not isinstance(args_raw, str):
                    args_raw = json.dumps(args_raw) if args_raw else "{}"
                try:
                    inp = json.loads(args_raw)
                except json.JSONDecodeError:
                    inp = {}
                tool_calls_list.append(ToolCall(
                    id=_get(block, "call_id") or "",
                    name=_get(block, "name") or "",
                    input=inp,
                ))

    return BackendResponse(
        content_text=content_text.strip(),
        stop_reason="tool_use" if tool_calls_list else "end_turn",
        tool_calls=tool_calls_list,
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
    """OpenAI API backend (含 Azure Responses API：base_url 含 /openai/responses 时走 responses.create)。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        api_key = (api_key or os.getenv("WECHAT_WRITER_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        base_url = (base_url or os.getenv("WECHAT_WRITER_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").rstrip("/").strip()
        self.model = model or os.getenv("WECHAT_WRITER_OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o"
        self._use_responses_api = _is_azure_responses_url(base_url)

        self._last_response_id: Optional[str] = None  # Responses API 续传用
        if self._use_responses_api and base_url and "openai.azure.com" in base_url:
            parsed = urlparse(base_url)
            path = (parsed.path or "").rstrip("/")
            if path.endswith("/responses"):
                path = path[: -len("/responses")]
            qs = parse_qs(parsed.query)
            api_ver = qs.get("api-version", ["2025-04-01-preview"])[0] if qs else "2025-04-01-preview"
            base_url = urlunparse((parsed.scheme, parsed.netloc, path or "/", "", "", "")).rstrip("/")
            self._client = OpenAI(api_key=api_key, base_url=base_url, default_query={"api-version": api_ver})
        else:
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
        if self._use_responses_api:
            tools_payload = [
                {"type": "function", "name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {"type": "object", "properties": {}, "required": []})}
                for t in tools
            ]
            kwargs: dict = {"model": self.model, "instructions": system, "max_output_tokens": max_tokens}
            # 续传：用 previous_response_id + 仅 function_call_output，否则 API 报 "No tool call found for function call output"
            if self._last_response_id and _is_continuation_with_tool_results(messages):
                tool_outputs = _responses_input_tool_outputs_only(messages)
                if tool_outputs:
                    kwargs["previous_response_id"] = self._last_response_id
                    kwargs["input"] = tool_outputs
            else:
                input_items = _normalized_to_responses_input(messages)
                if input_items is not None:
                    kwargs["input"] = input_items
            if tools_payload:
                kwargs["tools"] = tools_payload
            response = self._client.responses.create(**kwargs)
            self._last_response_id = getattr(response, "id", None) or ""
            return _parse_responses_output(response)

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
