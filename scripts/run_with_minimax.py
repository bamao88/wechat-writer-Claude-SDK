#!/usr/bin/env python3
"""Run main.py with MiniMax as LLM (uses MINIMAX_* from .env, switches Anthropic backend to MiniMax)."""
import os
import sys

# Load .env first
from dotenv import load_dotenv
load_dotenv()

# Point Anthropic backend to MiniMax (Anthropic-compatible endpoint + Bearer auth)
base = os.getenv("MINIMAX_ANTHROPIC_BASE_URL") or "https://api.minimaxi.com/anthropic"
key = os.getenv("MINIMAX_API_KEY") or ""
model = os.getenv("MINIMAX_MODEL") or "MiniMax-M2.1"
os.environ["WECHAT_WRITER_ANTHROPIC_BASE_URL"] = base
os.environ["WECHAT_WRITER_ANTHROPIC_API_KEY"] = key
os.environ["WECHAT_WRITER_ANTHROPIC_MODEL"] = model

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Run main (same argv: script name + topic)
from main import main
sys.exit(main())
