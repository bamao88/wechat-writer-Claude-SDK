#!/usr/bin/env python3
"""Minimal test for Anthropic API: load .env and call messages.create."""
import os
import sys

# Load project root into path and load .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

# Prefer project-prefixed (so .env overrides shell proxy URL)
api_key = (os.getenv("WECHAT_WRITER_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
base_url = (os.getenv("WECHAT_WRITER_ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL") or "").strip().rstrip("/")
model = os.getenv("WECHAT_WRITER_ANTHROPIC_MODEL") or os.getenv("ANTHROPIC_MODEL") or "claude-haiku-4-5-20251001"

print("API_KEY:", f"{api_key[:15]}...{api_key[-4:]}" if len(api_key) > 20 else "(empty or short)")
print("BASE_URL:", base_url or "(empty, use default)")
print("MODEL:", model)
print()

if not api_key:
    print("ERROR: ANTHROPIC_API_KEY is empty")
    sys.exit(1)

from anthropic import Anthropic

client = Anthropic(api_key=api_key, base_url=base_url or None)

try:
    r = client.messages.create(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": "Say OK in one word."}],
    )
    text = r.content[0].text if r.content else ""
    print("SUCCESS. Response:", text[:200])
except Exception as e:
    print("FAILED:", type(e).__name__, str(e))
    sys.exit(1)
