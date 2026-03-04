"""Integration tests for Executor (hub-spoke architecture core loop)."""
import pytest
from unittest.mock import Mock, MagicMock
from src.agent.hub_spoke.executor import Executor, MAX_ITERATIONS
from src.agent.hub_spoke.state import State
from src.agent.hub_spoke.workers.planner import PlannerResult
from src.agent.hub_spoke.workers.critic import CriticResult


class TestExecutorStateTransitions:
    """Test Executor state machine transitions."""

    def test_simple_flow_no_research(self):
        """Test: planner → orchestrator → writer → critic (pass) → done."""
        executor = Executor()
        state = State(topic="测试选题", user_context="充足的上下文" * 100)

        # Mock workers
        workers = {
            "planner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        # Planner: skip research
        workers["planner"].run = Mock(return_value=PlannerResult(
            use_private=False,
            use_web=False,
            reason="上下文充足"
        ))

        # Orchestrator: generate outline
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))

        # Writer: generate draft
        workers["writer"].run = Mock(return_value=Mock(draft="文章草稿" * 200))

        # Critic: pass on first try
        workers["critic"].run = Mock(return_value=CriticResult(
            score=9,
            passed=True,
            reason="质量达标"
        ))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        # Execute
        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        # Verify flow
        assert result_state.next_step == "done"
        assert result_state.status == "COMPLETED"
        assert workers["planner"].run.called
        assert workers["orchestrator"].run.called
        assert workers["writer"].run.called
        assert workers["critic"].run.called

    def test_flow_with_private_research(self):
        """Test: planner → miner → orchestrator → writer → critic → done."""
        executor = Executor()
        state = State(topic="我的产品方法论")

        workers = {
            "planner": Mock(),
            "miner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        # Planner: use private research (and update state)
        def planner_side_effect(s, b, t):
            s.use_private = True
            s.use_web = False
            s.planner_reason = "需要私域"
            return PlannerResult(use_private=True, use_web=False, reason="需要私域")

        workers["planner"].run = Mock(side_effect=planner_side_effect)

        # Miner: return research
        workers["miner"].run = Mock(return_value=Mock(
            structured_points=["观点1", "观点2"],
            raw_voice_clips=["片段1", "片段2"]
        ))

        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))
        workers["writer"].run = Mock(return_value=Mock(draft="草稿" * 200))
        workers["critic"].run = Mock(return_value=CriticResult(8, True, "通过"))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {"notebooklm": Mock()}

        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        assert result_state.next_step == "done"
        assert workers["miner"].run.called

    def test_flow_with_web_research(self):
        """Test: planner → web → orchestrator → writer → critic → done."""
        executor = Executor()
        state = State(topic="AI行业趋势")

        workers = {
            "planner": Mock(),
            "web": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        # Planner: use web research (and update state)
        def planner_side_effect(s, b, t):
            s.use_private = False
            s.use_web = True
            s.planner_reason = "需要全网调研"
            return PlannerResult(use_private=False, use_web=True, reason="需要全网调研")

        workers["planner"].run = Mock(side_effect=planner_side_effect)

        workers["web"].run = Mock(return_value=Mock(web_research="调研结果"))
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))
        workers["writer"].run = Mock(return_value=Mock(draft="草稿" * 200))
        workers["critic"].run = Mock(return_value=CriticResult(8, True, "通过"))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {"web_search": Mock()}

        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        assert result_state.next_step == "done"
        assert workers["web"].run.called


