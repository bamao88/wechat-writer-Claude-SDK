"""Output system: run directory, thought trace, article persistence."""
from pathlib import Path
from datetime import datetime
import secrets

from src.output.tracer import OutputTracer


def topic_to_slug(topic: str) -> str:
    """Convert topic to URL-safe slug (pinyin for Chinese, lowercase, hyphens)."""
    try:
        from pypinyin import lazy_pinyin, Style
        parts = lazy_pinyin(topic, style=Style.NORMAL)
        slug = "-".join(parts).lower()
    except Exception:
        slug = "".join(c if c.isalnum() or c.isspace() else "-" for c in topic)
        slug = "-".join(slug.split()).lower()
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
    slug = "-".join(filter(None, slug.split("-")))
    return slug[:80] or "topic"


def create_output_dir(topic: str, base_dir: str = "output") -> Path:
    """Create output run directory: base_dir/YYYY-MM-DD_HHMMSS_slug_shortid.

    Fail fast if creation fails.
    """
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H%M%S")
    slug = topic_to_slug(topic)
    short_id = secrets.token_hex(3)
    run_dir = base / f"{date}_{time}_{slug}_{short_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


__all__ = ["OutputTracer", "create_output_dir", "topic_to_slug"]
