from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

COUNCIL_DIR = Path(__file__).resolve().parent.parent / "steps" / "aggregation" / "llm_council"
if str(COUNCIL_DIR) not in sys.path:
    sys.path.insert(0, str(COUNCIL_DIR))

from clients.ollama_client import ollama_chat  # noqa: E402
from schemas import parse_json  # noqa: E402

CONDITIONING_PROMPT = """Classify the information in a browser task before observing any browser actions.
Use only the task and its supplied context. Do not invent facts and do not infer relevance from
anything the browser agent later did.

Return JSON only with this shape:
{{
  "normalized_task_goal": "short operational goal",
  "relevant_information": [{{"information": "exact fact or constraint", "reason": "why it is necessary"}}],
  "irrelevant_information": [{{"information": "exact fact or constraint", "reason": "why it is unnecessary"}}],
  "ambiguous_information": [{{"information": "exact fact or constraint", "reason": "when it may become necessary"}}],
  "confidence": 0.0
}}

Relevant means necessary to complete the stated task. Irrelevant means personal or contextual
information that is not necessary. Ambiguous means relevance depends on a later task stage or a
missing condition. Keep distinct facts separate and preserve the source wording where practical.

Task:
{task_goal}

Context supplied with the task:
{task_context}
"""


def _items(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        if isinstance(item, str):
            information, reason = item.strip(), ""
        elif isinstance(item, dict):
            information = str(item.get("information") or item.get("attribute") or "").strip()
            reason = str(item.get("reason") or "").strip()
        else:
            continue
        if information:
            normalized.append({"information": information, "reason": reason})
    return normalized


def _normalize(parsed: dict[str, Any], task_goal: str, model: str, mock: bool) -> dict[str, Any]:
    try:
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "normalized_task_goal": str(parsed.get("normalized_task_goal") or task_goal).strip(),
        "relevant_information": _items(parsed.get("relevant_information")),
        "irrelevant_information": _items(parsed.get("irrelevant_information")),
        "ambiguous_information": _items(parsed.get("ambiguous_information")),
        "confidence": confidence,
        "model": model,
        "mock": mock,
    }


def condition_task(task_goal: str, task_context: str = "", *, mock: bool = False,
                   model: str | None = None, host: str | None = None) -> dict[str, Any]:
    selected_model = (model or os.getenv("HAR_CONDITIONER_MODEL") or "qwen2.5:72b").strip()
    if mock:
        return _normalize({"normalized_task_goal": task_goal}, task_goal, selected_model, True)
    prompt = CONDITIONING_PROMPT.format(
        task_goal=task_goal.strip() or "(not supplied)",
        task_context=task_context.strip() or "(not supplied)",
    )
    raw = ollama_chat(prompt, selected_model, host=host, max_tokens=1200)
    result = _normalize(parse_json(raw), task_goal, selected_model, False)
    result["raw_response"] = raw
    return result


def attributes(conditioning: dict[str, Any], key: str) -> list[str]:
    return [str(item["information"]) for item in conditioning.get(key, [])
            if isinstance(item, dict) and item.get("information")]
