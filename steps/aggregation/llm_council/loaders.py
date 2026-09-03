from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from schemas import empty_counts, normalize_violations, slug


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def raw_persona_files(model_dir: Path) -> List[Path]:
    ignored = {"summary.json", "predictions.csv", "raw_judge_outputs_summary.json", "jury_results_fixed.json"}
    return sorted(path for path in model_dir.glob("*.json") if path.name not in ignored)


def step_number(step_key: str, fallback: int) -> int:
    digits = "".join(ch for ch in str(step_key) if ch.isdigit())
    return int(digits) if digits else fallback


def load_persona_tasks(tasks_dir: Path, domain: str) -> Dict[str, Dict[str, Any]]:
    path = tasks_dir / f"{domain}.json"
    if not path.exists():
        return {}
    data = load_json(path)
    lookup: Dict[str, Dict[str, Any]] = {}
    for persona in data.get("personas", []):
        pid = persona.get("id")
        name = persona.get("name")
        if pid is not None:
            lookup[str(pid)] = persona
        if name:
            lookup[str(name)] = persona
    return lookup


def candidate_from_step(model: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
    violations = normalize_violations(step_data.get("violations", []))
    return {
        "model": model,
        "cats": {cat: int((step_data.get("cats") or empty_counts()).get(cat, 0) or 0) for cat in empty_counts()},
        "violations": violations,
        "no_violation_reason": str(step_data.get("no_violation_reason") or ""),
        "response": str(step_data.get("response") or ""),
    }


def load_council_inputs(
    domain: str,
    prompt_slug: str,
    candidate_models: List[str],
    results_root: Path,
    tasks_dir: Path,
    limit_personas: int = 0,
    limit_steps: int = 0,
) -> List[Dict[str, Any]]:
    if not candidate_models:
        raise SystemExit("At least one candidate model is required")

    model_dirs = {model: results_root / domain / prompt_slug / slug(model) for model in candidate_models}
    missing = [str(path) for path in model_dirs.values() if not path.is_dir()]
    if missing:
        raise SystemExit("Missing candidate output directories:\n" + "\n".join(missing))

    tasks = load_persona_tasks(tasks_dir, domain)
    first_model = candidate_models[0]
    persona_files = raw_persona_files(model_dirs[first_model])
    if limit_personas and limit_personas > 0:
        persona_files = persona_files[:limit_personas]

    records: List[Dict[str, Any]] = []
    for persona_file in persona_files:
        per_model_data = {}
        for model in candidate_models:
            path = model_dirs[model] / persona_file.name
            if not path.exists():
                raise SystemExit(f"Missing persona file for model={model}: {path}")
            per_model_data[model] = load_json(path)

        first_data = per_model_data[first_model]
        step_items = sorted(first_data.items(), key=lambda item: step_number(item[0], 10**9))
        if limit_steps and limit_steps > 0:
            step_items = step_items[:limit_steps]

        for idx, (step_key, first_step) in enumerate(step_items, start=1):
            step_num = int(first_step.get("step") or step_number(step_key, idx))
            persona = str(first_step.get("persona") or persona_file.stem)
            persona_id = str(first_step.get("persona_id") or "")
            task = tasks.get(persona_id) or tasks.get(persona) or {}
            candidates = {}
            for model in candidate_models:
                model_step = per_model_data[model].get(step_key) or per_model_data[model].get(f"Step {step_num}")
                if not isinstance(model_step, dict):
                    raise SystemExit(f"Missing step={step_key} persona={persona} model={model}")
                candidates[model] = candidate_from_step(model, model_step)

            records.append({
                "domain": domain,
                "prompt_slug": prompt_slug,
                "persona": persona,
                "persona_id": persona_id,
                "step_key": step_key,
                "step": step_num,
                "task_goal": task.get("task", ""),
                "relevant_attributes": task.get("relevant_attributes", []) or [],
                "irrelevant_attributes": task.get("irrelevant_attributes", []) or [],
                "trajectory_step": str(first_step.get("trajectory_step") or ""),
                "candidates": candidates,
            })
    return records
