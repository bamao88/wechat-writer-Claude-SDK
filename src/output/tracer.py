"""Thought trace and article persistence for Phase 3."""
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

TRACE_ENTRY = "## [{seq:03d}] [{ts}] {kind}\n\n"
TRACE_ENTRY_WITH_AGENT = "## [{seq:03d}] [{ts}] [{agent}] {kind}\n\n"
TOOL_RESULT_TRUNCATE = 500
WRITE_RETRIES = 3
WRITE_RETRY_DELAY = 0.2


class OutputTracer:
    """Appends thought trace and saves article to output directory."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.trace_path = self.output_dir / "thought_trace.md"
        self.article_path = self.output_dir / "article.md"
        self._seq = 0
        self._buffer: list[str] = []

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
        self._append_to_trace(header)

    def append_agent_output(self, text: str, agent_name: Optional[str] = None) -> None:
        """Append one agent text output block. Optional agent_name shows in header as [Agent名]."""
        self._seq += 1
        kind = "Agent Output"
        if agent_name and agent_name.strip():
            block = TRACE_ENTRY_WITH_AGENT.format(seq=self._seq, ts=self._timestamp(), agent=agent_name.strip(), kind=kind)
        else:
            block = TRACE_ENTRY.format(seq=self._seq, ts=self._timestamp(), kind=kind)
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

    def close(self) -> None:
        """Flush any buffered trace content."""
        self._flush_buffer()
