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
    provider: Optional[str]  # openai | anthropic，None 表示用 .env
    model: Optional[str]     # 模型名，None 表示用 .env
    flow: str = "hub-spoke"  # hub-spoke | insight-alignment


def parse_args(argv: Optional[List[str]] = None) -> CLIResult:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments (defaults to sys.argv).
              Expected format: ["python", "main.py", "选题"] 或带 --provider/--model

    Returns:
        CLIResult with topic, optional provider and model.

    Raises:
        CLIError: If arguments are invalid.
        SystemExit: If -h/--help is passed.
    """
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="AI写作助手 - 基于NotebookLM资料生成文章",
        epilog=(
            "示例:\n"
            "  python main.py \"AI产品经理职业发展\"  # 默认使用 hub-spoke 流程\n"
            "  python main.py --flow insight-alignment \"如何提升个人品牌\"  # 使用旧流程\n"
            "  python main.py --provider openai --model gpt-5.2-chat \"选题\"\n"
            "  python main.py -p openai -m gpt-4o \"选题\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "topic",
        nargs="?",  # Optional to handle missing case manually
        help="文章选题（必需）"
    )
    parser.add_argument(
        "-p", "--provider",
        choices=["openai", "anthropic"],
        default=None,
        help="LLM 提供商：openai（含 Azure）或 anthropic；不填则用 .env 中 LLM_PROVIDER"
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="模型名称（如 gpt-5.2-chat、gpt-4o）；不填则用 .env 中对应 provider 的 MODEL"
    )
    parser.add_argument(
        "-f", "--flow",
        choices=["insight-alignment", "hub-spoke"],
        default="hub-spoke",
        help="写作流程：hub-spoke（默认，自动化+质量循环）或 insight-alignment（洞察对齐）"
    )

    # Parse args, skipping script name
    # When called from test: argv = ['py', 'main.py', 'topic'] -> skip 2
    # When called from script: argv = ['main.py', 'topic'] -> skip 1
    # Default to sys.argv if not provided
    if argv is None:
        argv = sys.argv

    # Determine how many elements to skip
    if len(argv) > 2 and argv[1].endswith('.py'):
        # Looks like ['python', 'main.py', ...] from test
        args_to_parse = argv[2:]
    elif len(argv) > 0:
        # Looks like ['main.py', ...] from script execution
        args_to_parse = argv[1:]
    else:
        args_to_parse = []

    # Handle help flag early - argparse will print help and exit with 0
    if "-h" in args_to_parse or "--help" in args_to_parse:
        parser.print_help()
        raise SystemExit(0)

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

    provider = (parsed.provider or "").strip() or None
    model = (parsed.model or "").strip() or None
    flow = parsed.flow or "hub-spoke"

    return CLIResult(topic=topic, provider=provider, model=model, flow=flow)

