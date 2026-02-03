"""Tests for output module (Phase 3)."""
import pytest
from pathlib import Path

from src.output import create_output_dir, topic_to_slug, OutputTracer


class TestTopicToSlug:
    def test_chinese_to_pinyin(self):
        slug = topic_to_slug("产品经理")
        assert slug
        assert " " not in slug
        assert slug.islower() or not slug  # or empty

    def test_ascii_lowercase(self):
        slug = topic_to_slug("AI product")
        assert "ai" in slug or "product" in slug


class TestCreateOutputDir:
    def test_creates_under_base(self, tmp_path):
        run_dir = create_output_dir("测试", base_dir=str(tmp_path))
        assert run_dir.is_dir()
        assert run_dir.parent == tmp_path
        assert "测试" in run_dir.name or "ce-shi" in run_dir.name or "topic" in run_dir.name

    def test_unique_per_call(self, tmp_path):
        d1 = create_output_dir("选题", base_dir=str(tmp_path))
        d2 = create_output_dir("选题", base_dir=str(tmp_path))
        assert d1 != d2


class TestOutputTracer:
    def test_start_and_append_agent_output(self, tmp_path):
        tracer = OutputTracer(tmp_path)
        tracer.start()
        tracer.append_agent_output("第一段输出")
        tracer.close()
        trace = (tmp_path / "thought_trace.md").read_text(encoding="utf-8")
        assert "Agent Output" in trace
        assert "第一段输出" in trace

    def test_append_tool_call_and_result(self, tmp_path):
        tracer = OutputTracer(tmp_path)
        tracer.start()
        tracer.append_tool_call("search_notebooklm", {"query": "测试"})
        tracer.append_tool_result("检索结果内容")
        tracer.close()
        trace = (tmp_path / "thought_trace.md").read_text(encoding="utf-8")
        assert "Tool Call" in trace
        assert "Tool Result" in trace
        assert "search_notebooklm" in trace

    def test_save_article(self, tmp_path):
        tracer = OutputTracer(tmp_path)
        err = tracer.save_article("# 标题\n\n正文内容")
        assert err is None
        article = (tmp_path / "article.md").read_text(encoding="utf-8")
        assert "标题" in article
        assert "正文内容" in article
