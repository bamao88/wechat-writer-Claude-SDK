"""Tests for OutputTracer extensions for hub-spoke architecture."""
import pytest
from pathlib import Path
from src.output.tracer import OutputTracer


class TestAppendCriticResult:
    """Test append_critic_result method."""

    def test_append_critic_result_writes_to_trace(self, tmp_path):
        """append_critic_result writes critic evaluation to trace file."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        tracer.append_critic_result(
            cycle=1,
            score=8,
            passed=True,
            reason="文章质量达标，结构完整"
        )

        tracer.close()

        # Check trace file contains critic result
        trace_content = tracer.trace_path.read_text(encoding='utf-8')
        assert "Critic Result" in trace_content
        assert "Cycle 1" in trace_content
        assert "评分: 8" in trace_content or "8/10" in trace_content
        assert "通过" in trace_content or "PASS" in trace_content

    def test_append_critic_result_formats_as_table(self, tmp_path):
        """append_critic_result formats output as a table."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        tracer.append_critic_result(
            cycle=1,
            score=6,
            passed=False,
            reason="字数不足"
        )

        trace_content = tracer.trace_path.read_text(encoding='utf-8')
        # Check for table-like structure
        assert "|" in trace_content  # Table delimiter
        assert "字数不足" in trace_content

    def test_append_critic_result_multiple_cycles(self, tmp_path):
        """append_critic_result handles multiple cycles."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        tracer.append_critic_result(1, 5, False, "第一轮：结构问题")
        tracer.append_critic_result(2, 7, False, "第二轮：字数不够")
        tracer.append_critic_result(3, 9, True, "第三轮：通过")

        trace_content = tracer.trace_path.read_text(encoding='utf-8')
        assert "Cycle 1" in trace_content or "第1轮" in trace_content
        assert "Cycle 2" in trace_content or "第2轮" in trace_content
        assert "Cycle 3" in trace_content or "第3轮" in trace_content

    def test_append_critic_result_with_long_reason(self, tmp_path):
        """append_critic_result handles long reasons."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        long_reason = "这是一个非常长的原因" * 50
        tracer.append_critic_result(1, 5, False, long_reason)

        # Should not raise error
        tracer.close()
        assert tracer.trace_path.exists()


class TestSaveArticleDegraded:
    """Test save_article with degraded flag."""

    def test_save_article_normal(self, tmp_path):
        """save_article saves article without warning when not degraded."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        content = "# 标题\n\n这是正文内容。"
        tracer.save_article(content, degraded=False)

        article_content = tracer.article_path.read_text(encoding='utf-8')
        assert article_content == content
        assert "⚠️" not in article_content
        assert "警告" not in article_content

    def test_save_article_degraded_adds_warning(self, tmp_path):
        """save_article adds warning at top when degraded=True."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        content = "# 标题\n\n这是正文内容。"
        tracer.save_article(content, degraded=True)

        article_content = tracer.article_path.read_text(encoding='utf-8')
        assert "⚠️" in article_content
        assert content in article_content
        # Warning should be at the top
        assert article_content.index("⚠️") < article_content.index("# 标题")

    def test_save_article_degraded_warning_format(self, tmp_path):
        """save_article degraded warning has correct format."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        content = "正文"
        tracer.save_article(content, degraded=True)

        article_content = tracer.article_path.read_text(encoding='utf-8')
        # Check warning contains explanation
        assert "⚠️" in article_content
        assert ("降级" in article_content or "未达标" in article_content or
                "质量检查" in article_content or "超出重写次数" in article_content)

    def test_save_article_backwards_compatible(self, tmp_path):
        """save_article without degraded parameter still works."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        content = "测试内容"
        result = tracer.save_article(content)

        assert result is None  # No error
        assert tracer.article_path.read_text(encoding='utf-8') == content

    def test_save_article_empty_content(self, tmp_path):
        """save_article handles empty content."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        tracer.save_article("", degraded=False)
        assert tracer.article_path.read_text(encoding='utf-8') == ""

        tracer.save_article("", degraded=True)
        article_content = tracer.article_path.read_text(encoding='utf-8')
        assert "⚠️" in article_content


class TestTracerIntegration:
    """Test integration of new methods with existing tracer."""

    def test_critic_results_appear_in_summary(self, tmp_path):
        """Critic results should be trackable in summary (future enhancement)."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        # Simulate a workflow with critic
        tracer.append_agent_input("Writer", "写作提示", [{"role": "user", "content": "测试"}])
        tracer.append_agent_output("第一版草稿", "Writer")
        tracer.append_critic_result(1, 6, False, "需要改进")

        tracer.close()

        # Check trace file exists and has content
        assert tracer.trace_path.exists()
        trace_content = tracer.trace_path.read_text(encoding='utf-8')
        assert len(trace_content) > 100  # Has substantial content

    def test_full_workflow_with_rewrites(self, tmp_path):
        """Test full workflow with multiple rewrite cycles."""
        tracer = OutputTracer(tmp_path)
        tracer.start()

        # First attempt
        tracer.append_agent_input("Writer", "写作", [])
        tracer.append_agent_output("草稿1", "Writer")
        tracer.append_critic_result(1, 5, False, "字数不足")

        # Second attempt
        tracer.append_agent_input("Writer", "改进写作", [])
        tracer.append_agent_output("草稿2", "Writer")
        tracer.append_critic_result(2, 7, False, "还需改进")

        # Final attempt (degraded)
        tracer.append_agent_input("Writer", "最后尝试", [])
        tracer.append_agent_output("草稿3", "Writer")
        tracer.append_critic_result(3, 6, False, "仍未达标，超出重写次数")

        tracer.save_article("草稿3的内容", degraded=True)
        tracer.close()

        # Verify both files exist
        assert tracer.trace_path.exists()
        assert tracer.article_path.exists()

        # Verify article has warning
        article_content = tracer.article_path.read_text(encoding='utf-8')
        assert "⚠️" in article_content
