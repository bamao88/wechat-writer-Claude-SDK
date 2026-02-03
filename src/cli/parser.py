"""CLI argument parsing for the writing assistant."""
import argparse
import sys
from dataclasses import dataclass
from typing import List, Optional


class CLIError(Exception):
    """Raised when CLI arguments are invalid."""
    pass


@dataclass
class CLIResult:
    """Result of CLI argument parsing."""
    topic: str


def parse_args(argv: Optional[List[str]] = None) -> CLIResult:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments (defaults to sys.argv).
              Expected format: ["python", "main.py", "选题"]

    Returns:
        CLIResult with parsed topic.

    Raises:
        CLIError: If arguments are invalid.
        SystemExit: If -h/--help is passed.
    """
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="AI写作助手 - 基于NotebookLM资料生成文章",
        epilog="示例: python main.py \"AI产品经理职业发展\"",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "topic",
        nargs="?",  # Optional to handle missing case manually
        help="文章选题（必需）"
    )

    # Parse args, skipping the first element if it looks like python/script
    args_to_parse = argv[2:] if argv and len(argv) > 1 else []

    try:
        parsed = parser.parse_args(args_to_parse)
    except SystemExit as e:
        # Re-raise help exits
        if e.code == 0:
            raise
        raise CLIError("参数解析失败，请使用 -h 查看帮助")

    # Validate topic
    if parsed.topic is None:
        raise CLIError("错误：缺少必需的参数 - 选题\n用法: python main.py \"选题\"")

    # Strip and validate non-empty
    topic = parsed.topic.strip()
    if not topic:
        raise CLIError("错误：选题不能为空，请提供有效的文章主题")

    return CLIResult(topic=topic)


def main():
    """Main entry point for CLI testing."""
    try:
        result = parse_args(sys.argv)
        print(f"选题: {result.topic}")
    except CLIError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
