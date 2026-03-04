#!/usr/bin/env python3
"""Hub-Spoke 流程真实 API 测试脚本。

测试场景：
1. 使用真实的 OpenAI/Azure API
2. 可选：使用真实的 NotebookLM（如果已认证）
3. 完整的 Hub-Spoke 流程

用法：
    python scripts/test_hub_spoke_real_api.py [--provider openai|anthropic] [--skip-notebooklm]
"""
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import load_config
from src.agent.hub_spoke.flow import run_hub_spoke_flow
from src.output import create_output_dir, OutputTracer
from src.agent.backends import get_model_name
from src.utils import setup_logger, get_logger


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_progress(message: str):
    """Print progress message."""
    print(f"[进度] {message}")


def main():
    parser = argparse.ArgumentParser(description="Hub-Spoke 真实 API 测试")
    parser.add_argument(
        "-p", "--provider",
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider (default: openai)"
    )
    parser.add_argument(
        "--skip-notebooklm",
        action="store_true",
        help="Skip NotebookLM tool (useful if not authenticated)"
    )
    parser.add_argument(
        "-t", "--topic",
        default="如何提升个人品牌",
        help="测试选题 (default: 如何提升个人品牌)"
    )
    args = parser.parse_args()

    print_section("Hub-Spoke 流程真实 API 测试")

    # 1. 设置 provider
    os.environ["LLM_PROVIDER"] = args.provider
    print(f"✓ LLM Provider: {args.provider}")

    # 2. 加载配置
    try:
        config = load_config()
        print(f"✓ 配置加载成功")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return 1

    # 3. 设置日志
    setup_logger(config.log_level)
    log = get_logger(__name__)

    # 4. 检查 NotebookLM
    if args.skip_notebooklm:
        print("⚠️  跳过 NotebookLM（可能影响 Miner Worker）")
    else:
        if config.notebook_id:
            print(f"✓ NotebookLM 已配置: {config.notebook_id[:8]}...")
        else:
            print("⚠️  NotebookLM 未配置")

    # 5. 创建输出目录
    output_base = os.getenv("OUTPUT_DIR", "output")
    model_name = get_model_name(config.llm_provider)
    print(f"✓ 使用模型: {model_name}")

    try:
        run_dir = create_output_dir(args.topic, base_dir=output_base, model_name=model_name)
        print(f"✓ 输出目录: {run_dir}")
    except OSError as e:
        print(f"✗ 创建输出目录失败: {e}")
        return 1

    # 6. 初始化 Tracer
    tracer = OutputTracer(run_dir)
    tracer.start()

    # 7. 执行 Hub-Spoke 流程
    print_section("执行 Hub-Spoke 流程")
    print(f"选题: {args.topic}")
    print(f"流程: Planner → Miner/Web → Orchestrator → Writer → Critic")
    print()

    try:
        result = run_hub_spoke_flow(
            topic=args.topic,
            user_context="",  # 空上下文，触发调研
            config=config,
            on_progress=print_progress,
            tracer=tracer,
        )

        # 8. 输出结果
        print_section("执行结果")

        if result.success:
            print("✓ 流程执行成功")
            print(f"✓ 工具调用次数: {result.tool_calls}")
            print(f"✓ 输出状态: {'降级输出' if result.degraded else '正常输出'}")

            if result.degraded:
                print("\n⚠️  警告：输出未达质量标准（已保存降级版本）")

            print_section("文章内容预览")
            # 显示前 500 字符
            preview = result.output[:500] + ("..." if len(result.output) > 500 else "")
            print(preview)

            print_section("完整输出")
            print(f"文章: {run_dir}/article.md")
            print(f"轨迹: {run_dir}/thought_trace.md")
            print(f"\n查看完整文章:")
            print(f"  cat {run_dir}/article.md")
            print(f"\n查看流程轨迹:")
            print(f"  cat {run_dir}/thought_trace.md")

            return 0
        else:
            print(f"✗ 流程执行失败: {result.error}")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 130
    except Exception as e:
        print(f"\n✗ 执行出错: {e}")
        log.error("Hub-Spoke 测试失败", exc_info=True)
        return 1
    finally:
        tracer.close()


if __name__ == "__main__":
    sys.exit(main())
