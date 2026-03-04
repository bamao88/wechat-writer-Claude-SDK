#!/usr/bin/env python3
"""
Phase 2 Core Agents Integration Test with Real API

This script tests Planner and Critic agents using real Azure OpenAI API.

Test scenarios:
1. Planner decision making (4 paths)
2. Critic quality checks (rule-based)
3. Planner + Critic workflow integration
4. Real API with various topics

Usage:
    python scripts/test_phase2_agents.py
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.hub_spoke.state import State
from src.agent.hub_spoke.workers.planner import PlannerWorker
from src.agent.hub_spoke.workers.critic import CriticWorker
from src.agent.backends import get_backend
from src.output.tracer import OutputTracer
from src.config.settings import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_planner_four_paths():
    """Test 1: Planner 4 decision paths with real API."""
    print("\n" + "="*80)
    print("Test 1: Planner 4 Decision Paths")
    print("="*80)

    import os
    from dotenv import load_dotenv
    load_dotenv()

    config = Config(
        notebook_id=os.getenv("NOTEBOOK_ID", "test"),
        notebook_url=os.getenv("NOTEBOOK_URL", "https://example.com"),
        retry_count=3,
        retry_delay_sec=2.0,
        timeout_sec=30.0,
        log_level="INFO",
        notebooklm_skill_dir="notebooklm_skill",
        llm_provider=os.getenv("WECHAT_WRITER_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai",
    )

    backend = get_backend(config.llm_provider)
    planner = PlannerWorker()

    test_cases = [
        {
            "name": "纯AI写作（长上下文）",
            "topic": "如何提升个人品牌",
            "user_context": "我是一个有10年经验的产品经理，在B端SaaS领域深耕多年。" * 10,  # >300 chars
            "expected": "可能both=false（如果LLM判断上下文足够）"
        },
        {
            "name": "全量调研（无上下文）",
            "topic": "2026年AI行业发展趋势",
            "user_context": "",
            "expected": "应该both=true（需要调研）"
        },
        {
            "name": "私域调研（个人经验类）",
            "topic": "我的产品管理方法论",
            "user_context": "分享我的经验",
            "expected": "倾向use_private=true"
        },
        {
            "name": "全网调研（客观分析类）",
            "topic": "ChatGPT vs Claude性能对比",
            "user_context": "",
            "expected": "倾向use_web=true"
        },
    ]

    results = []
    tmp_dir = Path("outputs") / f"phase2_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Path {i}: {case['name']} ---")
        print(f"选题: {case['topic']}")
        print(f"上下文长度: {len(case['user_context'])} 字")

        output_dir = tmp_dir / f"path{i}"
        tracer = OutputTracer(output_dir)
        tracer.start()

        state = State(
            topic=case['topic'],
            user_context=case['user_context']
        )

        try:
            result = planner.run(state, backend, tracer)
            tracer.close()

            print(f"✓ 决策结果:")
            print(f"  use_private: {result.use_private}")
            print(f"  use_web: {result.use_web}")
            print(f"  原因: {result.reason}")
            print(f"  预期: {case['expected']}")

            # Verify state was updated
            assert state.use_private == result.use_private
            assert state.use_web == result.use_web
            assert state.planner_reason == result.reason

            results.append((case['name'], True, result))

        except Exception as e:
            print(f"✗ 错误: {e}")
            results.append((case['name'], False, str(e)))
            tracer.close()

    return results


def test_critic_quality_checks():
    """Test 2: Critic quality checks with various article qualities."""
    print("\n" + "="*80)
    print("Test 2: Critic Quality Checks")
    print("="*80)

    critic = CriticWorker()

    test_cases = [
        {
            "name": "高质量文章（应通过）",
            "draft": """
# 如何系统化建立个人品牌

在当今信息爆炸的时代，个人品牌已成为职场人士的核心竞争力。本文将从价值定位、内容输出、互动运营三个维度，分享系统化建立个人品牌的方法论。

## 一、价值定位：找到你的独特性

