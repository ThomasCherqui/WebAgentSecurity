from __future__ import annotations

import json
import string
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from clients.ollama_client import safe_ollama_chat
from config import PROMPTS_DIR
from schemas import cats_from_violations, normalize_violations, parse_json


def load_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def render(template: str, values: Dict[str, Any]) -> str:
    text = template
    for key, value in values.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            rendered = str(value or "")
        text = text.replace("{{" + key + "}}", rendered)
    return text


def json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def compact_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "cats": candidate.get("cats", {}),
        "violations": normalize_violations(candidate.get("violations", [])),
        "no_violation_reason": str(candidate.get("no_violation_reason") or ""),
    }


def label_candidates(candidates: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    labels = list(string.ascii_uppercase)
    if len(candidates) > len(labels):
        raise ValueError("Too many candidate models for A-Z labels")

    label_map: Dict[str, str] = {}
    labelled: Dict[str, Dict[str, Any]] = {}
    for label, (model, candidate) in zip(labels, candidates.items()):
        label_map[label] = model
        labelled[label] = compact_candidate(candidate)
    return label_map, labelled


def prompt_context(record: Dict[str, Any], labelled: Dict[str, Dict[str, Any]], extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    values = {
        "task_goal": record.get("task_goal", ""),
        "relevant_attributes": record.get("relevant_attributes", []),
        "irrelevant_attributes": record.get("irrelevant_attributes", []),
        "trajectory_step": record.get("trajectory_step", ""),
        "candidates": labelled,
    }
    if extra:
        values.update(extra)
    return values


def normalize_review(raw_response: str, valid_labels: List[str]) -> Dict[str, Any]:
    parsed = parse_json(raw_response)
    choice = str(parsed.get("choice") or "").strip().upper()
    if choice not in valid_labels:
        choice = valid_labels[0] if valid_labels else ""

    ranked = parsed.get("ranked", [])
    if not isinstance(ranked, list):
        ranked = []
    ranked = [str(label).strip().upper() for label in ranked if str(label).strip().upper() in valid_labels]
    for label in valid_labels:
        if label not in ranked:
            ranked.append(label)

    return {
        "choice": choice,
        "ranked": ranked,
        "reason": str(parsed.get("reason") or ""),
        "candidate_notes": parsed.get("candidate_notes") if isinstance(parsed.get("candidate_notes"), dict) else {},
        "response": raw_response,
    }


def choose_label_from_reviews(reviews: List[Dict[str, Any]], valid_labels: List[str]) -> str:
    if not valid_labels:
        return ""
    counts = Counter(review.get("choice") for review in reviews if review.get("choice") in valid_labels)
    if not counts:
        return valid_labels[0]
    top_count = max(counts.values())
    tied = {label for label, count in counts.items() if count == top_count}
    for label in valid_labels:
        if label in tied:
            return label
    return valid_labels[0]


def final_from_candidate(label: str, labelled: Dict[str, Dict[str, Any]], summary: str) -> Dict[str, Any]:
    selected = labelled.get(label, {})
    violations = normalize_violations(selected.get("violations", []))
    return {
        "violations": violations,
        "cats": cats_from_violations(violations),
        "no_violation_reason": str(selected.get("no_violation_reason") or ""),
        "decision_summary": summary,
    }


def normalize_chairman(raw_response: str) -> Dict[str, Any]:
    parsed = parse_json(raw_response)
    violations = normalize_violations(parsed.get("violations", []))
    return {
        "violations": violations,
        "cats": cats_from_violations(violations),
        "no_violation_reason": str(parsed.get("no_violation_reason") or ""),
        "decision_summary": str(parsed.get("decision_summary") or ""),
        "selected_candidate": str(parsed.get("selected_candidate") or ""),
        "reviewer_signal": str(parsed.get("reviewer_signal") or ""),
    }


def run_step(
    record: Dict[str, Any],
    reviewer_models: List[str],
    chairman_model: str,
    host: str | None = None,
    allow_errors: bool = False,
    mock: bool = False,
) -> Dict[str, Any]:
    label_map, labelled = label_candidates(record.get("candidates", {}))
    valid_labels = list(labelled.keys())
    reviews: List[Dict[str, Any]] = []

    review_template = load_template("review_verdict.md")
    review_prompt = render(review_template, prompt_context(record, labelled))

    for reviewer_model in reviewer_models:
        if mock:
            raw_response = json.dumps({
                "choice": valid_labels[0] if valid_labels else "",
                "ranked": valid_labels,
                "reason": "mock review",
            })
        else:
            raw_response = safe_ollama_chat(review_prompt, reviewer_model, host=host, allow_errors=allow_errors)
        review = normalize_review(raw_response, valid_labels)
        review["reviewer_model"] = reviewer_model
        reviews.append(review)

    chosen_label = choose_label_from_reviews(reviews, valid_labels)

    if mock:
        final_verdict = final_from_candidate(chosen_label, labelled, "mock chairman selected the top reviewed candidate")
        chairman_response = json.dumps(final_verdict, ensure_ascii=False)
    else:
        chairman_template = load_template("chairman_verdict.md")
        chairman_prompt = render(chairman_template, prompt_context(record, labelled, {"reviews": reviews}))
        chairman_response = safe_ollama_chat(chairman_prompt, chairman_model, host=host, allow_errors=allow_errors)
        final_verdict = normalize_chairman(chairman_response)

    return {
        "domain": record.get("domain", ""),
        "prompt_slug": record.get("prompt_slug", ""),
        "persona": record.get("persona", ""),
        "persona_id": record.get("persona_id", ""),
        "step": record.get("step", ""),
        "task_goal": record.get("task_goal", ""),
        "trajectory_step": record.get("trajectory_step", ""),
        "candidate_label_map": label_map,
        "candidate_verdicts": labelled,
        "reviews": reviews,
        "reviewer_models": reviewer_models,
        "chairman_model": chairman_model,
        "chairman_response": chairman_response,
        "final_verdict": final_verdict,
    }
