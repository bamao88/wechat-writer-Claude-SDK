"""Tests for Planner Agent."""
import pytest
import json
from unittest.mock import Mock
from src.agent.hub_spoke.workers.planner import PlannerWorker, PlannerResult
from src.agent.hub_spoke.state import State


class TestPlannerResult:
    """Test PlannerResult dataclass."""

    def test_planner_result_structure(self):
        """PlannerResult has expected fields."""
        result = PlannerResult(
            use_private=True,
            use_web=False,
            reason="需要私域调研"
        )
        assert result.use_private is True
        assert result.use_web is False
        assert result.reason == "需要私域调研"


class TestPlannerJSONParsing:
    """Test Planner JSON output parsing."""

    def test_parse_valid_json_private_only(self):
        """Parses JSON with use_private=True, use_web=False."""
        worker = PlannerWorker()
        json_output = '{"use_private": true, "use_web": false, "reason": "需要私域调研"}'
        result = worker._parse_json_output(json_output)

        assert result.use_private is True
        assert result.use_web is False
        assert "私域" in result.reason

    def test_parse_valid_json_web_only(self):
        """Parses JSON with use_private=False, use_web=True."""
        worker = PlannerWorker()
        json_output = '{"use_private": false, "use_web": true, "reason": "需要全网调研"}'
        result = worker._parse_json_output(json_output)

        assert result.use_private is False
        assert result.use_web is True
        assert "全网" in result.reason

    def test_parse_valid_json_both(self):
        """Parses JSON with both flags True."""
        worker = PlannerWorker()
        json_output = '{"use_private": true, "use_web": true, "reason": "需要全量调研"}'
        result = worker._parse_json_output(json_output)

        assert result.use_private is True
        assert result.use_web is True

    def test_parse_valid_json_neither(self):
        """Parses JSON with both flags False (AI-only writing)."""
        worker = PlannerWorker()
        json_output = '{"use_private": false, "use_web": false, "reason": "用户提供足够上下文"}'
        result = worker._parse_json_output(json_output)

        assert result.use_private is False
        assert result.use_web is False

    def test_parse_malformed_json_fallback(self):
        """Falls back to default when JSON is malformed."""
        worker = PlannerWorker()
        malformed = '{"use_private": true, "use_web": false'  # Missing closing brace
        result = worker._parse_json_output(malformed)

        # Should fallback to safe default (both True)
        assert result.use_private is True
        assert result.use_web is True
        assert "解析失败" in result.reason or "fallback" in result.reason.lower()

    def test_parse_missing_fields(self):
        """Handles JSON with missing required fields."""
        worker = PlannerWorker()
        incomplete = '{"use_private": true}'  # Missing use_web and reason
        result = worker._parse_json_output(incomplete)

        assert hasattr(result, 'use_private')
        assert hasattr(result, 'use_web')
        assert hasattr(result, 'reason')

    def test_parse_non_json_text(self):
        """Handles non-JSON text output."""
        worker = PlannerWorker()
        text = "我建议使用私域调研，因为..."
        result = worker._parse_json_output(text)

        # Should fallback
        assert isinstance(result, PlannerResult)


