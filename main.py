#!/usr/bin/env python3
"""AI Writing Assistant - CLI Entry Point.

Usage:
    python main.py "选题"
    python main.py "AI产品经理职业发展"

This is Phase 1: Foundation Setup.
- Validates CLI can receive topic
- Validates Agent can call NotebookLM tool
- Validates Agent receives search results
"""
import sys

from src.cli import parse_args, CLIError
from src.config import load_config, ConfigError
from src.utils import setup_logger, get_logger
from src.agent import run_agent


def print_progress(message: str) -> None:
    """Print progress message to console.

    Args:
        message: Progress message to display.
    """
    print(message)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Parse CLI arguments
    try:
        cli_result = parse_args(sys.argv)
    except SystemExit as e:
        # Re-raise help exits (code 0)
        if e.code == 0:
            return 0
        return 1
    except CLIError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # Load configuration
    try:
        config = load_config()
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1

    # Setup logging
    logger = setup_logger(config.log_level)
    log = get_logger(__name__)

    log.info(f"选题: {cli_result.topic}")

    # Run agent
    print_progress(f"[选题] {cli_result.topic}")

    result = run_agent(
        topic=cli_result.topic,
        config=config,
        on_progress=print_progress
    )

    if result.success:
        print("\n" + "="*50)
        print("Agent 输出:")
        print("="*50)
        print(result.output)
        print("="*50)
        print(f"工具调用次数: {result.tool_calls}")
        return 0
    else:
        print(f"\n执行失败: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
