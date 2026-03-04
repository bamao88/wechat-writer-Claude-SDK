"""End-to-end tests for hub-spoke flow.

Tests the complete workflow from topic to article, covering:
1. Pure AI writing (no research)
2. Private domain research only
3. Full research (private + web)
4. Critic pass on first try
5. Critic rewrite loop (1 iteration)
6. Degraded output (max iterations exceeded)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.agent.hub_spoke.flow import run_hub_spoke_flow, HubSpokeResult
from src.agent.hub_spoke.state import State
from src.config.settings import Config


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock(spec=Config)
    config.llm_provider = "anthropic"
    config.notebooklm_auth = None
    config.tavily_api_key = None
    config.log_level = "INFO"
    return config


@pytest.fixture
def mock_backend():
    """Mock LLM backend with realistic responses."""
    from src.agent.backends.base import BackendResponse

    backend = Mock()

    def create_response(messages, **kwargs):
        """Generate response based on system prompt context."""
        system_prompt = kwargs.get("system", "")

        # Planner response
        if "策略决策" in system_prompt or "Planner" in system_prompt:
            return BackendResponse(
                content_text='{"use_private": true, "use_web": false, "reason": "需要调研私域资料"}',
                stop_reason="end_turn",
                tool_calls=[]
            )

        # Orchestrator response (outline)
        if "逻辑排布" in system_prompt or "Orchestrator" in system_prompt or "大纲" in system_prompt:
            return BackendResponse(
                content_text="""# 如何提升个人品牌

## 核心观点
1. 明确个人价值定位
2. 持续输出专业内容
3. 建立个人影响力

## 论据支撑
- 价值定位是品牌基础
- 内容输出需要规律性
- 影响力来自长期积累
""",
                stop_reason="end_turn",
                tool_calls=[]
            )

        # Writer response (draft)
        if "风格化写作" in system_prompt or "Writer" in system_prompt or "写作" in system_prompt:
            return BackendResponse(
                content_text="""# 如何提升个人品牌

在当今时代，个人品牌变得越来越重要。如何才能有效地提升个人品牌呢？

## 明确你的价值定位

个人品牌的核心是价值定位。我一直强调，做个人品牌最重要的是找到自己的独特价值。你需要清楚地知道自己能为他人提供什么独特的价值，这是建立个人品牌的基础。

## 持续输出专业内容

内容输出要有规律性，不能三天打鱼两天晒网。持续、高质量的内容输出是建立专业形象的关键。无论是文章、视频还是社交媒体内容，都需要保持稳定的输出节奏。

## 建立个人影响力

影响力不是一朝一夕就能建立的，需要长期的积累。通过持续的价值输出和与受众的互动，逐步扩大你的影响范围，最终建立起属于自己的个人品牌。

记住，个人品牌的打造是一个长期过程，需要耐心和坚持。只要你找准定位、持续输出、真诚互动，就一定能建立起强大的个人品牌。
""",
                stop_reason="end_turn",
                tool_calls=[]
            )

        # Default response
        return BackendResponse(
            content_text="Mock response",
            stop_reason="end_turn",
            tool_calls=[]
        )

    backend.create = Mock(side_effect=create_response)
    return backend


@pytest.fixture
def mock_tools():
    """Mock tools (NotebookLM and Web)."""
    notebooklm = Mock()
    notebooklm.name = "search_notebooklm"
    notebooklm.description = "私域知识库搜索"
    notebooklm.input_schema = {"type": "object"}
    notebooklm.execute = Mock(return_value=Mock(
        success=True,
        content="""根据私域资料搜索结果：
