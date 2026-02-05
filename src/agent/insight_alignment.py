"""Insight-alignment flow: 洞察顾问 → 总编辑 → 私域挖掘员(可选) → 风格执笔人. Prompts from prompts/insight-alignment/."""
import re
from typing import Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass

from src.config.settings import Config
from src.agent.backends import get_backend
from src.agent.backends.base import BackendResponse
from src.tools.notebooklm import NotebookLMTool
from src.utils.logger import get_logger
from src.utils.prompt_loader import load_prompt, PromptError

if TYPE_CHECKING:
    from src.output.tracer import OutputTracer

logger = get_logger(__name__)

MAX_ITERATIONS = 15
MAX_TOKENS = 8192
PROMPTS_SUBDIR = "insight-alignment"


@dataclass
class OrchestratorDecision:
    """Parsed orchestrator output."""
    direct_synthesis: bool  # True = 直接合成, False = 派单私域挖掘员
    queries: list[str]  # 查询1/2/3 列表，最多 3 条


def _tool_to_def(tool: NotebookLMTool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


def _parse_orchestrator(output: str) -> OrchestratorDecision:
    """Parse 派单: 直接合成 / 派单: 私域挖掘员 + 查询1/2/3."""
    text = (output or "").strip()
    if "派单: 直接合成" in text or "派单：直接合成" in text:
        return OrchestratorDecision(direct_synthesis=True, queries=[])
    queries: list[str] = []
    for i in range(1, 4):
        m = re.search(rf"查询{i}\s*[：:]\s*(.+?)(?=\n查询|\n派单|\Z)", text, re.DOTALL)
        if m:
            q = m.group(1).strip().split("\n")[0].strip()
            if q:
                queries.append(q)
    return OrchestratorDecision(direct_synthesis=False, queries=queries)


def _run_step(
    backend,
    tool: NotebookLMTool,
    system_prompt: str,
    messages: list,
    use_tools: bool,
    on_progress: Optional[Callable[[str], None]],
    tracer: Optional["OutputTracer"],
    step_name: str,
) -> tuple[str, int]:
    """Run one step until end_turn; return (content_text, tool_call_count)."""
    tools = [_tool_to_def(tool)] if use_tools else []
    tool_call_count = 0
    last_resp: Optional[BackendResponse] = None

    def handle_tool_call(tool_name: str, tool_input: dict) -> str:
        if tool_name == tool.name:
            query = tool_input.get("query", "")
            logger.info(f"[NotebookLM] {step_name} 搜索: {query[:50]}...")
            result = tool.execute(query=query)
            return result.content if result.success else f"搜索失败: {result.error}"
        return f"未知工具: {tool_name}"

    logger.info(f"[{step_name}] 开始")
    for iteration in range(MAX_ITERATIONS):
        if on_progress:
            on_progress(f"[{step_name}] 第{iteration + 1}轮...")
        resp: BackendResponse = backend.create(
            system=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=MAX_TOKENS,
        )
        last_resp = resp
        if tracer and resp.content_text:
            tracer.append_agent_output(resp.content_text, agent_name=step_name)

        if resp.stop_reason == "end_turn":
            logger.info(f"[{step_name}] 完成，工具调用 {tool_call_count} 次")
            return (resp.content_text, tool_call_count)

        if resp.stop_reason == "tool_use" and resp.tool_calls:
            tool_results = []
            assistant_tool_calls = [
                {"id": tc.id, "name": tc.name, "input": tc.input}
                for tc in resp.tool_calls
            ]
            for tc in resp.tool_calls:
                tool_call_count += 1
                if on_progress:
                    on_progress(f"[{step_name}] 工具调用 {tc.name}...")
                if tracer:
                    tracer.append_tool_call(tc.name, tc.input, agent_name=step_name)
                result = handle_tool_call(tc.name, tc.input)
                if tracer:
                    tracer.append_tool_result(result, agent_name=step_name)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result,
                })
            messages.append({
                "role": "assistant",
                "content": resp.content_text,
                "tool_calls": assistant_tool_calls,
            })
            messages.append({"role": "user", "content": tool_results})
        else:
            break
    logger.info(f"[{step_name}] 完成，工具调用 {tool_call_count} 次")
    return (last_resp.content_text if last_resp else "", tool_call_count)


