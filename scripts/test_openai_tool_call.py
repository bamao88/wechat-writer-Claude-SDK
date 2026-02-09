#!/usr/bin/env python3
"""单独测试 OpenAI（含 Azure Responses API）工具调用往返，不依赖 NotebookLM。

用法（在项目根目录）:
  LLM_PROVIDER=openai .venv/bin/python scripts/test_openai_tool_call.py

需要 .env 中配置: OPENAI_API_KEY, OPENAI_BASE_URL（可选）, OPENAI_MODEL（可选）
"""
import os
import sys

# 确保项目根在 path 并加载 .env，不依赖 load_config（避免 NOTEBOOK_ID 等）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# 强制使用 OpenAI，便于单独测
os.environ["LLM_PROVIDER"] = "openai"

from src.agent.backends import get_backend
from src.agent.backends.base import BackendResponse


# 简单工具定义：与 NotebookLM 无关，仅验证 API 工具往返
GET_WEATHER_TOOL = {
    "name": "get_weather",
    "description": "查询指定城市的当前天气。",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "城市名，如 北京、上海"},
        },
        "required": ["location"],
    },
}


def main() -> None:
    backend = get_backend("openai")
    system = "你是一个助手。当用户问天气时，你必须先调用 get_weather 工具获取数据，再根据结果用一句话总结回复。"
    messages = [{"role": "user", "content": "北京今天天气怎么样？请先查天气再总结。"}]
    tools = [GET_WEATHER_TOOL]

    print("=== 第 1 轮：期望模型返回 tool_use (get_weather) ===\n")
    r1: BackendResponse = backend.create(
        system=system,
        messages=messages,
        tools=tools,
        max_tokens=1024,
    )
    print(f"stop_reason: {r1.stop_reason}")
    print(f"content_text: {r1.content_text[:200] if r1.content_text else '(空)'}...")
    print(f"tool_calls: {len(r1.tool_calls)}")
    for tc in r1.tool_calls:
        print(f"  - {tc.name}(id={tc.id}) input={tc.input}")

    if r1.stop_reason != "tool_use" or not r1.tool_calls:
        print("\n未得到工具调用，请检查模型/接口是否支持 tool calling。")
        sys.exit(1)

    # 模拟执行工具并拼装第二轮消息
    tool_results = []
    assistant_tool_calls = [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in r1.tool_calls]
    for tc in r1.tool_calls:
        # 不调用真实 NotebookLM，直接返回模拟结果
        mock_output = "北京今天晴，气温 15°C，微风。"
        tool_results.append({"type": "tool_result", "tool_use_id": tc.id, "content": mock_output})

    messages.append({"role": "assistant", "content": r1.content_text, "tool_calls": assistant_tool_calls})
    messages.append({"role": "user", "content": tool_results})

    print("\n=== 第 2 轮：传入 function_call_output，期望 end_turn 与总结 ===\n")
    r2: BackendResponse = backend.create(
        system=system,
        messages=messages,
        tools=tools,
        max_tokens=1024,
    )
    print(f"stop_reason: {r2.stop_reason}")
    print(f"content_text:\n{r2.content_text}")

    if r2.stop_reason != "end_turn":
        print("\n第二轮未得到 end_turn，可能续传或解析异常。")
        sys.exit(1)

    print("\n=== OpenAI 工具调用往返测试通过 ===")


if __name__ == "__main__":
    main()
