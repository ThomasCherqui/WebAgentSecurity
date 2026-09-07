from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
COUNCIL_DIR = HERE.parent / "steps" / "aggregation" / "llm_council"
COMMON_DIR = HERE.parent / "steps" / "common"
COMPARATIVE_PROMPT_PATH = (
    HERE.parent
    / "steps"
    / "prompt_judges"
    / "prompts"
    / "comparative_counterexamples_fewshot.md"
)
if str(COUNCIL_DIR) not in sys.path:
    sys.path.insert(0, str(COUNCIL_DIR))
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from council import run_step  # noqa: E402
from ollama_jury_common import safe_judge_ollama  # noqa: E402
from schemas import normalize_violations, parse_json  # noqa: E402


def _comparative_prompt(
    *,
    task_goal: str,
    full_user_prompt: str,
    relevant_attributes: list[str],
    irrelevant_attributes: list[str],
    trajectory_step: str,
) -> str:
    template = COMPARATIVE_PROMPT_PATH.read_text(encoding="utf-8")
    values = {
        "task_goal": task_goal or "the user's task",
        "full_user_prompt": full_user_prompt,
        "relevant_attributes": ", ".join(relevant_attributes),
        "irrelevant_attributes": ", ".join(irrelevant_attributes),
        "trajectory_step": trajectory_step,
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value or ""))
    return template


def _candidate(prompt: str, model: str, host: str | None) -> dict[str, Any]:
    raw, cats = safe_judge_ollama(prompt, model, host=host, max_tokens=4096)
    parsed = parse_json(raw)
    violations = normalize_violations(parsed.get("violations", []))
    return {
        "violations": violations,
        "cats": cats,
        "no_violation_reason": str(parsed.get("no_violation_reason") or ""),
        "response": raw,
    }


def analyze(events: list[dict[str, Any]], task_goal: str = "", mock: bool = False,
            relevant_attributes: list[str] | None = None,
            irrelevant_attributes: list[str] | None = None,
            ambiguous_attributes: list[str] | None = None,
            full_user_prompt: str = "") -> dict[str, Any]:
    candidate_models = os.getenv("COUNCIL_CANDIDATE_MODELS", "gemma4:latest,mistral-small:latest").split(",")
    reviewer_models = os.getenv("COUNCIL_REVIEWER_MODELS", "gpt-oss:20b").split(",")
    chairman_model = os.getenv("COUNCIL_CHAIRMAN_MODEL", "gemma4:latest")
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    trajectory_parts = [
        str(event.get("trajectory") or "").strip()
        for event in events
        if isinstance(event, dict) and event.get("trajectory")
    ]
    trajectory = "\n\n".join(trajectory_parts) or json.dumps(events, ensure_ascii=False, indent=2)
    relevant_attributes = relevant_attributes or []
    irrelevant_attributes = irrelevant_attributes or []
    ambiguous_attributes = ambiguous_attributes or []
    prompt = _comparative_prompt(
        task_goal=task_goal,
        full_user_prompt=full_user_prompt,
        relevant_attributes=relevant_attributes,
        irrelevant_attributes=irrelevant_attributes,
        trajectory_step=trajectory,
    )

    if mock:
        candidates = {
            model: {"violations": [], "cats": {}, "no_violation_reason": "mock: no disclosure detected"}
            for model in candidate_models
        }
    else:
        with ThreadPoolExecutor(max_workers=len(candidate_models)) as executor:
            futures = {
                model: executor.submit(_candidate, prompt, model, host)
                for model in candidate_models
            }
            candidates = {model: futures[model].result() for model in candidate_models}

    record = {
        "domain": "live_browser",
        "prompt_slug": "comparative_counterexamples_fewshot",
        "persona": "current_user",
        "step": 1,
        "task_goal": task_goal,
        "trajectory_step": trajectory,
        "relevant_attributes": relevant_attributes,
        "irrelevant_attributes": irrelevant_attributes,
        "ambiguous_attributes": ambiguous_attributes,
        "candidates": candidates,
    }
    result = run_step(
        record,
        reviewer_models=reviewer_models,
        chairman_model=chairman_model,
        host=host,
        mock=mock,
    )
    verdict = result["final_verdict"]
    result["oversharing"] = bool(verdict.get("violations"))
    return result
