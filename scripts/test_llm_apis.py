#!/usr/bin/env python3
"""Test OpenAI and MiniMax (Anthropic-compatible) backends with real API calls."""
import os
import sys

# Load .env before importing backends (they read env in __init__)
from dotenv import load_dotenv
load_dotenv()

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.backends.openai_ import OpenAIBackend
from src.agent.backends.anthropic_ import AnthropicBackend


# Minimal tool def for search_notebooklm (same schema as NotebookLMTool)
SEARCH_TOOL = {
    "name": "search_notebooklm",
    "description": "搜索 NotebookLM 笔记本中的资料。",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "搜索问题"}},
        "required": ["query"],
    },
}


def test_openai():
    """Test OpenAI backend (OPENAI_* or WECHAT_WRITER_OPENAI_* from .env)."""
    print("=" * 50)
    print("测试 OpenAI 后端")
    print("=" * 50)
    api_key = os.getenv("WECHAT_WRITER_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("WECHAT_WRITER_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    model = os.getenv("WECHAT_WRITER_OPENAI_MODEL") or os.getenv("OPENAI_MODEL")
    if not api_key:
        print("跳过: 未设置 OPENAI_API_KEY 或 WECHAT_WRITER_OPENAI_API_KEY")
        return False
    print(f"  base_url: {base_url or '(默认)'}")
    print(f"  model: {model or '(默认)'}")
    backend = OpenAIBackend(api_key=api_key, base_url=base_url, model=model)
    messages = [{"role": "user", "content": "用一句话介绍你自己，并说明你现在能否调用工具。"}]
    try:
        resp = backend.create(
            system="你是一个助手。",
            messages=messages,
            tools=[SEARCH_TOOL],
            max_tokens=256,
        )
        print(f"  stop_reason: {resp.stop_reason}")
        print(f"  content_text: {resp.content_text[:200]}..." if len(resp.content_text) > 200 else f"  content_text: {resp.content_text}")
        print(f"  tool_calls: {len(resp.tool_calls)}")
        print("OpenAI 后端测试通过。")
        return True
    except Exception as e:
        print(f"OpenAI 后端测试失败: {e}")
        print("  提示: 404 多为 base_url 或 model 与当前端点不匹配，请核对第三方/Azure 文档。")
        return False


def test_minimax():
    """Test MiniMax via Anthropic-compatible endpoint (MINIMAX_* from .env)."""
    print("=" * 50)
    print("测试 MiniMax（Anthropic 兼容）后端")
    print("=" * 50)
    api_key = os.getenv("MINIMAX_API_KEY")
    # Anthropic-compatible endpoint: https://platform.minimaxi.com/docs/api-reference/text-anthropic-api
    base_url = os.getenv("MINIMAX_ANTHROPIC_BASE_URL") or "https://api.minimaxi.com/anthropic"
    model = os.getenv("MINIMAX_MODEL") or "MiniMax-M2.1"
    if not api_key:
        print("跳过: 未设置 MINIMAX_API_KEY")
        return False
    print(f"  base_url: {base_url}")
    print(f"  model: {model}")
    # MiniMax Anthropic-compatible 常要求 Authorization: Bearer
    backend = AnthropicBackend(api_key=api_key, base_url=base_url, model=model, use_bearer_auth=True)
    messages = [{"role": "user", "content": "用一句话介绍你自己，并说明你现在能否调用工具。"}]
    try:
        resp = backend.create(
            system="你是一个助手。",
            messages=messages,
            tools=[SEARCH_TOOL],
            max_tokens=256,
        )
        print(f"  stop_reason: {resp.stop_reason}")
        print(f"  content_text: {resp.content_text[:200]}..." if len(resp.content_text) > 200 else f"  content_text: {resp.content_text}")
        print(f"  tool_calls: {len(resp.tool_calls)}")
        print("MiniMax 后端测试通过。")
        return True
    except Exception as e:
        print(f"MiniMax 后端测试失败: {e}")
        print("  提示: 401 多为 API Key 无效或 base_url 不对。Anthropic 兼容端点为 https://api.minimaxi.com/anthropic 或 https://api.minimax.io/anthropic，需用对应平台的 Key。")
        return False


def main():
    ok_openai = test_openai()
    print()
    ok_minimax = test_minimax()
    print()
    print("=" * 50)
    if ok_openai and ok_minimax:
        print("全部通过")
    else:
        print(f"OpenAI: {'通过' if ok_openai else '失败'}; MiniMax: {'通过' if ok_minimax else '失败'}")
    sys.exit(0 if (ok_openai and ok_minimax) else 1)


if __name__ == "__main__":
    main()
