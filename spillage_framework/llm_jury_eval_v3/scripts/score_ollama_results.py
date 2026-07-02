#!/usr/bin/env python3
"""Shim for score_ollama_results: re-export implementation from tools/score_ollama_results.

Keeps backward-compatible imports like `from score_ollama_results import process_file`.
"""
from __future__ import annotations

import sys
import importlib
import os

THIS_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
TOOLS_DIR = os.path.join(ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

try:
    # local tools copy
    from score_ollama_results import process_file, main  # type: ignore
except Exception:
    mod = importlib.import_module("llm_jury_eval_v3.tools.score_ollama_results")
    process_file = getattr(mod, "process_file")
    main = getattr(mod, "main")

__all__ = ["process_file", "main"]

if __name__ == '__main__':
    main()
