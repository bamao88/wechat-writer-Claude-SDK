#!/usr/bin/env python3
"""单独测试 NotebookLM 工具是否已认证、能否返回结果。

用法（在项目根目录）:
  .venv/bin/python scripts/test_notebooklm_tool.py

需要 .env 中配置: NOTEBOOK_ID, NOTEBOOK_URL；且已在 notebooklm_skill 下执行过 auth_manager.py setup。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from src.config.settings import load_config
    from src.tools.notebooklm import NotebookLMTool

    try:
        config = load_config()
    except Exception as e:
        print(f"配置加载失败: {e}")
        sys.exit(1)

    tool = NotebookLMTool(config)
    query = "简要总结本笔记本的主题或内容（一两句即可）"
    print(f"调用 NotebookLM: query={query!r}")
    print("(可能需 30–90 秒，会启动浏览器…)")
    result = tool.execute(query)

    if result.success:
        print("\n✅ NotebookLM 工具调用成功")
        print(f"内容预览: {(result.content or '')[:300]}...")
    else:
        print("\n❌ NotebookLM 工具调用失败")
        print(result.error or result.content)
        sys.exit(1)

if __name__ == "__main__":
    main()
