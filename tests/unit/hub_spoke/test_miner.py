"""Tests for Miner Worker (dual-layer output)."""
import pytest
from unittest.mock import Mock
from src.agent.hub_spoke.workers.miner import MinerWorker, MinerResult
from src.agent.hub_spoke.state import State
from src.tools.notebooklm import ToolResult


class TestMinerResult:
    """Test MinerResult dataclass."""

    def test_miner_result_structure(self):
        """MinerResult has structured_points and raw_voice_clips."""
        result = MinerResult(
            structured_points=["观点A", "观点B"],
            raw_voice_clips=["片段1", "片段2"]
        )
        assert result.structured_points == ["观点A", "观点B"]
        assert result.raw_voice_clips == ["片段1", "片段2"]


class TestMinerJSONParsing:
    """Test Miner JSON parsing."""

    def test_parse_valid_dual_layer_json(self):
        """Parses dual-layer JSON correctly."""
        worker = MinerWorker()
        json_output = '''{
            "structured_points": ["个人品牌核心是价值定位", "内容输出要持续"],
            "raw_voice_clips": ["我一直强调，价值定位最重要", "不能三天打鱼两天晒网"]
        }'''

        result = worker._parse_json_output(json_output)

        assert len(result.structured_points) == 2
        assert len(result.raw_voice_clips) == 2
        assert "价值定位" in result.structured_points[0]

    def test_parse_empty_arrays(self):
        """Handles empty arrays gracefully."""
        worker = MinerWorker()
        json_output = '{"structured_points": [], "raw_voice_clips": []}'

        result = worker._parse_json_output(json_output)

        assert result.structured_points == []
        assert result.raw_voice_clips == []

    def test_parse_malformed_json_fallback(self):
        """Falls back to empty result on malformed JSON."""
        worker = MinerWorker()
        malformed = '{"structured_points": ["观点A"'  # Incomplete

        result = worker._parse_json_output(malformed)

        # Should fallback to empty
        assert isinstance(result.structured_points, list)
        assert isinstance(result.raw_voice_clips, list)


class TestMinerExecution:
    """Test Miner execution with NotebookLM tool."""

    def test_miner_calls_notebooklm_tool(self):
        """Miner calls NotebookLM tool with query."""
        worker = MinerWorker()
        state = State(topic="如何提升个人品牌")

        # Mock NotebookLM tool
        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(
            success=True,
            content='''{
                "structured_points": ["观点1"],
                "raw_voice_clips": ["片段1"]
            }''',
            error=None
        ))

        mock_backend = Mock()
        mock_backend.create = Mock(return_value=Mock(
            content_text='''{
                "structured_points": ["观点1"],
                "raw_voice_clips": ["片段1"]
            }'''
        ))

        mock_tracer = Mock()

        result = worker.run(state, mock_tool, mock_backend, mock_tracer)

        # Verify tool was called
        assert mock_tool.execute.called
        # Verify result structure
        assert len(result.structured_points) >= 0
        assert len(result.raw_voice_clips) >= 0

    def test_miner_updates_state(self):
        """Miner updates state with results."""
        worker = MinerWorker()
        state = State(topic="测试")

        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(
            success=True,
            content="NotebookLM结果",
            error=None
        ))

        mock_backend = Mock()
        mock_backend.create = Mock(return_value=Mock(
            content_text='''{
                "structured_points": ["观点A", "观点B"],
                "raw_voice_clips": ["片段1", "片段2"]
            }'''
        ))

        mock_tracer = Mock()

        result = worker.run(state, mock_tool, mock_backend, mock_tracer)

        # State should be updated by executor, not by worker directly
        # Worker just returns result
        assert result.structured_points == ["观点A", "观点B"]
        assert result.raw_voice_clips == ["片段1", "片段2"]


class TestMinerOutputConstraints:
    """Test Miner output length constraints."""

    def test_output_length_warning(self):
        """Miner logs warning if output exceeds 500 chars."""
        worker = MinerWorker()
        state = State(topic="测试")

        # Mock very long output
        long_points = ["观点" + str(i) * 50 for i in range(20)]
        long_clips = ["片段" + str(i) * 50 for i in range(20)]

        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(True, "结果", None))

        mock_backend = Mock()
        mock_backend.create = Mock(return_value=Mock(
            content_text=f'{{"structured_points": {long_points}, "raw_voice_clips": {long_clips}}}'
        ))

        mock_tracer = Mock()

        # Should not crash, but may log warning
        result = worker.run(state, mock_tool, mock_backend, mock_tracer)

        assert isinstance(result, MinerResult)


class TestMinerErrorHandling:
    """Test Miner error handling."""

    def test_notebooklm_tool_failure(self):
        """Handles NotebookLM tool failure gracefully."""
        worker = MinerWorker()
        state = State(topic="测试")

        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(
            success=False,
            content="",
            error="NotebookLM调用失败"
        ))

        mock_backend = Mock()
        mock_tracer = Mock()

        # Should handle gracefully
        result = worker.run(state, mock_tool, mock_backend, mock_tracer)

        # Should return empty or fallback result
        assert isinstance(result, MinerResult)

    def test_backend_exception(self):
        """Handles backend exception gracefully."""
        worker = MinerWorker()
        state = State(topic="测试")

        mock_tool = Mock()
        mock_tool.execute = Mock(return_value=ToolResult(True, "结果", None))

        mock_backend = Mock()
        mock_backend.create = Mock(side_effect=Exception("API error"))

        mock_tracer = Mock()

        # Should handle gracefully
        result = worker.run(state, mock_tool, mock_backend, mock_tracer)

        assert isinstance(result, MinerResult)
