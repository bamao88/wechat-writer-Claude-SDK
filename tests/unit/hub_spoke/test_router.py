"""Tests for Router module (XML parsing and next_step determination)."""
import pytest
from src.agent.hub_spoke.router import parse_status_signal, determine_next_step
from src.agent.hub_spoke.state import State


class TestParseStatusSignal:
    """Test XML status signal extraction."""

    def test_parse_status_pass(self):
        """Extracts PASS status from XML."""
        output = "文章质量很好。<status>PASS</status>"
        assert parse_status_signal(output) == "PASS"

    def test_parse_status_need_rewrite(self):
        """Extracts NEED_REWRITE status from XML."""
        output = "需要改进。<status>NEED_REWRITE</status>"
        assert parse_status_signal(output) == "NEED_REWRITE"

    def test_parse_status_error(self):
        """Extracts ERROR status from XML."""
        output = "出现错误。<status>ERROR</status>"
        assert parse_status_signal(output) == "ERROR"

    def test_parse_status_with_whitespace(self):
        """Handles whitespace inside XML tags."""
        output = "<status>  PASS  </status>"
        assert parse_status_signal(output) == "PASS"

    def test_parse_status_case_sensitive(self):
        """Status extraction is case-sensitive."""
        output = "<status>pass</status>"
        assert parse_status_signal(output) == "pass"

    def test_parse_status_multiple_tags(self):
        """Returns first status when multiple tags present."""
        output = "<status>PASS</status> and <status>ERROR</status>"
        assert parse_status_signal(output) == "PASS"

    def test_parse_status_no_tag(self):
        """Returns None when no status tag present."""
        output = "这是一段没有状态标签的文本"
        assert parse_status_signal(output) is None

    def test_parse_status_empty_tag(self):
        """Returns empty string when tag is empty."""
        output = "<status></status>"
        assert parse_status_signal(output) == ""

    def test_parse_status_malformed_tag(self):
        """Returns None for malformed tags."""
        output = "<status>PASS"
        assert parse_status_signal(output) is None

    def test_parse_status_with_newlines(self):
        """Handles status tags spanning multiple lines."""
        output = """
        评审结果：
        <status>
        PASS
        </status>
        """
        result = parse_status_signal(output)
        assert result is not None
        assert "PASS" in result


class TestDetermineNextStep:
    """Test next_step determination based on state and agent output."""

    def test_planner_to_miner_when_use_private(self):
        """Planner routes to miner when use_private=True."""
        state = State(topic="测试", use_private=True, use_web=False, next_step="planner")
        next_step = determine_next_step(state, "")
        assert next_step == "miner"

    def test_planner_to_web_when_use_web_only(self):
        """Planner routes to web when use_web=True and use_private=False."""
        state = State(topic="测试", use_private=False, use_web=True, next_step="planner")
        next_step = determine_next_step(state, "")
        assert next_step == "web"

    def test_planner_to_orchestrator_when_both_false(self):
        """Planner routes to orchestrator when both flags are False."""
        state = State(topic="测试", use_private=False, use_web=False, next_step="planner")
        next_step = determine_next_step(state, "")
        assert next_step == "orchestrator"

    def test_planner_to_miner_when_both_true(self):
        """Planner routes to miner first when both flags are True."""
        state = State(topic="测试", use_private=True, use_web=True, next_step="planner")
        next_step = determine_next_step(state, "")
        assert next_step == "miner"

    def test_miner_to_web_when_use_web(self):
        """Miner routes to web when use_web=True."""
        state = State(topic="测试", use_private=True, use_web=True, next_step="miner")
        next_step = determine_next_step(state, "")
        assert next_step == "web"

    def test_miner_to_orchestrator_when_web_false(self):
        """Miner routes to orchestrator when use_web=False."""
        state = State(topic="测试", use_private=True, use_web=False, next_step="miner")
        next_step = determine_next_step(state, "")
        assert next_step == "orchestrator"

    def test_web_to_orchestrator(self):
        """Web always routes to orchestrator."""
        state = State(topic="测试", use_web=True, next_step="web")
        next_step = determine_next_step(state, "")
        assert next_step == "orchestrator"

    def test_orchestrator_to_writer(self):
        """Orchestrator always routes to writer."""
        state = State(topic="测试", next_step="orchestrator")
        next_step = determine_next_step(state, "")
        assert next_step == "writer"

    def test_writer_to_critic(self):
        """Writer always routes to critic."""
        state = State(topic="测试", next_step="writer")
        next_step = determine_next_step(state, "")
        assert next_step == "critic"

    def test_critic_to_done_when_pass(self):
        """Critic routes to done when status is PASS."""
        state = State(topic="测试", next_step="critic")
        output = "<status>PASS</status>"
        next_step = determine_next_step(state, output)
        assert next_step == "done"

    def test_critic_to_writer_when_need_rewrite(self):
        """Critic routes back to writer when status is NEED_REWRITE."""
        state = State(topic="测试", iteration_count=0, next_step="critic")
        output = "<status>NEED_REWRITE</status>"
        next_step = determine_next_step(state, output)
        assert next_step == "writer"

    def test_critic_to_done_when_max_iterations(self):
        """Critic routes to done when max iterations reached."""
        state = State(topic="测试", iteration_count=3, next_step="critic")
        output = "<status>NEED_REWRITE</status>"
        next_step = determine_next_step(state, output)
        assert next_step == "done"

    def test_unknown_next_step_raises_error(self):
        """Unknown next_step raises ValueError."""
        state = State(topic="测试", next_step="unknown")
        with pytest.raises(ValueError, match="Unknown next_step"):
            determine_next_step(state, "")


class TestRouterEdgeCases:
    """Test edge cases and error handling."""

    def test_determine_next_step_with_empty_output(self):
        """determine_next_step handles empty output string."""
        state = State(topic="测试", next_step="orchestrator")
        next_step = determine_next_step(state, "")
        assert next_step == "writer"

    def test_determine_next_step_with_none_output(self):
        """determine_next_step handles None output."""
        state = State(topic="测试", next_step="orchestrator")
        next_step = determine_next_step(state, None)
        assert next_step == "writer"

    def test_parse_status_with_special_characters(self):
        """parse_status_signal handles special characters."""
        output = "<status>PASS & COMPLETE!</status>"
        assert parse_status_signal(output) == "PASS & COMPLETE!"