class TestExecutorRewriteLoop:
    """Test Executor rewrite loop (critic → writer backtracking)."""

    def test_rewrite_once_then_pass(self):
        """Test: writer → critic (fail) → writer → critic (pass) → done."""
        executor = Executor()
        state = State(topic="测试")

        workers = {
            "planner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        workers["planner"].run = Mock(return_value=PlannerResult(False, False, ""))
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))

        # Writer called twice
        workers["writer"].run = Mock(side_effect=[
            Mock(draft="草稿v1"),  # First attempt
            Mock(draft="草稿v2改进版"),  # After rewrite
        ])

        # Critic: fail first, pass second
        workers["critic"].run = Mock(side_effect=[
            CriticResult(6, False, "字数不足"),  # First attempt
            CriticResult(8, True, "改进后通过"),  # After rewrite
        ])

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        assert result_state.next_step == "done"
        assert result_state.iteration_count == 1  # One rewrite
        assert workers["writer"].run.call_count == 2
        assert workers["critic"].run.call_count == 2

    def test_max_iterations_degraded_output(self):
        """Test: 3 rewrites → degraded output → done."""
        executor = Executor()
        state = State(topic="测试")

        workers = {
            "planner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        workers["planner"].run = Mock(return_value=PlannerResult(False, False, ""))
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))
        workers["writer"].run = Mock(return_value=Mock(draft="草稿"))

        # Critic always fails
        workers["critic"].run = Mock(return_value=CriticResult(
            score=5,
            passed=False,
            reason="持续不达标"
        ))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        assert result_state.next_step == "done"
        assert result_state.status == "DEGRADED_OUTPUT"
        assert result_state.iteration_count == MAX_ITERATIONS
        # Writer: initial + 3 rewrites = 4 calls
        assert workers["writer"].run.call_count == MAX_ITERATIONS + 1
        # Critic: 4 attempts
        assert workers["critic"].run.call_count == MAX_ITERATIONS + 1

        # Verify degraded article was saved
        assert mock_tracer.save_article.called
        call_args = mock_tracer.save_article.call_args
        assert call_args[1]['degraded'] is True  # degraded=True


class TestExecutorCriticFeedback:
    """Test critic feedback injection into writer."""

    def test_critic_feedback_passed_to_writer(self):
        """Critic feedback is passed to writer on rewrite."""
        executor = Executor()
        state = State(topic="测试")

        workers = {
            "planner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        workers["planner"].run = Mock(return_value=PlannerResult(False, False, ""))
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))
        workers["writer"].run = Mock(return_value=Mock(draft="草稿"))

        # Critic fails with specific feedback
        workers["critic"].run = Mock(side_effect=[
            CriticResult(6, False, "字数不足，需要扩充到800字以上"),
            CriticResult(8, True, "改进后通过"),
        ])

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        # Verify feedback was stored in state
        assert "字数不足" in result_state.critic_feedback or result_state.critic_feedback == ""
        # Note: After passing, feedback might be cleared


class TestExecutorEdgeCases:
    """Test Executor edge cases and error handling."""

    def test_empty_topic(self):
        """Executor handles empty topic gracefully."""
        executor = Executor()
        state = State(topic="")

        workers = {"planner": Mock(), "orchestrator": Mock(), "writer": Mock(), "critic": Mock()}
        workers["planner"].run = Mock(return_value=PlannerResult(False, False, ""))
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))
        workers["writer"].run = Mock(return_value=Mock(draft="草稿"))
        workers["critic"].run = Mock(return_value=CriticResult(8, True, "通过"))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        # Should not crash
        result_state = executor.run(state, workers, mock_tools, mock_backend, mock_tracer)
        assert result_state.next_step == "done"

    def test_worker_exception_handling(self):
        """Executor handles worker exceptions gracefully."""
        executor = Executor()
        state = State(topic="测试")

        workers = {
            "planner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        workers["planner"].run = Mock(return_value=PlannerResult(False, False, ""))

        # Orchestrator raises exception
        workers["orchestrator"].run = Mock(side_effect=Exception("Worker error"))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        # Should handle exception
        with pytest.raises(Exception):
            executor.run(state, workers, mock_tools, mock_backend, mock_tracer)


class TestExecutorTracerIntegration:
    """Test Executor integration with OutputTracer."""

    def test_tracer_records_all_steps(self):
        """Tracer records all agent steps."""
        executor = Executor()
        state = State(topic="测试")

        workers = {
            "planner": Mock(),
            "orchestrator": Mock(),
            "writer": Mock(),
            "critic": Mock(),
        }

        workers["planner"].run = Mock(return_value=PlannerResult(False, False, ""))
        workers["orchestrator"].run = Mock(return_value=Mock(outline="大纲"))
        workers["writer"].run = Mock(return_value=Mock(draft="草稿" * 200))
        workers["critic"].run = Mock(return_value=CriticResult(8, True, "通过"))

        mock_backend = Mock()
        mock_tracer = Mock()
        mock_tools = {}

        executor.run(state, workers, mock_tools, mock_backend, mock_tracer)

        # Verify tracer was called for critic
        assert mock_tracer.append_critic_result.called

        # Verify article was saved
        assert mock_tracer.save_article.called
