"""Shared test fixtures for hub-spoke architecture tests."""
import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from typing import Any


@pytest.fixture
def mock_backend():
    """Mock LLM backend for testing agents."""
    backend = Mock()
    backend.create = Mock(return_value=Mock(
        content=[Mock(text="Mock response")],
        stop_reason="end_turn",
    ))
    return backend


@pytest.fixture
def mock_tool():
    """Mock tool (NotebookLM or Web) for testing."""
    tool = Mock()
    tool.name = "mock_tool"
    tool.description = "Mock tool for testing"
    tool.input_schema = {"type": "object", "properties": {}}
    tool.execute = Mock(return_value=Mock(
        content="Mock tool result",
        is_error=False,
    ))
    return tool


@pytest.fixture
def mock_tracer(tmp_path):
    """Mock OutputTracer for testing."""
    tracer = Mock()
    tracer.output_dir = tmp_path / "output"
    tracer.trace_path = tracer.output_dir / "thought_trace.md"
    tracer.article_path = tracer.output_dir / "article.md"
    tracer.start = Mock()
    tracer.append_agent_input = Mock()
    tracer.append_agent_output = Mock()
    tracer.append_tool_call = Mock()
    tracer.append_tool_result = Mock()
    tracer.append_critic_result = Mock()
    tracer.save_article = Mock(return_value=None)
    tracer.close = Mock()
    return tracer


@pytest.fixture
def sample_state():
    """Sample State object for testing."""
    from dataclasses import dataclass, field

    @dataclass
    class State:
        topic: str
        user_context: str = ""
        use_private: bool = False
        use_web: bool = False
        planner_reason: str = ""
        structured_points: list = field(default_factory=list)
        raw_voice_clips: list = field(default_factory=list)
        web_research: str = ""
        outline: str = ""
        draft: str = ""
        critic_score: int = 0
        critic_reason: str = ""
        critic_feedback: str = ""
        iteration_count: int = 0
        next_step: str = "planner"
        status: str = "PENDING"

    return State(topic="测试选题：如何提升个人品牌")


@pytest.fixture
def sample_planner_output():
    """Sample Planner JSON output."""
    return {
        "use_private": True,
        "use_web": False,
        "reason": "用户未提供足够上下文，需要调研私域资料"
    }


@pytest.fixture
def sample_miner_output():
    """Sample Miner dual-layer JSON output."""
    return {
        "structured_points": [
            "个人品牌的核心是价值定位",
            "需要持续输出专业内容",
        ],
        "raw_voice_clips": [
            "我一直强调，做个人品牌最重要的是找到自己的独特价值",
            "内容输出要有规律性，不能三天打鱼两天晒网",
        ]
    }


@pytest.fixture
def sample_critic_result():
    """Sample Critic evaluation result."""
    return {
        "score": 6,
        "passed": False,
        "reason": "字数不足（仅600字，要求≥800字）",
        "feedback": "需要扩充正文，增加案例或数据支撑"
    }