价值定位是个人品牌的基石。我们需要深入思考：在所处领域，你的核心竞争力是什么？这不仅仅是技能，更是你独特的视角和方法论。""" + "详细论述内容" * 100 + """

## 二、内容输出：持续创造价值

内容输出的持续性至关重要。建议每周至少发布2篇高质量内容，保持稳定的更新频率。质量永远比数量重要。""" + "详细论述内容" * 100 + """

## 三、互动运营：建立深度连接

建立自己的社群，与读者建立更紧密的连接。积极收集读者反馈，不断优化内容方向。""" + "详细论述内容" * 100 + """

## 总结

个人品牌的建立是一个长期过程，需要持续投入。只要坚持系统化的方法，每个人都能建立属于自己的个人品牌。
""",
            "outline": """
# 大纲
- 价值定位
- 内容输出
- 互动运营
""",
            "expected_pass": True,
            "expected_score_range": (8, 10)
        },
        {
            "name": "字数不足（应失败）",
            "draft": "# 标题\n\n这是一篇很短的文章。",
            "outline": "大纲",
            "expected_pass": False,
            "expected_score_range": (0, 5)
        },
        {
            "name": "缺少结构（应失败）",
            "draft": "没有标题和章节。" + "x" * 800,
            "outline": "大纲",
            "expected_pass": False,
            "expected_score_range": (0, 6)
        },
        {
            "name": "大纲论点缺失（应失败）",
            "draft": """
# 文章标题

## 第一章

只谈了第一个点。""" + "x" * 800,
            "outline": """
- 论点A
- 论点B（缺失）
- 论点C（缺失）
""",
            "expected_pass": False,
            "expected_score_range": (0, 6)
        },
    ]

    results = []

    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Case {i}: {case['name']} ---")

        state = State(topic="测试")
        state.draft = case['draft']
        state.outline = case['outline']

        result = critic.run(state)

        print(f"✓ 评分: {result.score}/10")
        print(f"  通过: {result.passed}")
        print(f"  原因: {result.reason[:100]}...")
        print(f"  预期: {'通过' if case['expected_pass'] else '失败'}, 评分 {case['expected_score_range']}")

        # Verify expectations
        score_in_range = case['expected_score_range'][0] <= result.score <= case['expected_score_range'][1]
        pass_matches = result.passed == case['expected_pass']

        if score_in_range and pass_matches:
            print(f"  ✓ 符合预期")
            results.append((case['name'], True, result))
        else:
            print(f"  ✗ 不符合预期")
            results.append((case['name'], False, result))

    return results


def test_planner_critic_integration():
    """Test 3: Planner + Critic workflow integration with real API."""
    print("\n" + "="*80)
    print("Test 3: Planner + Critic Workflow Integration")
    print("="*80)

    import os
    from dotenv import load_dotenv
    load_dotenv()

    config = Config(
        notebook_id=os.getenv("NOTEBOOK_ID", "test"),
        notebook_url=os.getenv("NOTEBOOK_URL", "https://example.com"),
        retry_count=3,
        retry_delay_sec=2.0,
        timeout_sec=30.0,
        log_level="INFO",
        notebooklm_skill_dir="notebooklm_skill",
        llm_provider=os.getenv("WECHAT_WRITER_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai",
    )

    backend = get_backend(config.llm_provider)
    planner = PlannerWorker()
    critic = CriticWorker()

    tmp_dir = Path("outputs") / f"phase2_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}" / "integration"
    tracer = OutputTracer(tmp_dir)
    tracer.start()

    print("\nStep 1: Planner决策")
    state = State(
        topic="AI产品经理的核心能力",
        user_context="简短上下文"
    )

    planner_result = planner.run(state, backend, tracer)
    print(f"✓ Planner决策: use_private={planner_result.use_private}, use_web={planner_result.use_web}")

    # Simulate a draft article for Critic
    print("\nStep 2: Critic评审（模拟草稿）")

    # Good draft
    state.draft = """
# AI产品经理的核心能力

在AI时代，产品经理需要掌握新的能力体系。本文将分析AI产品经理的核心竞争力。

