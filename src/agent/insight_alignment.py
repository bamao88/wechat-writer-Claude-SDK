"""Insight-alignment flow: 洞察顾问 → 总编辑 → 私域挖掘员(可选) → 风格执笔人. Prompts from prompts/insight-alignment/."""
import re
import xml.etree.ElementTree as ET
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
    """支持两轮制的总编辑决策解析（XML + 文本降级）"""
    round: int  # 1 或 2
    decision: str  # "派单私域挖掘员" | "派单风格执笔人" | "直接合成" | "继续挖掘"
    queries: list[str]  # 查询列表（仅第一轮或继续挖掘时）

    @property
    def ready_for_writing(self) -> bool:
        """是否已准备好交给风格执笔人"""
        return self.round == 2 and self.decision == "派单风格执笔人"


@dataclass
class Stage2Package:
    """提取的阶段二大纲和素材包（XML + 文本降级）"""
    outline: str  # <stage2_outline> 或 【阶段二：执笔用大纲】内容
    materials: str  # <materials_package> 或 【素材包】内容
    success: bool
    error: Optional[str] = None


def _tool_to_def(tool: NotebookLMTool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


def _parse_orchestrator_xml(output: str) -> OrchestratorDecision:
    """
    从 XML 标签解析总编辑决策（orchestrator.txt 的 XML 输出格式）

    预期格式：
    <orchestrator_decision>
      <round>1</round>
      <decision>派单私域挖掘员</decision>
      <queries>
        <query id="1">查询内容</query>
        <query id="2">查询内容</query>
      </queries>
    </orchestrator_decision>
    """
    try:
        # 提取 <orchestrator_decision> 块
        match = re.search(
            r'<orchestrator_decision>(.*?)</orchestrator_decision>',
            output,
            re.DOTALL
        )
        if not match:
            raise ValueError("未找到 <orchestrator_decision> 标签")

        xml_content = f"<root>{match.group(1)}</root>"
        root = ET.fromstring(xml_content)

        # 解析字段
        round_elem = root.find('round')
        decision_elem = root.find('decision')
        queries_elem = root.find('queries')

        round_num = int(round_elem.text) if round_elem is not None else 1
        decision = decision_elem.text.strip() if decision_elem is not None else ""

        # 解析查询列表
        queries = []
        if queries_elem is not None:
            for query_elem in queries_elem.findall('query'):
                if query_elem.text:
                    queries.append(query_elem.text.strip())

        return OrchestratorDecision(
            round=round_num,
            decision=decision,
            queries=queries
        )

    except (ValueError, ET.ParseError) as e:
        logger.warning(f"XML 解析失败: {e}，使用降级解析器")
        raise  # 抛出异常，触发降级


def _parse_orchestrator_fallback(output: str) -> OrchestratorDecision:
    """降级解析器：处理非 XML 格式的输出（兼容旧提示词格式）"""
    text = (output or "").strip()

    # 检测阶段二：派单风格执笔人
    if "派单: 风格执笔人" in text or "派单：风格执笔人" in text:
        return OrchestratorDecision(
            round=2,
            decision="派单风格执笔人",
            queries=[]
        )

    # 检测直接合成
    if "派单: 直接合成" in text or "派单：直接合成" in text:
        return OrchestratorDecision(
            round=1,
            decision="直接合成",
            queries=[]
        )

    # 提取查询列表（阶段一或继续挖掘）
    queries = []
    for i in range(1, 4):
        m = re.search(rf"查询{i}\s*[：:]\s*(.+?)(?=\n查询|\n派单|\n|$)", text, re.DOTALL)
        if m:
            q = m.group(1).strip().split("\n")[0].strip()
            if q:
                queries.append(q)

    # 判断是第一轮还是继续挖掘
    is_continuation = any(marker in text for marker in ["素材评估", "当前缺口", "继续挖掘"])

    return OrchestratorDecision(
        round=1,
        decision="继续挖掘" if is_continuation else "派单私域挖掘员",
        queries=queries
    )


def _parse_orchestrator(output: str) -> OrchestratorDecision:
    """
    解析总编辑决策，支持两轮制
    优先尝试 XML 格式，失败则降级到文本解析
    """
    try:
        return _parse_orchestrator_xml(output)
    except (ValueError, ET.ParseError):
        return _parse_orchestrator_fallback(output)


def _extract_stage2_package_xml(output: str) -> Stage2Package:
    """
    从 XML 标签提取阶段二大纲和素材包

    预期格式：
    <stage2_outline>...</stage2_outline>
    <materials_package>...</materials_package>
    """
    try:
        # 提取 <stage2_outline>
        outline_match = re.search(
            r'<stage2_outline>(.*?)</stage2_outline>',
            output,
            re.DOTALL
        )

        # 提取 <materials_package>
        materials_match = re.search(
            r'<materials_package>(.*?)</materials_package>',
            output,
            re.DOTALL
        )

        if not outline_match:
            raise ValueError("未找到 <stage2_outline> 标签")

        outline = outline_match.group(1).strip()
        materials = materials_match.group(1).strip() if materials_match else ""

        return Stage2Package(
            outline=outline,
            materials=materials,
            success=True
        )

    except (ValueError, Exception) as e:
        logger.warning(f"XML 提取失败: {e}，使用降级提取器")
        raise  # 触发降级


def _extract_stage2_package_fallback(output: str) -> Stage2Package:
    """
    降级提取器：从文本标记提取【阶段二：执笔用大纲】和【素材包】

    预期格式（orchestrator.txt:207-290）：
    [决策]
    派单: 风格执笔人

    ---

    【阶段二：执笔用大纲】
    核心判断：...
    Act 1: ...
    ...

    ---

    【素材包】
    SN-xxx-001: ...
    ...

    ---

    ✅ 总编辑工作结束，进入写作阶段。
    """
    text = (output or "").strip()

    # 提取【阶段二：执笔用大纲】
    outline_match = re.search(
        r"【阶段二：执笔用大纲】\s*\n(.*?)(?=\n---\s*\n\s*【素材包】|\n【素材包】|\Z)",
        text,
        re.DOTALL
    )

    # 提取【素材包】
    materials_match = re.search(
        r"【素材包】\s*\n(.*?)(?=\n---\s*\n\s*✅|✅ 总编辑工作结束|\Z)",
        text,
        re.DOTALL
    )

    if not outline_match:
        return Stage2Package(
            outline="",
            materials="",
            success=False,
            error="未找到【阶段二：执笔用大纲】标记"
        )

    outline = outline_match.group(1).strip()
    materials = materials_match.group(1).strip() if materials_match else ""

    # 验证终止标记
    if "✅ 总编辑工作结束" not in text:
        logger.warning("未找到总编辑结束标记，但继续处理")

    return Stage2Package(
        outline=outline,
        materials=materials,
        success=True
    )


def _extract_stage2_package(output: str) -> Stage2Package:
    """
    从总编辑第二轮输出中提取【阶段二：执笔用大纲】和【素材包】
    优先尝试 XML 格式，失败则降级到文本解析
    """
    try:
        return _extract_stage2_package_xml(output)
    except (ValueError, Exception):
        return _extract_stage2_package_fallback(output)


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

    # Log agent input before execution
    if tracer:
        tracer.append_agent_input(
            agent_name=step_name,
            system_prompt=system_prompt,
            messages=messages,
            routing_info=None,
        )

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
    """
    两轮流程：
    Round 1: 洞察顾问 → 总编辑(阶段一，派单用大纲) → 私域挖掘员
    Round 2: 总编辑(阶段二，收到素材，执笔用大纲) → 风格执笔人
    """
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

    # === Round 1: 洞察顾问 ===
    messages_insight = [{"role": "user", "content": f"选题：{topic}"}]
    insight_output, n1 = _run_step(
        backend, tool, insight_prompt, messages_insight,
        use_tools=True, on_progress=on_progress, tracer=tracer,
        step_name="洞察顾问",
    )
    total_tool_calls += n1

    # === Round 1: 总编辑(阶段一) ===
    messages_orch = [{
        "role": "user",
        "content": f"用户选题：{topic}\n\n洞察顾问回复：\n{insight_output}",
    }]
    orch_round1_output, _ = _run_step(
        backend, tool, orchestrator_prompt, messages_orch,
        use_tools=False, on_progress=on_progress, tracer=tracer,
        step_name="总编辑-第一轮",
    )
    decision_r1 = _parse_orchestrator(orch_round1_output)

    # === 私域挖掘员（根据第一轮决策）===
    final_orch_output = orch_round1_output  # 默认值

    if decision_r1.decision in ["派单私域挖掘员", "继续挖掘"]:
        # 构建挖掘员任务
        if decision_r1.queries:
            lines = "\n".join([f"查询{i+1}: {q}" for i, q in enumerate(decision_r1.queries)])
            miner_content = f"请对以下查询依次调用 search_notebooklm 并汇总结果。\n\n{lines}"
        else:
            # 降级方案：传递完整上下文让挖掘员自己判断
            miner_content = (
                f"选题：{topic}\n\n"
                f"洞察顾问输出：\n{insight_output}\n\n"
                f"总编辑指示：\n{orch_round1_output}\n\n"
                f"请根据以上信息调用 search_notebooklm 进行必要的私域搜索并汇总结果。"
            )

        messages_miner = [{"role": "user", "content": miner_content}]
        miner_output, n3 = _run_step(
            backend, tool, miner_prompt, messages_miner,
            use_tools=True, on_progress=on_progress, tracer=tracer,
            step_name="私域挖掘员",
        )
        total_tool_calls += n3

        # === Round 2: 总编辑(阶段二) ===
        # 累积第一轮对话，添加私域结果
        messages_orch.append({"role": "assistant", "content": orch_round1_output})
        messages_orch.append({
            "role": "user",
            "content": f"私域挖掘员返回的证据：\n\n{miner_output}\n\n请评估这些证据并决策下一步。",
        })

        orch_round2_output, _ = _run_step(
            backend, tool, orchestrator_prompt, messages_orch,
            use_tools=False, on_progress=on_progress, tracer=tracer,
            step_name="总编辑-第二轮",
        )
        decision_r2 = _parse_orchestrator(orch_round2_output)

        if not decision_r2.ready_for_writing:
            logger.warning("总编辑第二轮未输出【阶段二大纲】，可能需要继续挖掘")
            # 此处可实现迭代循环（可选）

        final_orch_output = orch_round2_output
    else:
        # 罕见情况：第一轮就选择直接合成
        if on_progress:
            on_progress("[总编辑] 直接合成，跳过私域挖掘员")
        logger.info("[总编辑] 直接合成，跳过私域挖掘员")

    # === 提取阶段二包 ===
    stage2_pkg = _extract_stage2_package(final_orch_output)

    if not stage2_pkg.success:
        logger.error(f"提取阶段二大纲失败: {stage2_pkg.error}")
        # 降级方案：使用完整总编辑输出
        ghostwriter_input = f"选题：{topic}\n\n总编辑指导：\n{final_orch_output}"
    else:
        # 正常流程：传递精简的阶段二包
        ghostwriter_input = (
            f"选题：{topic}\n\n"
            f"【阶段二：执笔用大纲】\n{stage2_pkg.outline}\n\n"
            f"【素材包】\n{stage2_pkg.materials}"
        )

    # === 风格执笔人 ===
    messages_gw = [{"role": "user", "content": ghostwriter_input}]
    final_output, _ = _run_step(
        backend, tool, ghostwriter_prompt, messages_gw,
        use_tools=False, on_progress=on_progress, tracer=tracer,
        step_name="风格执笔人",
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
