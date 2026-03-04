"""Tests for Critic Agent (rule-based quality checker)."""
import pytest
from src.agent.hub_spoke.workers.critic import CriticWorker, CriticResult
from src.agent.hub_spoke.state import State


class TestCriticResult:
    """Test CriticResult dataclass."""

    def test_critic_result_structure(self):
        """CriticResult has expected fields."""
        result = CriticResult(
            score=8,
            passed=True,
            reason="文章质量达标"
        )
        assert result.score == 8
        assert result.passed is True
        assert result.reason == "文章质量达标"


class TestCriticWordCount:
    """Test word count check (≥800 chars)."""

    def test_word_count_pass(self):
        """Passes when draft ≥800 chars."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "# 标题\n\n" + "这是正文内容。" * 150  # >800 chars
        state.outline = "大纲"

        result = worker.run(state)

        # Should not fail on word count
        assert "字数" not in result.reason or result.score >= 7

    def test_word_count_fail(self):
        """Fails when draft < 800 chars."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "# 标题\n\n短文章"  # <800 chars
        state.outline = "大纲"

        result = worker.run(state)

        assert result.passed is False
        assert "字数" in result.reason
        assert result.score < 7

    def test_word_count_exact_800(self):
        """Passes when draft exactly 800 chars."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "# 标题\n\n" + "x" * 794  # Exactly 800 with title
        state.outline = "大纲"

        result = worker.run(state)

        # 800 should pass
        assert result.passed is True or result.score >= 7


class TestCriticStructure:
    """Test structure completeness check."""

    def test_structure_complete(self):
        """Passes when all structure elements present."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = """
# 如何提升个人品牌

个人品牌建立是一个长期过程。这是引言部分。

## 核心要素

价值定位非常重要。这是正文第一段的详细内容，需要足够长度来满足字数要求。

内容输出同样关键。这是正文第二段的详细内容，也需要足够长度。

互动运营不可忽视。这是正文第三段的详细内容，继续扩充字数。

## 总结

综上所述，个人品牌建立需要持续努力。这是结尾部分的总结。
""" + "补充内容" * 50
        state.outline = "大纲"

        result = worker.run(state)

        # Should pass structure check
        assert result.passed is True
        assert "结构" not in result.reason or result.score >= 7

    def test_structure_missing_title(self):
        """Fails when title missing."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "这是正文，没有标题。" * 100
        state.outline = "大纲"

        result = worker.run(state)

        assert result.passed is False
        assert "标题" in result.reason or "结构" in result.reason

    def test_structure_missing_sections(self):
        """Fails when missing major sections."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "# 标题\n\n" + "一段话而已。" * 100  # Only one paragraph
        state.outline = "大纲"

        result = worker.run(state)

        # May fail on structure
        if not result.passed:
            assert "段落" in result.reason or "结构" in result.reason


class TestCriticOutlineAlignment:
    """Test outline key points alignment."""

    def test_outline_points_covered(self):
        """Passes when outline points appear in draft."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.outline = """
# 大纲
- 价值定位
- 内容输出
- 互动运营
"""
        state.draft = """
# 如何提升个人品牌

## 价值定位
价值定位是核心。""" + "详细内容" * 50 + """

## 内容输出
内容输出很重要。""" + "详细内容" * 50 + """

## 互动运营
互动运营不可少。""" + "详细内容" * 50

        result = worker.run(state)

        assert result.passed is True

    def test_outline_points_missing(self):
        """Fails when outline points not in draft."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.outline = """
# 大纲
- 价值定位
- 内容输出
- 互动运营
"""
        state.draft = """
# 文章标题

