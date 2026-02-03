"""NotebookLM tool wrapper using PleasePrompto/notebooklm-skill (Skill)."""
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from src.config.settings import Config


class ToolError(Exception):
    """Raised when tool execution fails unrecoverably."""
    pass


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    content: str
    error: Optional[str]


_ANSWER_SEP = "=" * 60


def _skill_dir(config: Config) -> Path:
    """Resolve NotebookLM Skill root directory."""
    if config.notebooklm_skill_dir:
        return Path(config.notebooklm_skill_dir).expanduser().resolve()
    return (Path.home() / ".claude" / "skills" / "notebooklm").resolve()


def _skill_python(skill_dir: Path) -> str:
    """Python executable for running Skill scripts: prefer Skill's .venv, else sys.executable."""
    # Prefer Skill's isolated venv (avoids polluting project venv with patchright etc.)
    venv_bin = skill_dir / ".venv" / "bin" / "python"
    if venv_bin.is_file():
        return str(venv_bin)
    venv_scripts = skill_dir / ".venv" / "Scripts" / "python.exe"
    if venv_scripts.is_file():
        return str(venv_scripts)
    return sys.executable


def _parse_answer_from_stdout(stdout: str) -> str:
    """Extract answer from ask_question.py stdout (between separator blocks)."""
    if not stdout or not stdout.strip():
        return ""
    parts = stdout.split(_ANSWER_SEP)
    if len(parts) >= 3:
        return parts[2].strip()
    return stdout.strip()


def search_notebook(query: str, config: Config) -> ToolResult:
    """Search NotebookLM using notebooklm-skill's ask_question.py.

    Uses Skill's .venv/bin/python when present (isolated deps); else sys.executable.
    Requires Skill at ~/.claude/skills/notebooklm (or NOTEBOOKLM_SKILL_DIR),
    its .venv set up (python -m venv .venv && pip install -r requirements.txt),
    and one-time auth (e.g. .venv/bin/python scripts/auth_manager.py setup).

    Args:
        query: Search query string.
        config: Application configuration (notebook_url, optional notebooklm_skill_dir).

    Returns:
        ToolResult with search results or error message.
    """
    skill_dir = _skill_dir(config)
    script_path = skill_dir / "scripts" / "ask_question.py"

    if not script_path.is_file():
        return ToolResult(
            success=False,
            content="",
            error=(
                "未找到 NotebookLM Skill 脚本。请克隆 Skill 并设置路径：\n"
                "  git clone https://github.com/PleasePrompto/notebooklm-skill.git ~/.claude/skills/notebooklm\n"
                "  或在 .env 中设置 NOTEBOOKLM_SKILL_DIR 指向 Skill 根目录。\n"
                f"当前查找路径: {script_path}"
            ),
        )

    python_exe = _skill_python(skill_dir)
    last_error = None
    for attempt in range(config.retry_count):
        try:
            cmd = [
                python_exe,
                str(script_path),
                "--question",
                query,
                "--notebook-url",
                config.notebook_url,
            ]
            result = subprocess.run(
                cmd,
                cwd=str(skill_dir),
                capture_output=True,
                text=True,
                timeout=config.timeout_sec,
            )

            if result.returncode == 0:
                answer = _parse_answer_from_stdout(result.stdout)
                return ToolResult(
                    success=True,
                    content=answer or result.stdout.strip(),
                    error=None,
                )

            last_error = (
                result.stderr.strip() or result.stdout.strip()
                or f"脚本退出码: {result.returncode}"
            )

        except subprocess.TimeoutExpired:
            last_error = f"工具调用超时（{config.timeout_sec}秒）"
        except Exception as e:
            last_error = f"工具调用异常: {str(e)}"

        if attempt < config.retry_count - 1 and config.retry_delay_sec > 0:
            time.sleep(config.retry_delay_sec)

    return ToolResult(
        success=False,
        content="",
        error=f"NotebookLM 搜索失败，已重试 {config.retry_count} 次。最后一次错误: {last_error}",
    )


class NotebookLMTool:
    """NotebookLM search tool for Claude SDK integration.

    Uses PleasePrompto/notebooklm-skill (ask_question.py) via subprocess.
    """

    def __init__(self, config: Config):
        self.config = config
        self.name = "search_notebooklm"
        self.description = "搜索 NotebookLM 笔记本中的资料。用于查找与写作主题相关的参考内容、案例和素材。（基于 notebooklm-skill）"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索问题，用于在 NotebookLM 中查找相关资料",
                }
            },
            "required": ["query"],
        }

    def execute(self, query: str) -> ToolResult:
        return search_notebook(query, self.config)

    def to_claude_tool(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