@dataclass
class InsightAlignmentResult:
    """Result of full insight-alignment flow."""
    success: bool
    output: str
    tool_calls: int
    error: Optional[str] = None


def run_insight_alignment_flow(
    topic: str,
    config: Config,
    on_progress: Optional[Callable[[str], None]] = None,
    tracer: Optional["OutputTracer"] = None,
) -> InsightAlignmentResult:
    """Run full flow: 洞察顾问 → 总编辑 → 私域挖掘员(可选) → 风格执笔人. All prompts from prompts/insight-alignment/."""
    backend = get_backend(config.llm_provider)
    tool = NotebookLMTool(config)
    total_tool_calls = 0

    try:
        # Load all prompts from prompts/insight-alignment/
        insight_prompt = load_prompt(f"{PROMPTS_SUBDIR}/insight_specialist.txt")
        orchestrator_prompt = load_prompt(f"{PROMPTS_SUBDIR}/orchestrator.txt")
        miner_prompt = load_prompt(f"{PROMPTS_SUBDIR}/knowledge_miner.txt")
        ghostwriter_prompt = load_prompt(f"{PROMPTS_SUBDIR}/ghostwriter.txt")
    except PromptError as e:
        logger.error(f"Prompt 加载失败: {e}")
        return InsightAlignmentResult(success=False, output="", tool_calls=0, error=str(e))

    if on_progress:
        on_progress("[开始] 洞察对齐流程...")
    logger.info("[洞察对齐] 流程开始")

    # Step 1: 洞察顾问
    messages_insight = [{"role": "user", "content": f"选题：{topic}"}]
    insight_output, n1 = _run_step(
        backend, tool, insight_prompt, messages_insight,
        use_tools=True, on_progress=on_progress, tracer=tracer, step_name="洞察顾问",
    )
    total_tool_calls += n1

    # Step 2: 总编辑
    messages_orch = [{
        "role": "user",
        "content": f"用户选题：{topic}\n\n洞察顾问回复：\n{insight_output}",
    }]
    orchestrator_output, _ = _run_step(
        backend, tool, orchestrator_prompt, messages_orch,
        use_tools=False, on_progress=on_progress, tracer=tracer, step_name="总编辑",
    )
    decision = _parse_orchestrator(orchestrator_output)

    # Step 3: 私域挖掘员（可选）
    miner_output = ""
    if not decision.direct_synthesis and decision.queries:
        lines = "\n".join([f"查询{i+1}: {q}" for i, q in enumerate(decision.queries)])
        messages_miner = [{
            "role": "user",
            "content": f"请对以下查询依次调用 search_notebooklm 并汇总结果。\n\n{lines}",
        }]
        miner_output, n3 = _run_step(
            backend, tool, miner_prompt, messages_miner,
            use_tools=True, on_progress=on_progress, tracer=tracer, step_name="私域挖掘员",
        )
        total_tool_calls += n3
    else:
        if on_progress:
            on_progress("[总编辑] 直接合成，跳过私域挖掘员")
        logger.info("[总编辑] 直接合成，跳过私域挖掘员")

    # Step 4: 风格执笔人
    miner_block = f"\n\n私域挖掘结果：\n{miner_output}" if miner_output else "\n\n私域挖掘结果：无（总编辑选择直接合成）"
    messages_gw = [{
        "role": "user",
        "content": f"选题：{topic}\n\n洞察顾问输出：\n{insight_output}{miner_block}\n\n请输出最终文章（含正文与标题）。",
    }]
    final_output, _ = _run_step(
        backend, tool, ghostwriter_prompt, messages_gw,
        use_tools=False, on_progress=on_progress, tracer=tracer, step_name="风格执笔人",
    )

    if tracer:
        tracer.save_article(final_output)
        tracer.close()
    if on_progress:
        on_progress("[完成]")
    logger.info("[洞察对齐] 流程完成")

    return InsightAlignmentResult(
        success=True,
        output=final_output,
        tool_calls=total_tool_calls,
    )