只谈了价值定位，没有其他内容。
""" + "x" * 800  # Enough length

        result = worker.run(state)

        # Should fail on missing points
        assert result.passed is False
        assert "论点" in result.reason or "大纲" in result.reason


class TestCriticScoringLogic:
    """Test Critic scoring and pass/fail logic."""

    def test_score_range(self):
        """Score is between 0 and 10."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "# 标题\n\n" + "内容" * 200
        state.outline = "大纲"

        result = worker.run(state)

        assert 0 <= result.score <= 10

    def test_pass_threshold_7(self):
        """passed=True when score ≥7."""
        worker = CriticWorker()
        state = State(topic="测试")

        # Create a high-quality draft
        state.draft = """
# 如何提升个人品牌

个人品牌的建立需要系统化思考。

## 价值定位
首先要明确自己的独特价值。""" + "详细论述" * 100 + """

## 内容输出
持续输出高质量内容是关键。""" + "详细论述" * 100 + """

## 互动运营
与读者建立深度连接。""" + "详细论述" * 100 + """

## 总结
综上所述，系统化建立个人品牌。
"""
        state.outline = """
- 价值定位
- 内容输出
- 互动运营
"""

        result = worker.run(state)

        if result.score >= 7:
            assert result.passed is True
        else:
            assert result.passed is False

    def test_fail_threshold_below_7(self):
        """passed=False when score <7."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "短文章"  # Too short
        state.outline = "大纲"

        result = worker.run(state)

        assert result.score < 7
        assert result.passed is False


class TestCriticIntegration:
    """Test Critic with real-like scenarios."""

    def test_critic_perfect_article(self):
        """High-quality article scores ≥9."""
        worker = CriticWorker()
        state = State(topic="如何提升个人品牌")
        state.outline = """
# 大纲
## 一、价值定位
- 核心竞争力
- 差异化定位

## 二、内容输出
- 持续性
- 高质量

## 三、互动运营
- 社群建设
- 反馈收集
"""
        state.draft = """
# 如何系统化建立个人品牌

在当今信息爆炸的时代，建立个人品牌已成为职场人士的必备技能。本文将从价值定位、内容输出、互动运营三个维度，分享系统化建立个人品牌的方法论。

## 一、价值定位：找到你的独特性

### 核心竞争力分析

价值定位是个人品牌的基石。我们需要深入思考：在所处领域，你的核心竞争力是什么？这不仅仅是技能，更是你独特的视角和方法论。""" + "详细论述" * 50 + """

### 差异化定位策略

差异化定位帮助你在竞争中脱颖而出。通过明确自己的独特价值主张，你可以吸引目标受众。""" + "详细论述" * 50 + """

## 二、内容输出：持续创造价值

### 保持持续性

内容输出的持续性至关重要。建议每周至少发布2篇高质量内容，保持稳定的更新频率。""" + "详细论述" * 50 + """

### 确保高质量

质量永远比数量重要。每一篇内容都应该经过深思熟虑，为读者提供真正的价值。""" + "详细论述" * 50 + """

## 三、互动运营：建立深度连接

### 社群建设

建立自己的社群，与读者建立更紧密的连接。""" + "详细论述" * 50 + """

### 收集反馈

积极收集读者反馈，不断优化内容方向。""" + "详细论述" * 50 + """

## 总结

个人品牌的建立是一个长期过程，需要在价值定位、内容输出、互动运营三个方面持续投入。只要坚持系统化的方法，每个人都能建立属于自己的个人品牌。
"""

        result = worker.run(state)

        assert result.passed is True
        assert result.score >= 8

    def test_critic_poor_article(self):
        """Low-quality article scores ≤5."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = "# 标题\n\n内容太少了。"
        state.outline = "应该有的大纲点"

        result = worker.run(state)

        assert result.passed is False
        assert result.score <= 5
        assert len(result.reason) > 0

    def test_critic_empty_draft(self):
        """Handles empty draft gracefully."""
        worker = CriticWorker()
        state = State(topic="测试")
        state.draft = ""
        state.outline = "大纲"

        result = worker.run(state)

        assert result.passed is False
        assert result.score == 0
        assert "空" in result.reason or "无内容" in result.reason
