#!/usr/bin/env python3
"""AI Writing Assistant - CLI Entry Point.

Usage:
    python main.py "选题"
    python main.py "AI产品经理职业发展"

Output (Phase 3): output/YYYY-MM-DD_HHMMSS_topic-slug_model-slug_shortid/
  - thought_trace.md  (workflow trace)
  - article.md        (final article)
  (model-slug 为当前 LLM 模型名，如 MiniMax-M2-1、gpt-4o)
"""
import os
import sys

from src.cli import parse_args, CLIError
from src.config import load_config, ConfigError
from src.utils import setup_logger, get_logger
from src.agent import run_agent
from src.agent.backends import get_model_name
from src.output import create_output_dir, OutputTracer


def print_progress(message: str) -> None:
    """Print progress message to console."""
    print(message)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        cli_result = parse_args(sys.argv)
    except SystemExit as e:
        if e.code == 0:
            return 0
        return 1
    except CLIError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    try:
        config = load_config()
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1

    setup_logger(config.log_level)
    log = get_logger(__name__)
    log.info(f"选题: {cli_result.topic}")

    # Create output directory (Phase 3: fail fast; include model name in dir)
    output_base = os.getenv("OUTPUT_DIR", "output")
    model_name = get_model_name(config.llm_provider)
    try:
        run_dir = create_output_dir(cli_result.topic, base_dir=output_base, model_name=model_name)
    except OSError as e:
        print(f"无法创建输出目录: {e}", file=sys.stderr)
        return 1

    tracer = OutputTracer(run_dir)
    tracer.start()

    print_progress(f"[选题] {cli_result.topic}")
    print_progress(f"[输出] {run_dir}")

    result = run_agent(
        topic=cli_result.topic,
        config=config,
        on_progress=print_progress,
        tracer=tracer
    )

    if result.success:
        print("\n" + "=" * 50)
        print("Agent 输出:")
        print("=" * 50)
        print(result.output)
        print("=" * 50)
        print(f"工具调用次数: {result.tool_calls}")
        print(f"输出目录: {run_dir}")
        return 0
    else:
        print(f"\n执行失败: {result.error}", file=sys.stderr)
        tracer.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
