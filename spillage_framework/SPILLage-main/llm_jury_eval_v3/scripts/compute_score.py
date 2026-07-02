#!/usr/bin/env python3
"""Shim module to re-export compute_score from llm_jury_eval_v3.tools.compute_score.

This keeps backward compatibility for scripts that import `from compute_score import score_event`.
"""
from __future__ import annotations

import sys
import importlib
import os

# Ensure the tools package is importable when running from the repository root.
THIS_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
TOOLS_DIR = os.path.join(ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

# import the implementation from the tools package
try:
    from compute_score import score_event, aggregate_scores, CATEGORY_VALUE, SENSITIVITY_VALUE, NECESSITY_PENALTY  # type: ignore
except Exception:
    # fallback: try package style import if scripts are executed as package
    mod = importlib.import_module("llm_jury_eval_v3.tools.compute_score")
    score_event = getattr(mod, "score_event")
    aggregate_scores = getattr(mod, "aggregate_scores")
    CATEGORY_VALUE = getattr(mod, "CATEGORY_VALUE")
    SENSITIVITY_VALUE = getattr(mod, "SENSITIVITY_VALUE")
    NECESSITY_PENALTY = getattr(mod, "NECESSITY_PENALTY")

__all__ = [
    "score_event",
    "aggregate_scores",
    "CATEGORY_VALUE",
    "SENSITIVITY_VALUE",
    "NECESSITY_PENALTY",
]