class TestPlannerDecisionLogic:
    """Test Planner decision-making logic."""

    def test_planner_with_long_user_context(self, mock_backend, mock_tracer):
        """Planner allows both=False when user_context ≥300 chars."""
        worker = PlannerWorker()
        state = State(
            topic="如何提升个人品牌",
            user_context="我是一个资深产品经理" + "，有丰富的经验" * 50  # >300 chars
        )

        # Mock backend to return both=False
        mock_backend.create.return_value = Mock(
            content_text='{"use_private": false, "use_web": false, "reason": "用户上下文充足"}'
        )

        result = worker.run(state, mock_backend, mock_tracer)

        assert result.use_private is False
        assert result.use_web is False

    def test_planner_with_short_user_context(self, mock_backend, mock_tracer):
        """Planner should use research when user_context < 300 chars."""
        worker = PlannerWorker()
        state = State(
            topic="如何提升个人品牌",
            user_context="我是产品经理"  # Short context
        )

        # Mock backend to return need research
        mock_backend.create.return_value = Mock(
            content_text='{"use_private": true, "use_web": true, "reason": "上下文不足，需全量调研"}'
        )

        result = worker.run(state, mock_backend, mock_tracer)

        # Should need at least one type of research
        assert result.use_private or result.use_web

    def test_planner_updates_state(self, mock_backend, mock_tracer):
        """Planner correctly updates State object."""
        worker = PlannerWorker()
        state = State(topic="测试选题")

        mock_backend.create.return_value = Mock(
            content_text='{"use_private": true, "use_web": false, "reason": "只需私域"}'
        )

        result = worker.run(state, mock_backend, mock_tracer)

        assert state.use_private is True
        assert state.use_web is False
        assert state.planner_reason == "只需私域"


class TestPlannerIntegration:
    """Test Planner with real-like scenarios."""

    def test_planner_four_decision_paths(self, mock_backend, mock_tracer):
        """Planner supports 4 decision paths."""
        worker = PlannerWorker()

        # Path 1: AI-only (both False)
        state1 = State(topic="测试1", user_context="详细上下文" * 100)
        mock_backend.create.return_value = Mock(
            content_text='{"use_private": false, "use_web": false, "reason": "上下文充足"}'
        )
        result1 = worker.run(state1, mock_backend, mock_tracer)
        assert not result1.use_private and not result1.use_web

        # Path 2: Private only
        state2 = State(topic="测试2")
        mock_backend.create.return_value = Mock(
            content_text='{"use_private": true, "use_web": false, "reason": "只需私域"}'
        )
        result2 = worker.run(state2, mock_backend, mock_tracer)
        assert result2.use_private and not result2.use_web

        # Path 3: Web only
        state3 = State(topic="测试3")
        mock_backend.create.return_value = Mock(
            content_text='{"use_private": false, "use_web": true, "reason": "只需全网"}'
        )
        result3 = worker.run(state3, mock_backend, mock_tracer)
        assert not result3.use_private and result3.use_web

        # Path 4: Full research (both True)
        state4 = State(topic="测试4")
        mock_backend.create.return_value = Mock(
            content_text='{"use_private": true, "use_web": true, "reason": "全量调研"}'
        )
        result4 = worker.run(state4, mock_backend, mock_tracer)
        assert result4.use_private and result4.use_web

    def test_planner_records_trace(self, mock_backend, mock_tracer):
        """Planner records input/output to tracer."""
        worker = PlannerWorker()
        state = State(topic="测试选题")

        mock_backend.create.return_value = Mock(
            content_text='{"use_private": true, "use_web": false, "reason": "测试"}'
        )

        worker.run(state, mock_backend, mock_tracer)

        # Verify tracer was called
        assert mock_tracer.append_agent_input.called
        assert mock_tracer.append_agent_output.called

        # Check agent name in first call
        if mock_tracer.append_agent_input.call_args:
            # call_args is (args, kwargs)
            args, kwargs = mock_tracer.append_agent_input.call_args
            if args:
                assert args[0] == "Planner"
            elif 'agent_name' in kwargs:
                assert kwargs['agent_name'] == "Planner"

    def test_planner_handles_backend_error(self, mock_backend, mock_tracer):
        """Planner handles backend errors gracefully."""
        worker = PlannerWorker()
        state = State(topic="测试")

        # Mock backend raises exception
        mock_backend.create.side_effect = Exception("API error")

        result = worker.run(state, mock_backend, mock_tracer)

        # Should fallback to safe default
        assert isinstance(result, PlannerResult)
        assert result.use_private is True  # Safe default
        assert result.use_web is True
        assert "错误" in result.reason or "error" in result.reason.lower()