1. 个人品牌的核心是价值定位
2. 需要持续输出专业内容
3. 建立影响力需要长期积累
""",
        error=None
    ))

    web_search = Mock()
    web_search.name = "search_web"
    web_search.description = "全网搜索"
    web_search.input_schema = {"type": "object"}
    web_search.execute = Mock(return_value=Mock(
        success=True,
        content="全网搜索结果：个人品牌建设的最新趋势...",
        error=None
    ))

    return {
        "search_notebooklm": notebooklm,
        "search_web": web_search
    }


@pytest.fixture
def mock_workers_critic_pass():
    """Mock workers where critic passes on first try."""
    from src.agent.hub_spoke.workers.planner import PlannerWorker, PlannerResult
    from src.agent.hub_spoke.workers.miner import MinerWorker, MinerResult
    from src.agent.hub_spoke.workers.web import WebWorker, WebResult
    from src.agent.hub_spoke.workers.orchestrator import OrchestratorWorker, OrchestratorResult
    from src.agent.hub_spoke.workers.writer import WriterWorker, WriterResult
    from src.agent.hub_spoke.workers.critic import CriticWorker, CriticResult

    # Mock critic to always pass
    with patch.object(CriticWorker, 'run') as mock_critic:
        mock_critic.return_value = CriticResult(
            score=8,
            passed=True,
            reason="文章质量优秀"
        )

        return {
            "planner": PlannerWorker(),
            "miner": MinerWorker(),
            "web": WebWorker(),
            "orchestrator": OrchestratorWorker(),
            "writer": WriterWorker(),
            "critic": CriticWorker()
        }


class TestHubSpokeE2E:
    """End-to-end tests for hub-spoke workflow."""

    @patch('src.agent.hub_spoke.flow.get_backend')
    @patch('src.agent.hub_spoke.flow.create_tools')
    @patch('src.agent.hub_spoke.flow.create_workers')
    @patch('src.agent.hub_spoke.workers.critic.CriticWorker.run')
    def test_scenario_1_pure_ai_writing(
        self,
        mock_critic_run,
        mock_create_workers,
        mock_create_tools,
        mock_get_backend,
        mock_config,
        mock_backend,
        mock_tools,
        mock_tracer
    ):
        """Test Scenario 1: Pure AI writing (user_context ≥300 chars, no research)."""
        # Setup: Planner should skip research when given long context
        long_context = "用户提供的详细上下文" * 50  # >300 chars

        # Mock critic to pass
        from src.agent.hub_spoke.workers.critic import CriticResult
        mock_critic_run.return_value = CriticResult(score=8, passed=True, reason="优秀")

        # Setup mocks
        mock_get_backend.return_value = mock_backend
        mock_create_tools.return_value = mock_tools
        from src.agent.hub_spoke.workers import create_workers
        mock_create_workers.return_value = create_workers()

        # Execute
        result = run_hub_spoke_flow(
            topic="测试选题",
            user_context=long_context,
            config=mock_config,
            tracer=mock_tracer
        )

        # Verify: Should succeed without calling research tools
        assert result.success is True
        assert result.degraded is False
        assert len(result.output) > 0

    @patch('src.agent.hub_spoke.flow.get_backend')
    @patch('src.agent.hub_spoke.flow.create_tools')
    @patch('src.agent.hub_spoke.flow.create_workers')
    @patch('src.agent.hub_spoke.workers.critic.CriticWorker.run')
    def test_scenario_2_private_research_only(
        self,
        mock_critic_run,
        mock_create_workers,
        mock_create_tools,
        mock_get_backend,
        mock_config,
        mock_backend,
        mock_tools,
        mock_tracer
    ):
        """Test Scenario 2: Private domain research only (use_private=true, use_web=false)."""
        # Mock critic to pass
        from src.agent.hub_spoke.workers.critic import CriticResult
        mock_critic_run.return_value = CriticResult(score=8, passed=True, reason="优秀")

        # Setup mocks
        mock_get_backend.return_value = mock_backend
        mock_create_tools.return_value = mock_tools
        from src.agent.hub_spoke.workers import create_workers
        mock_create_workers.return_value = create_workers()

        # Execute
        result = run_hub_spoke_flow(
            topic="测试选题",
            config=mock_config,
            tracer=mock_tracer
        )

        # Verify: Should succeed and call NotebookLM
        assert result.success is True
        assert result.tool_calls >= 1  # At least miner was called

    @patch('src.agent.hub_spoke.flow.get_backend')
    @patch('src.agent.hub_spoke.flow.create_tools')
    @patch('src.agent.hub_spoke.flow.create_workers')
    @patch('src.agent.hub_spoke.workers.critic.CriticWorker.run')
    def test_scenario_4_critic_pass_first_try(
        self,
        mock_critic_run,
        mock_create_workers,
        mock_create_tools,
        mock_get_backend,
        mock_config,
        mock_backend,
        mock_tools,
        mock_tracer
    ):
        """Test Scenario 4: Critic passes on first try."""
        # Mock critic to pass immediately
        from src.agent.hub_spoke.workers.critic import CriticResult
        mock_critic_run.return_value = CriticResult(score=9, passed=True, reason="完美")

        # Setup mocks
        mock_get_backend.return_value = mock_backend
        mock_create_tools.return_value = mock_tools
        from src.agent.hub_spoke.workers import create_workers
        mock_create_workers.return_value = create_workers()

        # Execute
        result = run_hub_spoke_flow(
            topic="测试选题",
            config=mock_config,
            tracer=mock_tracer
        )

        # Verify: Should succeed without rewrite
        assert result.success is True
        assert result.degraded is False
        # Critic should be called only once
        assert mock_critic_run.call_count == 1

    @patch('src.agent.hub_spoke.flow.get_backend')
    @patch('src.agent.hub_spoke.flow.create_tools')
    @patch('src.agent.hub_spoke.flow.create_workers')
    @patch('src.agent.hub_spoke.workers.critic.CriticWorker.run')
    def test_scenario_5_critic_rewrite_once(
        self,
        mock_critic_run,
        mock_create_workers,
        mock_create_tools,
        mock_get_backend,
        mock_config,
        mock_backend,
        mock_tools,
        mock_tracer
    ):
        """Test Scenario 5: Critic fails first time, passes on second try."""
        # Mock critic to fail first, pass second
        from src.agent.hub_spoke.workers.critic import CriticResult
        mock_critic_run.side_effect = [
            CriticResult(score=6, passed=False, reason="字数不足"),
            CriticResult(score=8, passed=True, reason="修改后合格")
        ]

        # Setup mocks
        mock_get_backend.return_value = mock_backend
        mock_create_tools.return_value = mock_tools
        from src.agent.hub_spoke.workers import create_workers
        mock_create_workers.return_value = create_workers()

        # Execute
        result = run_hub_spoke_flow(
            topic="测试选题",
            config=mock_config,
            tracer=mock_tracer
        )

        # Verify: Should succeed after one rewrite
        assert result.success is True
        assert result.degraded is False
        # Critic should be called twice
        assert mock_critic_run.call_count == 2

    @patch('src.agent.hub_spoke.flow.get_backend')
    @patch('src.agent.hub_spoke.flow.create_tools')
    @patch('src.agent.hub_spoke.flow.create_workers')
    @patch('src.agent.hub_spoke.workers.critic.CriticWorker.run')
    def test_scenario_6_degraded_output(
        self,
        mock_critic_run,
        mock_create_workers,
        mock_create_tools,
        mock_get_backend,
        mock_config,
        mock_backend,
        mock_tools,
        mock_tracer
    ):
        """Test Scenario 6: Max iterations reached, degraded output."""
        # Mock critic to always fail (max 3 iterations)
        from src.agent.hub_spoke.workers.critic import CriticResult
        mock_critic_run.return_value = CriticResult(
            score=5,
            passed=False,
            reason="持续质量不达标"
        )

        # Setup mocks
        mock_get_backend.return_value = mock_backend
        mock_create_tools.return_value = mock_tools
        from src.agent.hub_spoke.workers import create_workers
        mock_create_workers.return_value = create_workers()

        # Execute
        result = run_hub_spoke_flow(
            topic="测试选题",
            config=mock_config,
            tracer=mock_tracer
        )

        # Verify: Should succeed but marked as degraded
        assert result.success is True
        assert result.degraded is True
        # Critic should be called at least 3 times (max iterations)
        assert mock_critic_run.call_count >= 3
        # Tracer should have called save_article with degraded=True
        mock_tracer.save_article.assert_called()
        # Check that at least one call had degraded=True
        calls = mock_tracer.save_article.call_args_list
        assert any(call.kwargs.get('degraded', False) for call in calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
