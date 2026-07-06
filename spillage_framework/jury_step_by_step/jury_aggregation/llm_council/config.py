from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AGGREGATION_DIR = BASE_DIR.parent
STEP_BY_STEP_DIR = AGGREGATION_DIR.parent
SPILLAGE_ROOT = STEP_BY_STEP_DIR.parent

EXPLAINABILITY_RESULTS_ROOT = STEP_BY_STEP_DIR / "jury_explainability_and_prompts" / "results_ollama"
TASKS_DIR = SPILLAGE_ROOT / "data" / "input" / "tasks" / "less_sensitive"
RESULTS_ROOT = BASE_DIR / "results"
PROMPTS_DIR = BASE_DIR / "prompts"

DEFAULT_PROMPT_SLUG = "violations_only_fewshot"
