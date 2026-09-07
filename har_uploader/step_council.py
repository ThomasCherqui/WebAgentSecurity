from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

LIVE_MONITOR_DIR = Path(__file__).resolve().parent
if str(LIVE_MONITOR_DIR) not in sys.path:
    sys.path.insert(0, str(LIVE_MONITOR_DIR))

from council_adapter import analyze
from task_conditioner import attributes


DEFAULT_COUNCIL_MODELS = [
    "gemma4:31b-cloud",
    "gpt-oss:20b-cloud",
    "nemotron-3-nano:30b-cloud",
]
DEFAULT_CHAIRMAN_MODEL = "gpt-oss:120b-cloud"


def configure_models() -> tuple[list[str], str]:
    models = [
        model.strip()
        for model in os.getenv("HAR_COUNCIL_MODELS", ",".join(DEFAULT_COUNCIL_MODELS)).split(",")
        if model.strip()
    ]
    chairman = os.getenv("HAR_CHAIRMAN_MODEL", DEFAULT_CHAIRMAN_MODEL).strip()
    os.environ["COUNCIL_CANDIDATE_MODELS"] = ",".join(models)
    os.environ["COUNCIL_REVIEWER_MODELS"] = ",".join(models)
    os.environ["COUNCIL_CHAIRMAN_MODEL"] = chairman
    return models, chairman


def compact_step_result(position: int, source: dict[str, Any], result: dict[str, Any], elapsed: float) -> dict[str, Any]:
    reviews = [
        {
            "reviewer_model": review.get("reviewer_model"),
            "choice": review.get("choice"),
            "ranked": review.get("ranked", []),
            "reason": review.get("reason", ""),
            "candidate_notes": review.get("candidate_notes", {}),
        }
        for review in result.get("reviews", [])
    ]
    return {
        "step": position,
        "prompt_slug": result.get("prompt_slug", ""),
        "timestamp": source.get("timestamp"),
        "source_model": source.get("model"),
        "message_id": source.get("message_id"),
        "trajectory": source.get("trajectory", ""),
        "candidate_label_map": result.get("candidate_label_map", {}),
        "candidate_verdicts": result.get("candidate_verdicts", {}),
        "reviews": reviews,
        "final_verdict": result.get("final_verdict", {}),
        "elapsed_seconds": round(elapsed, 2),
    }


def run_per_step(events: list[dict[str, Any]], task_goal: str, mock: bool = False,
                 conditioning: dict[str, Any] | None = None,
                 task_context: str = "") -> dict[str, Any]:
    models, chairman = configure_models()
    conditioning = conditioning or {}
    normalized_task_goal = str(conditioning.get("normalized_task_goal") or task_goal)
    full_user_prompt = "\n\n".join(
        value.strip() for value in (task_goal, task_context) if value.strip()
    )
    started = time.monotonic()
    step_results = []
    all_violations = []

    def analyze_step(position: int, event: dict[str, Any]) -> dict[str, Any]:
        step_started = time.monotonic()
        result = analyze(
            [event], normalized_task_goal, mock=mock,
            relevant_attributes=attributes(conditioning, "relevant_information"),
            irrelevant_attributes=attributes(conditioning, "irrelevant_information"),
            ambiguous_attributes=attributes(conditioning, "ambiguous_information"),
            full_user_prompt=full_user_prompt,
        )
        return compact_step_result(position, event, result, time.monotonic() - step_started)

    configured_workers = max(1, int(os.getenv("HAR_MAX_PARALLEL_STEPS", "2")))
    max_workers = min(configured_workers, len(events))
    if events:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(analyze_step, position, event): position
                for position, event in enumerate(events, start=1)
            }
            for future in as_completed(futures):
                step_results.append(future.result())

    step_results.sort(key=lambda item: item["step"])
    for compact in step_results:
        position = compact["step"]
        for violation in compact["final_verdict"].get("violations", []):
            all_violations.append({"step": position, **violation})

    violating_steps = sorted({violation["step"] for violation in all_violations})
    return {
        "oversharing": bool(all_violations),
        "summary": {
            "steps_analyzed": len(step_results),
            "violating_steps": violating_steps,
            "violation_count": len(all_violations),
        },
        "violations": all_violations,
        "step_results": step_results,
        "task_conditioning": conditioning,
        "analysis_metadata": {
            "candidate_prompt": "comparative_counterexamples_fewshot",
            "council_models": models,
            "chairman_model": chairman,
            "calls_per_step": 0 if mock else len(models) * 2 + 1,
            "ollama_calls": 0 if mock else 1 + len(step_results) * (len(models) * 2 + 1),
            "conditioner_model": conditioning.get("model", ""),
            "parallel_steps": max_workers if events else 0,
            "peak_parallel_ollama_calls": (max_workers * len(models)) if events and not mock else 0,
            "elapsed_seconds": round(time.monotonic() - started, 2),
        },
    }
