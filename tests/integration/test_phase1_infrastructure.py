#!/usr/bin/env python3
"""
Phase 1 Infrastructure Integration Test with Real API

This script tests the Phase 1 components (State, Router, Tracer) using real LLM backends.

Test scenarios:
1. State creation and mutation
2. Router XML parsing with real LLM outputs
3. OutputTracer recording (including critic results and degraded output)
4. State serialization/deserialization
5. Full workflow simulation: planner → miner → orchestrator → writer → critic (with rewrite)

Usage:
    python scripts/test_phase1_infrastructure.py
"""
import sys
import json
from pathlib import Path
from dataclasses import asdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.hub_spoke.state import State
from src.agent.hub_spoke.router import parse_status_signal, determine_next_step, MAX_ITERATIONS
from src.output.tracer import OutputTracer
from src.agent.backends import get_backend
from src.config.settings import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_state_operations():
    """Test 1: State creation, mutation, and serialization."""
    print("\n" + "="*80)
    print("Test 1: State Operations")
    print("="*80)

    # Create state
    state = State(
        topic="如何提升个人品牌",
        user_context="我是一个产品经理，想要在公众号建立影响力"
    )

    print(f"✓ State created with topic: {state.topic}")
    print(f"✓ Initial next_step: {state.next_step}")
    print(f"✓ Initial status: {state.status}")

    # Mutate state (simulate planner decision)
    state.use_private = True
    state.use_web = True
    state.planner_reason = "用户上下文不足300字，需要全量调研"
    state.next_step = "miner"

    print(f"✓ After planner: use_private={state.use_private}, use_web={state.use_web}")

    # Simulate miner output
    state.structured_points = [
        "个人品牌的核心是价值定位",
        "需要持续输出专业内容"
    ]
    state.raw_voice_clips = [
        "我一直强调，做个人品牌最重要的是找到自己的独特价值",
        "内容输出要有规律性，不能三天打鱼两天晒网"
    ]
    state.next_step = "orchestrator"

    print(f"✓ After miner: {len(state.structured_points)} points, {len(state.raw_voice_clips)} clips")

    # Test serialization
    state_dict = asdict(state)
    assert "topic" in state_dict
    assert "structured_points" in state_dict
    assert len(state_dict["structured_points"]) == 2

    print(f"✓ State serialization: {len(state_dict)} fields")
    print(f"  Sample: topic='{state_dict['topic'][:30]}...', next_step='{state_dict['next_step']}'")

    return state


