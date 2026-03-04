#!/usr/bin/env python3
"""AI 写作助手 - 命令行入口。

支持两种流程：
1. hub-spoke（默认）：Planner → Miner/Web → Orchestrator → Writer → Critic (质量循环)
2. insight-alignment：洞察顾问 → 总编辑 → 私域挖掘员(可选) → 风格执笔人

用法:
    python main.py "选题"  # 默认 hub-spoke 流程
    python main.py --flow insight-alignment "如何提升个人品牌"  # 使用旧流程
    python main.py -p openai "AI产品经理职业发展"

输出目录: output/YYYY-MM-DD_HHMMSS_选题拼音_模型名_短id/
  - thought_trace.md  流程轨迹
  - article.md        最终文章
"""
import os
import sys

from src.cli import parse_args, CLIError
from src.config import load_config, ConfigError
from src.utils import setup_logger, get_logger
from src.agent.insight_alignment import run_insight_alignment_flow
from src.agent.hub_spoke.flow import run_hub_spoke_flow
from src.agent.backends import get_model_name
from src.output import create_output_dir, OutputTracer


def print_progress(message: str) -> None:
    """把进度信息打印到控制台，供用户实时看到当前阶段。"""
    print(message)


def main() -> int:
    """主入口：解析参数 → 加载配置 → 创建输出目录 → 按流程运行 Agent → 输出结果。

    Returns:
        0 成功，1 失败。
    """
    # ---------- 1. 解析命令行参数 ----------
    try:
        cli_result = parse_args(sys.argv)
    except SystemExit as e:
        if e.code == 0:
            return 0
        return 1
    except CLIError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # ---------- 2. 加载配置（.env + 环境变量）；命令行可覆盖 provider/model ----------
    if cli_result.provider:
        os.environ["LLM_PROVIDER"] = cli_result.provider
    try:
        config = load_config()
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1
    if cli_result.model:
        p = (cli_result.provider or config.llm_provider or "").strip().lower()
        if p == "openai":
            os.environ["OPENAI_MODEL"] = cli_result.model
        else:
            os.environ["ANTHROPIC_MODEL"] = cli_result.model

    setup_logger(config.log_level)
    log = get_logger(__name__)
    log.info(f"选题: {cli_result.topic}")

    # ---------- 3. 创建本次运行的输出目录 ----------
    # 目录名含选题拼音、模型名（如 MiniMax-M2-1）、短随机 id，便于区分不同 run
    output_base = os.getenv("OUTPUT_DIR", "output")
    model_name = get_model_name(config.llm_provider)
    try:
        run_dir = create_output_dir(cli_result.topic, base_dir=output_base, model_name=model_name)
    except OSError as e:
        print(f"无法创建输出目录: {e}", file=sys.stderr)
        return 1

    # ---------- 4. 初始化轨迹记录器 ----------
    # 负责往 run_dir 下写 thought_trace.md（流程日志）和 article.md（最终文章）
    tracer = OutputTracer(run_dir)
    tracer.start()

    print_progress(f"[选题] {cli_result.topic}")
    print_progress(f"[流程] {cli_result.flow}")
    print_progress(f"[输出] {run_dir}")

    # ---------- 5. 根据 flow 参数执行相应的流程 ----------
    if cli_result.flow == "hub-spoke":
        # Hub-Spoke 流程（默认）：Planner → Miner/Web → Orchestrator → Writer → Critic
        # 详见 doc/hub_spoke_实施计划_TDD.md
        result = run_hub_spoke_flow(
            topic=cli_result.topic,
            user_context="",  # 暂不支持从命令行传入 user_context
            config=config,
            on_progress=print_progress,
            tracer=tracer,
        )
    else:
        # 洞察对齐流程：洞察顾问 → 总编辑 → 私域挖掘员(可选) → 风格执笔人
        # 流程逻辑见 src/agent/insight_alignment.py，详见 doc/refer.md
        result = run_insight_alignment_flow(
            topic=cli_result.topic,
            config=config,
            on_progress=print_progress,
            tracer=tracer,
        )

    # ---------- 6. 根据执行结果输出并返回退出码 ----------
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