## 一、技术理解能力

理解AI模型的原理和局限性是基础。""" + "详细论述" * 100 + """

## 二、场景洞察能力

找到AI能够真正解决问题的场景。""" + "详细论述" * 100 + """

## 三、产品设计能力

设计符合AI特性的产品体验。""" + "详细论述" * 100 + """

## 总结

AI产品经理需要技术、场景、设计的综合能力。
"""
    state.outline = """
- 技术理解能力
- 场景洞察能力
- 产品设计能力
"""

    critic_result = critic.run(state)
    tracer.append_critic_result(1, critic_result.score, critic_result.passed, critic_result.reason)

    print(f"✓ Critic评分: {critic_result.score}/10")
    print(f"  通过: {critic_result.passed}")
    print(f"  原因: {critic_result.reason}")

    # Save article based on critic result
    tracer.save_article(state.draft, degraded=not critic_result.passed)
    tracer.close()

    print(f"\n✓ 工作流完成")
    print(f"  输出目录: {tmp_dir}")
    print(f"  Trace文件: {tracer.trace_path}")
    print(f"  文章文件: {tracer.article_path}")

    return critic_result.passed


def test_planner_error_handling():
    """Test 4: Planner error handling (malformed API response)."""
    print("\n" + "="*80)
    print("Test 4: Planner Error Handling")
    print("="*80)

    from unittest.mock import Mock

    planner = PlannerWorker()

    # Test with malformed JSON
    print("\n--- Malformed JSON Response ---")
    state = State(topic="测试")

    mock_backend = Mock()
    mock_backend.create.return_value = Mock(
        content_text='这不是JSON格式的输出'
    )

    mock_tracer = Mock()
    mock_tracer.append_agent_input = Mock()
    mock_tracer.append_agent_output = Mock()

    result = planner.run(state, mock_backend, mock_tracer)

    print(f"✓ Fallback结果: use_private={result.use_private}, use_web={result.use_web}")
    print(f"  原因: {result.reason[:100]}...")

    # Should fallback to safe default (both True)
    assert result.use_private is True
    assert result.use_web is True
    assert "解析" in result.reason or "fallback" in result.reason.lower()

    print(f"✓ 错误处理正常（已fallback到安全默认值）")

    return True


def main():
    """Run all Phase 2 integration tests."""
    print("=" * 80)
    print("Phase 2 Core Agents Integration Test")
    print("Testing Planner + Critic with Real API")
    print("=" * 80)

    import os
    from dotenv import load_dotenv
    load_dotenv()

    llm_provider = os.getenv("WECHAT_WRITER_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai"
    print(f"\nConfiguration:")
    print(f"  Provider: {llm_provider}")

    if llm_provider == "openai":
        openai_base = os.getenv("WECHAT_WRITER_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        openai_model = os.getenv("WECHAT_WRITER_OPENAI_MODEL") or os.getenv("OPENAI_MODEL")
        print(f"  Base URL: {openai_base[:60] if openai_base else None}...")
        print(f"  Model: {openai_model}")

    all_results = []

    try:
        # Test 1: Planner 4 paths
        planner_results = test_planner_four_paths()
        all_results.append(("Planner 4 Paths", all(r[1] for r in planner_results)))

        # Test 2: Critic checks
        critic_results = test_critic_quality_checks()
        all_results.append(("Critic Quality Checks", all(r[1] for r in critic_results)))

        # Test 3: Integration
        integration_passed = test_planner_critic_integration()
        all_results.append(("Planner + Critic Integration", integration_passed))

        # Test 4: Error handling
        error_handling_passed = test_planner_error_handling()
        all_results.append(("Error Handling", error_handling_passed))

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for name, passed in all_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in all_results)

    if all_passed:
        print("\n🎉 All Phase 2 integration tests passed!")
        print("\n✅ Planner Agent: 可正常决策4种路径")
        print("✅ Critic Agent: 规则检查100%准确")
        print("✅ 工作流集成: Planner → Critic → 输出")
        print("✅ 错误处理: Fallback机制正常")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