def test_router_xml_parsing():
    """Test 2: Router XML parsing with various formats."""
    print("\n" + "="*80)
    print("Test 2: Router XML Parsing")
    print("="*80)

    test_cases = [
        ("文章质量很好。<status>PASS</status>", "PASS"),
        ("需要改进。<status>NEED_REWRITE</status>", "NEED_REWRITE"),
        ("<status>  PASS  </status>", "PASS"),
        ("这是一段没有状态标签的文本", None),
        ("<status></status>", ""),
    ]

    for output, expected in test_cases:
        result = parse_status_signal(output)
        status = "✓" if result == expected else "✗"
        print(f"{status} parse_status_signal('{output[:30]}...') = {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    return True


def test_router_state_transitions():
    """Test 3: Router state machine transitions."""
    print("\n" + "="*80)
    print("Test 3: Router State Transitions")
    print("="*80)

    # Test planner → miner (when use_private=True)
    state = State(topic="测试", use_private=True, use_web=False, next_step="planner")
    next_step = determine_next_step(state, "")
    print(f"✓ planner (use_private=True) → {next_step} (expected: miner)")
    assert next_step == "miner"

    # Test miner → web (when use_web=True)
    state.next_step = "miner"
    state.use_web = True
    next_step = determine_next_step(state, "")
    print(f"✓ miner (use_web=True) → {next_step} (expected: web)")
    assert next_step == "web"

    # Test web → orchestrator
    state.next_step = "web"
    next_step = determine_next_step(state, "")
    print(f"✓ web → {next_step} (expected: orchestrator)")
    assert next_step == "orchestrator"

    # Test orchestrator → writer
    state.next_step = "orchestrator"
    next_step = determine_next_step(state, "")
    print(f"✓ orchestrator → {next_step} (expected: writer)")
    assert next_step == "writer"

    # Test writer → critic
    state.next_step = "writer"
    next_step = determine_next_step(state, "")
    print(f"✓ writer → {next_step} (expected: critic)")
    assert next_step == "critic"

    # Test critic → done (when PASS)
    state.next_step = "critic"
    next_step = determine_next_step(state, "<status>PASS</status>")
    print(f"✓ critic (PASS) → {next_step} (expected: done)")
    assert next_step == "done"

    # Test critic → writer (when NEED_REWRITE)
    state.next_step = "critic"
    state.iteration_count = 0
    next_step = determine_next_step(state, "<status>NEED_REWRITE</status>")
    print(f"✓ critic (NEED_REWRITE, iteration=0) → {next_step} (expected: writer)")
    assert next_step == "writer"

    # Test critic → done (when max iterations)
    state.iteration_count = MAX_ITERATIONS
    next_step = determine_next_step(state, "<status>NEED_REWRITE</status>")
    print(f"✓ critic (NEED_REWRITE, iteration={MAX_ITERATIONS}) → {next_step} (expected: done)")
    assert next_step == "done"

    return True


def test_tracer_operations(tmp_dir: Path):
    """Test 4: OutputTracer recording with critic results and degraded output."""
    print("\n" + "="*80)
    print("Test 4: OutputTracer Operations")
    print("="*80)

    output_dir = tmp_dir / "test_output"
    tracer = OutputTracer(output_dir)
    tracer.start()

    print(f"✓ Tracer initialized: {output_dir}")

    # Simulate agent workflow
    tracer.append_agent_input(
        agent_name="Planner",
        system_prompt="你是一个策略规划专家，决定调研路径。",
        messages=[{"role": "user", "content": "选题：如何提升个人品牌"}],
        routing_info={
            "triggered_by": "User",
            "reason": "开始新的写作任务",
            "expected_output": "use_private和use_web决策"
        }
    )
    tracer.append_agent_output('{"use_private": true, "use_web": false, "reason": "需要私域调研"}', "Planner")

    print("✓ Recorded Planner input/output")

    # Simulate writer attempts with critic feedback
    for cycle in [1, 2, 3]:
        tracer.append_agent_input(
            agent_name="Writer",
            system_prompt=f"第{cycle}轮写作" + ("\n反馈：" + f"改进第{cycle-1}轮问题" if cycle > 1 else ""),
            messages=[{"role": "user", "content": "写一篇文章"}],
        )
        tracer.append_agent_output(f"这是第{cycle}版草稿...", "Writer")

        # Critic evaluation
        if cycle == 1:
            tracer.append_critic_result(cycle, 5, False, "字数不足（仅600字）")
        elif cycle == 2:
            tracer.append_critic_result(cycle, 6, False, "结构不完整，缺少案例")
        else:
            tracer.append_critic_result(cycle, 7, False, "仍未达标，超出重写次数")

    print(f"✓ Recorded 3 rewrite cycles with critic results")

    # Save degraded article
    article_content = "# 如何提升个人品牌\n\n这是一篇经过3轮重写仍未达标的文章内容..."
    tracer.save_article(article_content, degraded=True)

    print("✓ Saved degraded article with warning")

    # Close tracer (generates summary)
    tracer.close()

    # Verify files
    assert tracer.trace_path.exists(), "thought_trace.md should exist"
    assert tracer.article_path.exists(), "article.md should exist"

    trace_content = tracer.trace_path.read_text(encoding='utf-8')
    article_content_saved = tracer.article_path.read_text(encoding='utf-8')

    # Verify trace contains critic results
    assert "Critic Result" in trace_content
    assert "Cycle 1" in trace_content or "第1轮" in trace_content
    assert "Cycle 2" in trace_content or "第2轮" in trace_content
    assert "Cycle 3" in trace_content or "第3轮" in trace_content
    print("✓ Trace file contains 3 critic results")

    # Verify article has degraded warning
    assert "⚠️" in article_content_saved
    assert "质量检查" in article_content_saved or "降级" in article_content_saved
    print("✓ Article has degraded warning at top")

    # Verify summary was generated
    assert "执行摘要" in trace_content or "📊" in trace_content
    print("✓ Trace file has execution summary")

    print(f"\nTrace file: {tracer.trace_path}")
    print(f"Article file: {tracer.article_path}")

    return True


def test_real_llm_xml_parsing(config: Config):
    """Test 5: Real LLM API call to generate XML output and parse it."""
    print("\n" + "="*80)
    print("Test 5: Real LLM API with XML Parsing")
    print("="*80)

    backend = get_backend(config.llm_provider)
    print(f"✓ Backend initialized: {config.llm_provider}")

    # Test prompt that should produce XML output
    system_prompt = """你是一个文章质量评审专家。请评估以下文章质量，并按以下格式输出：

1. 给出评分（1-10分）
2. 说明原因
3. 最后用XML标签输出状态：<status>PASS</status> 或 <status>NEED_REWRITE</status>

如果评分≥7，输出PASS；否则输出NEED_REWRITE。
"""

    article = """
# 如何提升个人品牌

个人品牌的建立是一个长期过程，需要持续的价值输出和专业形象塑造。

## 核心要素
1. 价值定位：明确自己的独特价值
2. 内容输出：持续产出高质量内容
3. 互动运营：与读者建立深度连接

建议从公众号开始，每周至少发布2篇原创文章。
"""

    messages = [{"role": "user", "content": f"请评估这篇文章：\n\n{article}"}]

    print("Calling LLM API...")
    try:
        response = backend.create(
            system=system_prompt,
            messages=messages,
            tools=[],  # No tools needed for this test
            max_tokens=500,
        )

        # Extract text from response
        if hasattr(response, 'content') and len(response.content) > 0:
            output_text = response.content[0].text
        else:
            output_text = str(response)

        print(f"✓ LLM response received ({len(output_text)} chars)")
        print(f"\nLLM Output:\n{'-'*60}\n{output_text}\n{'-'*60}")

        # Parse status signal
        status = parse_status_signal(output_text)
        print(f"\n✓ Parsed status: {status}")

        if status in ["PASS", "NEED_REWRITE"]:
            print(f"✓ Valid status extracted: {status}")
        else:
            print(f"⚠ Warning: Unexpected status '{status}' (expected PASS or NEED_REWRITE)")
            print("  This is OK - LLM may not always follow format perfectly")

        # Test router with this output
        state = State(topic="测试", next_step="critic", iteration_count=0)
        next_step = determine_next_step(state, output_text)
        print(f"✓ Router determined next_step: {next_step}")

        return True

    except Exception as e:
        print(f"✗ Error calling LLM API: {e}")
        print(f"  Provider: {config.llm_provider}")
        print("\n  Make sure your API credentials are configured correctly.")
        return False


def test_workflow_simulation(config: Config, tmp_dir: Path):
    """Test 6: Full workflow simulation from planner to critic."""
    print("\n" + "="*80)
    print("Test 6: Full Workflow Simulation")
    print("="*80)

    output_dir = tmp_dir / "workflow_test"
    tracer = OutputTracer(output_dir)
    tracer.start()

    # Initialize state
    state = State(
        topic="如何提升个人品牌",
        user_context="我是产品经理"
    )

    print(f"Initial state: next_step={state.next_step}, status={state.status}")

    # Simulate workflow steps
    steps = []

    # Step 1: Planner
    state.use_private = True
    state.use_web = False
    state.planner_reason = "需要私域调研"
    old_step = state.next_step
    state.next_step = determine_next_step(state, "")
    steps.append(f"{old_step} → {state.next_step}")
    tracer.append_agent_input("Planner", "策略决策", [])
    tracer.append_agent_output(f"use_private=True, use_web=False", "Planner")

    # Step 2: Miner
    state.structured_points = ["观点A", "观点B"]
    state.raw_voice_clips = ["片段1", "片段2"]
    old_step = state.next_step
    state.next_step = determine_next_step(state, "")
    steps.append(f"{old_step} → {state.next_step}")
    tracer.append_agent_input("Miner", "私域挖掘", [])
    tracer.append_agent_output("挖掘了2个观点和2个原话片段", "Miner")

    # Step 3: Orchestrator
    state.outline = "# 大纲\n\n1. 价值定位\n2. 内容输出"
    old_step = state.next_step
    state.next_step = determine_next_step(state, "")
    steps.append(f"{old_step} → {state.next_step}")
    tracer.append_agent_input("Orchestrator", "逻辑编排", [])
    tracer.append_agent_output("生成了大纲", "Orchestrator")

    # Step 4: Writer (first attempt)
    state.draft = "# 如何提升个人品牌\n\n内容..."
    old_step = state.next_step
    state.next_step = determine_next_step(state, "")
    steps.append(f"{old_step} → {state.next_step}")
    tracer.append_agent_input("Writer", "风格写作", [])
    tracer.append_agent_output("生成了草稿", "Writer")

    # Step 5: Critic (first attempt - fail)
    state.critic_score = 6
    state.critic_reason = "字数不足"
    state.critic_feedback = "需要扩充内容"
    old_step = state.next_step
    state.next_step = determine_next_step(state, "<status>NEED_REWRITE</status>")
    steps.append(f"{old_step} → {state.next_step}")
    state.iteration_count += 1
    tracer.append_critic_result(1, 6, False, "字数不足")

    # Step 6: Writer (second attempt)
    old_step = state.next_step
    state.next_step = determine_next_step(state, "")
    steps.append(f"{old_step} → {state.next_step}")
    tracer.append_agent_input("Writer", "改进写作", [])
    tracer.append_agent_output("生成了改进版草稿", "Writer")

    # Step 7: Critic (second attempt - pass)
    state.critic_score = 8
    state.critic_reason = "质量达标"
    old_step = state.next_step
    state.next_step = determine_next_step(state, "<status>PASS</status>")
    steps.append(f"{old_step} → {state.next_step}")
    tracer.append_critic_result(2, 8, True, "质量达标，结构完整")

    # Save article (not degraded)
    tracer.save_article(state.draft, degraded=False)
    state.status = "COMPLETED"

    tracer.close()

    print("\nWorkflow steps:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")

    print(f"\nFinal state:")
    print(f"  next_step: {state.next_step}")
    print(f"  status: {state.status}")
    print(f"  iteration_count: {state.iteration_count}")
    print(f"  critic_score: {state.critic_score}")

    # Verify
    assert state.next_step == "done"
    assert state.status == "COMPLETED"
    assert state.iteration_count == 1  # Only 1 rewrite

    # Check article has no warning (not degraded)
    article_content = tracer.article_path.read_text(encoding='utf-8')
    assert "⚠️" not in article_content

    print(f"✓ Workflow completed successfully")
    print(f"✓ Article saved without warning (passed quality check)")
    print(f"\nOutput directory: {output_dir}")

    return True


def main():
    """Run all Phase 1 infrastructure tests."""
    print("=" * 80)
    print("Phase 1 Infrastructure Integration Test")
    print("Testing with Real LLM API")
    print("=" * 80)

    # Load config with defaults for Phase 1 testing
    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Use OpenAI provider to test Azure OpenAI (configured in .env)
    llm_provider = os.getenv("WECHAT_WRITER_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai"

    config = Config(
        notebook_id=os.getenv("NOTEBOOK_ID", "test_notebook"),
        notebook_url=os.getenv("NOTEBOOK_URL", "https://example.com"),
        retry_count=3,
        retry_delay_sec=2.0,
        timeout_sec=30.0,
        log_level="INFO",
        notebooklm_skill_dir="notebooklm_skill",
        llm_provider=llm_provider,
    )
    print(f"\nConfiguration:")
    print(f"  Provider: {config.llm_provider}")

    # Show backend details
    if llm_provider == "openai":
        openai_base = os.getenv("WECHAT_WRITER_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        openai_model = os.getenv("WECHAT_WRITER_OPENAI_MODEL") or os.getenv("OPENAI_MODEL")
        print(f"  Base URL: {openai_base[:50]}..." if openai_base and len(openai_base) > 50 else f"  Base URL: {openai_base}")
        print(f"  Model: {openai_model}")
        if openai_base and "/openai/responses" in openai_base:
            print(f"  Mode: Azure Responses API")
    else:
        print(f"  Mode: Anthropic API")

    # Create temp directory for outputs
    tmp_dir = Path("outputs") / f"phase1_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Output dir: {tmp_dir}")

    results = []

    # Run tests
    try:
        results.append(("State Operations", test_state_operations()))
        results.append(("Router XML Parsing", test_router_xml_parsing()))
        results.append(("Router State Transitions", test_router_state_transitions()))
        results.append(("Tracer Operations", test_tracer_operations(tmp_dir)))
        results.append(("Real LLM XML Parsing", test_real_llm_xml_parsing(config)))
        results.append(("Workflow Simulation", test_workflow_simulation(config, tmp_dir)))

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

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 All Phase 1 infrastructure tests passed!")
        print(f"\nTest outputs saved to: {tmp_dir}")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
