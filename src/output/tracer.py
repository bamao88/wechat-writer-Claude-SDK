"""Thought trace and article persistence for Phase 3."""
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

TRACE_ENTRY = "## [{seq:03d}] [{ts}] {kind}\n\n"
TRACE_ENTRY_WITH_AGENT = "## [{seq:03d}] [{ts}] [{agent}] {kind}\n\n"
TOOL_RESULT_TRUNCATE = 500
WRITE_RETRIES = 3
WRITE_RETRY_DELAY = 0.2


def _serialize_message_content(content: Any) -> str:
    """将单条 message 的 content 转为可读字符串（支持 str 或 tool_result 列表）."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "tool_result":
                    c = item.get("content", "")
                    parts.append(f"[tool_result] {c}" if isinstance(c, str) else str(c))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)
    return str(content)


def _messages_to_string(messages: list) -> str:
    """将 messages 列表序列化为可读的「角色: 内容」文本."""
    lines = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        text = _serialize_message_content(content)
        lines.append(f"--- [{i+1}] {role} ---\n{text}")
    return "\n\n".join(lines)


class OutputTracer:
    """Appends thought trace and saves article to output directory."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.trace_path = self.output_dir / "thought_trace.md"
        self.article_path = self.output_dir / "article.md"
        self.inputs_path = self.output_dir / "agent_inputs.json"  # 新增：结构化输入记录
        self._seq = 0
        self._buffer: list[str] = []
        self._last_agent_input_seq: Optional[int] = None  # 用于在 Output 处提示「输入见上方」
        self._agent_calls: list[dict] = []  # 记录所有Agent调用，用于生成摘要
        self._start_time = time.time()
        self._agent_inputs: list[dict] = []  # 新增：存储所有Agent输入的结构化数据

    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _append_to_trace(self, content: str) -> None:
        for attempt in range(WRITE_RETRIES):
            try:
                with open(self.trace_path, "a", encoding="utf-8") as f:
                    f.write(content)
                return
            except OSError:
                if attempt < WRITE_RETRIES - 1:
                    time.sleep(WRITE_RETRY_DELAY)
        self._buffer.append(content)

    def _flush_buffer(self) -> None:
        if not self._buffer:
            return
        try:
            with open(self.trace_path, "a", encoding="utf-8") as f:
                f.write("".join(self._buffer))
        except OSError:
            pass
        self._buffer.clear()

    def start(self) -> None:
        """Initialize thought_trace.md with a header."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        header = "# Thought Trace\n\n"
        header += "## 📊 执行摘要\n\n"
        header += "_（此部分将在执行结束后更新）_\n\n"
        header += "---\n\n"
        header += "## 🔄 完整执行日志\n\n"
        self._append_to_trace(header)

    def append_agent_input(
        self,
        agent_name: str,
        system_prompt: str,
        messages: list,
        routing_info: Optional[dict] = None,
    ) -> None:
        """记录即将发给该 Agent 的完整输入（system + messages），默认折叠以便与 Output 紧邻可读。

        Args:
            agent_name: Agent名称
            system_prompt: System提示词
            messages: 消息列表
            routing_info: 路由信息，包含 {
                'triggered_by': str,  # 触发者（如 'Orchestrator', 'User'）
                'reason': str,        # 调用原因
                'expected_output': str  # 期望输出
            }
        """
        self._seq += 1
        input_seq = self._seq
        kind = "Agent Input"

        # 记录Agent调用用于摘要
        call_record = {
            'seq': self._seq,
            'agent': agent_name.strip(),
            'start_time': time.time(),
            'triggered_by': routing_info.get('triggered_by', '未知') if routing_info else '未知',
        }
        self._agent_calls.append(call_record)

        block = TRACE_ENTRY_WITH_AGENT.format(
            seq=self._seq, ts=self._timestamp(), agent=agent_name.strip(), kind=kind
        )

        # 添加路由信息（如果提供）
        if routing_info:
            block += "**🔀 路由信息**\n\n"
            block += f"- **触发者**: {routing_info.get('triggered_by', '未知')}\n"
            block += f"- **调用原因**: {routing_info.get('reason', '未指定')}\n"
            if routing_info.get('expected_output'):
                block += f"- **期望输出**: {routing_info['expected_output']}\n"
            block += "\n"

        sys_text = (system_prompt or "").strip()
        msg_text = _messages_to_string(messages)
        # 默认折叠，整块仅几行，方便在 Output 处「往上看一眼」就是输入
        block += "**System** <details><summary>展开查看（共 {} 字）</summary>\n\n{}\n\n</details>\n\n".format(
            len(sys_text), sys_text
        )
        block += "**Messages** <details><summary>展开查看（共 {} 字）</summary>\n\n{}\n\n</details>\n\n".format(
            len(msg_text), msg_text
        )
        self._last_agent_input_seq = input_seq
        self._append_to_trace(block)

        # 新增：同时保存结构化的输入数据到 JSON
        input_record = {
            'seq': self._seq,
            'timestamp': self._timestamp(),
            'agent_name': agent_name.strip(),
            'system_prompt': system_prompt,
            'messages': messages,  # 保留原始 messages 列表
            'routing_info': routing_info or {},
        }
        self._agent_inputs.append(input_record)

    def append_agent_output(self, text: str, agent_name: Optional[str] = None) -> None:
        """Append one agent text output block. Optional agent_name shows in header as [Agent名]."""
        self._seq += 1
        kind = "Agent Output"

        # 更新Agent调用记录（添加结束时间和耗时）
        if agent_name and self._agent_calls:
            for call in reversed(self._agent_calls):
                if call['agent'] == agent_name.strip() and 'end_time' not in call:
                    call['end_time'] = time.time()
                    call['duration'] = call['end_time'] - call['start_time']
                    break

        if agent_name and agent_name.strip():
            block = TRACE_ENTRY_WITH_AGENT.format(seq=self._seq, ts=self._timestamp(), agent=agent_name.strip(), kind=kind)
        else:
            block = TRACE_ENTRY.format(seq=self._seq, ts=self._timestamp(), kind=kind)
        # 提示本步输入在上方，便于在 Output 处一眼看到「输入在哪」
        if agent_name and self._last_agent_input_seq is not None:
            block += "（本步输入见上方 **## [{}] Agent Input**，可展开查看 System / Messages）\n\n".format(
                self._last_agent_input_seq
            )
        block += "> " + text.replace("\n", "\n> ") + "\n\n"
        self._append_to_trace(block)

    def append_tool_call(self, name: str, params: dict, agent_name: Optional[str] = None) -> None:
        """Append one tool call (name + key params only). Optional agent_name shows in header as [Agent名]."""
        self._seq += 1
        kind = "Tool Call"
        if agent_name and agent_name.strip():
            block = TRACE_ENTRY_WITH_AGENT.format(seq=self._seq, ts=self._timestamp(), agent=agent_name.strip(), kind=kind)
        else:
            block = TRACE_ENTRY.format(seq=self._seq, ts=self._timestamp(), kind=kind)
        block += "```\n"
        block += f"tool: {name}\n"
        for k, v in params.items():
            if k == "query" or k == "question":
                block += f"{k}: {v[:200]}...\n" if len(str(v)) > 200 else f"{k}: {v}\n"
            else:
                block += f"{k}: {v}\n"
        block += "```\n\n"
        self._append_to_trace(block)

    def append_tool_result(self, content: str, agent_name: Optional[str] = None) -> None:
        """Append one tool result (truncate long content, rest in details). Optional agent_name shows in header as [Agent名]."""
        self._seq += 1
        kind = "Tool Result"
        if agent_name and agent_name.strip():
            block = TRACE_ENTRY_WITH_AGENT.format(seq=self._seq, ts=self._timestamp(), agent=agent_name.strip(), kind=kind)
        else:
            block = TRACE_ENTRY.format(seq=self._seq, ts=self._timestamp(), kind=kind)
        if len(content) <= TOOL_RESULT_TRUNCATE:
            block += "<details><summary>内容</summary>\n\n" + content + "\n\n</details>\n\n"
        else:
            visible = content[:TOOL_RESULT_TRUNCATE] + "..."
            rest = content[TOOL_RESULT_TRUNCATE:]
            block += "<details><summary>内容（前 500 字）</summary>\n\n" + visible + "\n\n</details>\n\n"
            block += "<details><summary>完整内容</summary>\n\n" + rest + "\n\n</details>\n\n"
        self._append_to_trace(block)

    def save_article(self, content: str) -> Optional[str]:
        """Save final article to article.md. Returns error message on failure (soft fail)."""
        for attempt in range(WRITE_RETRIES):
            try:
                with open(self.article_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return None
            except OSError as e:
                if attempt < WRITE_RETRIES - 1:
                    time.sleep(WRITE_RETRY_DELAY)
                else:
                    return str(e)
        return "写入 article.md 失败"

    def _generate_summary(self) -> str:
        """生成执行摘要文本"""
        total_duration = time.time() - self._start_time

        summary = "## 📊 执行摘要\n\n"
        summary += f"**总耗时**: {total_duration:.2f}秒\n\n"
        summary += f"**总步骤数**: {self._seq}\n\n"

        # Agent调用链
        summary += "### 🔄 Agent调用链\n\n"
        summary += "```mermaid\n"
        summary += "graph TD\n"
        summary += "    Start[用户请求] --> A1\n"

        for i, call in enumerate(self._agent_calls):
            agent_id = f"A{i+1}"
            agent_name = call['agent']
            triggered_by = call.get('triggered_by', '未知')
            duration = call.get('duration', 0)

            summary += f"    {agent_id}[{agent_name}<br/>耗时: {duration:.1f}s]\n"

            # 添加到下一个Agent的连接
            if i < len(self._agent_calls) - 1:
                summary += f"    {agent_id} --> A{i+2}\n"

        if self._agent_calls:
            summary += f"    A{len(self._agent_calls)} --> End[完成]\n"

        summary += "```\n\n"

        # Agent详细信息表格
        summary += "### 📋 Agent执行详情\n\n"
        summary += "| 序号 | Agent名称 | 触发者 | 耗时(秒) | 开始时间 |\n"
        summary += "|------|----------|--------|----------|----------|\n"

        for i, call in enumerate(self._agent_calls):
            agent_name = call['agent']
            triggered_by = call.get('triggered_by', '未知')
            duration = call.get('duration', 0)
            start_time = datetime.fromtimestamp(call['start_time']).strftime("%H:%M:%S")

            summary += f"| {i+1} | {agent_name} | {triggered_by} | {duration:.2f} | {start_time} |\n"

        summary += "\n---\n\n"
        summary += "## 🔄 完整执行日志\n\n"

        return summary

    def close(self) -> None:
        """Flush any buffered trace content and update summary."""
        self._flush_buffer()

        # 生成并插入摘要到文件开头
        if self._agent_calls and self.trace_path.exists():
            try:
                # 读取现有内容
                with open(self.trace_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 生成摘要
                summary = self._generate_summary()

                # 替换占位符
                if "_（此部分将在执行结束后更新）_" in content:
                    content = content.replace(
                        "## 📊 执行摘要\n\n_（此部分将在执行结束后更新）_\n\n---\n\n## 🔄 完整执行日志",
                        summary.rstrip()
                    )

                    # 写回文件
                    with open(self.trace_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            except Exception:
                pass  # 如果更新失败也不影响主流程

        # 新增：保存结构化的 Agent 输入数据到 JSON 文件
        if self._agent_inputs:
            try:
                with open(self.inputs_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'metadata': {
                            'total_agents': len(self._agent_inputs),
                            'total_duration': time.time() - self._start_time,
                            'generated_at': datetime.now().isoformat(),
                        },
                        'inputs': self._agent_inputs
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"保存 agent_inputs.json 失败: {e}")
