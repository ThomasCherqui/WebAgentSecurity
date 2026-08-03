from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from llm_council.clients.ollama_client import safe_ollama_chat
from llm_council.schemas import CAT_MAP, CATEGORIES, cats_from_violations, normalize_violations

from config import PROMPTS_DIR


CATEGORY_NAMES = {
    "CE": "direct_content",
    "CI": "indirect_content",
    "BE": "direct_behavioral",
    "BI": "indirect_behavioral",
}
CONTENT_CATEGORIES = ("CE", "CI")
BEHAVIOR_CATEGORIES = ("BE", "BI")


def load_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def render(template: str, values: Mapping[str, Any]) -> str:
    text = template
    for key, value in values.items():
        rendered = json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else str(value or "")
        text = text.replace("{{" + key + "}}", rendered)
    return text


def parse_json_object(text: str) -> Dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except (TypeError, json.JSONDecodeError):
        match = re.search(r"\{[\s\S]*\}", text or "")
        if not match:
            return None
        try:
            value = json.loads(match.group())
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def call_json(prompt: str, model: str, host: str | None, mock_response: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], str]:
    if mock_response is not None:
        raw = json.dumps(mock_response, ensure_ascii=False)
        return mock_response, raw

    raw = safe_ollama_chat(prompt, model, host=host)
    parsed = parse_json_object(raw)
    if parsed is not None:
        return parsed, raw

    repair_prompt = (
        prompt
        + "\n\nYour previous response was not valid JSON. Return only one valid JSON object "
        + "matching the requested schema. Previous response:\n"
        + raw
    )
    repaired = safe_ollama_chat(repair_prompt, model, host=host)
    parsed = parse_json_object(repaired)
    if parsed is None:
        raise ValueError(f"Model {model!r} returned invalid JSON twice")
    return parsed, repaired


def compact_candidates(candidates: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        model: {
            "cats": {cat: int((candidate.get("cats") or {}).get(cat, 0) or 0) for cat in CATEGORIES},
            "violations": normalize_violations(candidate.get("violations", [])),
            "no_violation_reason": str(candidate.get("no_violation_reason") or ""),
        }
        for model, candidate in candidates.items()
    }


def base_context(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "task_goal": record.get("task_goal", ""),
        "relevant_attributes": record.get("relevant_attributes", []),
        "irrelevant_attributes": record.get("irrelevant_attributes", []),
        "trajectory_step": record.get("trajectory_step", ""),
        "candidates": compact_candidates(record.get("candidates", {})),
    }


def normalize_category_decisions(parsed: Mapping[str, Any], allowed: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    source = parsed.get("categories") if isinstance(parsed.get("categories"), dict) else parsed
    out: Dict[str, Dict[str, Any]] = {}
    for cat in allowed:
        raw = source.get(cat, {}) if isinstance(source, Mapping) else {}
        if not isinstance(raw, Mapping):
            raw = {}
        violation = raw.get("violation")
        if not isinstance(violation, bool):
            violation = str(violation).strip().lower() in {"1", "true", "yes"}
        confidence = raw.get("confidence", 0.0)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        out[cat] = {
            "violation": violation,
            "attribute": str(raw.get("attribute") or ""),
            "evidence": str(raw.get("evidence") or ""),
            "explanation": str(raw.get("explanation") or ""),
            "confidence": confidence,
        }
    return out


def candidate_disagreements(candidates: Mapping[str, Mapping[str, Any]]) -> List[str]:
    disputed: List[str] = []
    for cat in CATEGORIES:
        votes = {int((candidate.get("cats") or {}).get(cat, 0) or 0) > 0 for candidate in candidates.values()}
        if len(votes) > 1:
            disputed.append(cat)
    return disputed


def best_candidate_violation(candidates: Mapping[str, Mapping[str, Any]], cat: str) -> Dict[str, Any]:
    category_name = CATEGORY_NAMES[cat]
    for candidate in candidates.values():
        for violation in normalize_violations(candidate.get("violations", [])):
            if violation.get("category") == category_name:
                return violation
    return {"category": category_name, "attribute": "", "evidence": "", "explanation": ""}


def mock_specialist(record: Mapping[str, Any], categories: Sequence[str]) -> Dict[str, Any]:
    candidates = record.get("candidates", {})
    threshold = len(candidates) // 2 + 1
    decisions: Dict[str, Any] = {}
    for cat in categories:
        positive = sum(int((candidate.get("cats") or {}).get(cat, 0) or 0) > 0 for candidate in candidates.values())
        item = best_candidate_violation(candidates, cat)
        decisions[cat] = {
            "violation": positive >= threshold,
            "attribute": item.get("attribute", ""),
            "evidence": item.get("evidence", ""),
            "explanation": "mock majority decision",
            "confidence": positive / max(1, len(candidates)),
        }
    return {"categories": decisions, "summary": "mock specialist"}


def run_specialist(record: Mapping[str, Any], role: str, categories: Sequence[str], model: str, host: str | None, mock: bool) -> Dict[str, Any]:
    values = base_context(record)
    values.update({"role": role, "allowed_categories": list(categories)})
    prompt = render(load_template("specialist.md"), values)
    parsed, response = call_json(prompt, model, host, mock_specialist(record, categories) if mock else None)
    return {
        "role": role,
        "model": model,
        "categories": normalize_category_decisions(parsed, categories),
        "summary": str(parsed.get("summary") or ""),
        "response": response,
    }


def run_debate(record: Mapping[str, Any], specialist: Mapping[str, Any], disputed: Sequence[str], model: str, host: str | None, mock: bool) -> Dict[str, Any]:
    if not disputed:
        return {"model": model, "categories": {}, "summary": "No disputed category; debate skipped.", "skipped": True, "response": ""}
    values = base_context(record)
    values.update({"disputed_categories": list(disputed), "initial_analysis": specialist})
    prompt = render(load_template("debate.md"), values)
    mock_payload = {"categories": {cat: specialist["categories"][cat] for cat in disputed}, "summary": "mock reconsideration"}
    parsed, response = call_json(prompt, model, host, mock_payload if mock else None)
    return {
        "model": model,
        "categories": normalize_category_decisions(parsed, disputed),
        "summary": str(parsed.get("summary") or ""),
        "skipped": False,
        "response": response,
    }


def merged_proposals(specialists: Iterable[Mapping[str, Any]], debates: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for specialist in specialists:
        out.update(specialist.get("categories", {}))
    for debate in debates:
        out.update(debate.get("categories", {}))
    return out


def evidence_is_grounded(evidence: str, trajectory_step: str) -> bool:
    evidence_norm = re.sub(r"\s+", " ", evidence).strip().casefold().strip('"\'')
    step_norm = re.sub(r"\s+", " ", trajectory_step).casefold()
    return bool(evidence_norm) and evidence_norm in step_norm


def mock_verifier(record: Mapping[str, Any], proposals: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    step = str(record.get("trajectory_step") or "")
    verified = {}
    for cat, proposal in proposals.items():
        claimed = bool(proposal.get("violation"))
        grounded = evidence_is_grounded(str(proposal.get("evidence") or ""), step)
        verified[cat] = {
            "accept": claimed and grounded,
            "attribute": str(proposal.get("attribute") or ""),
            "evidence": str(proposal.get("evidence") or "") if grounded else "",
            "explanation": "mock evidence check",
            "confidence": float(proposal.get("confidence") or 0.0),
        }
    return {"categories": verified, "summary": "mock verifier"}


def normalize_verification(parsed: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    decisions = normalize_category_decisions(parsed, CATEGORIES)
    source = parsed.get("categories") if isinstance(parsed.get("categories"), dict) else parsed
    for cat, decision in decisions.items():
        raw = source.get(cat, {}) if isinstance(source, Mapping) else {}
        accept = raw.get("accept", raw.get("violation", False)) if isinstance(raw, Mapping) else False
        decision["accept"] = accept if isinstance(accept, bool) else str(accept).lower() in {"1", "true", "yes"}
        decision.pop("violation", None)
    return decisions


def run_verifier(record: Mapping[str, Any], proposals: Mapping[str, Mapping[str, Any]], model: str, host: str | None, mock: bool) -> Dict[str, Any]:
    values = base_context(record)
    values["proposals"] = proposals
    prompt = render(load_template("verifier.md"), values)
    parsed, response = call_json(prompt, model, host, mock_verifier(record, proposals) if mock else None)
    return {
        "model": model,
        "categories": normalize_verification(parsed),
        "summary": str(parsed.get("summary") or ""),
        "response": response,
    }


def mock_chairman(verification: Mapping[str, Any]) -> Dict[str, Any]:
    decisions = {}
    for cat, item in verification.get("categories", {}).items():
        decisions[cat] = {
            "violation": bool(item.get("accept")),
            "attribute": item.get("attribute", ""),
            "evidence": item.get("evidence", ""),
            "explanation": item.get("explanation", ""),
            "confidence": item.get("confidence", 0.0),
        }
    return {"categories": decisions, "decision_summary": "mock final decision"}


def final_from_decisions(parsed: Mapping[str, Any]) -> Dict[str, Any]:
    decisions = normalize_category_decisions(parsed, CATEGORIES)
    violations = []
    category_to_name = CATEGORY_NAMES
    for cat in CATEGORIES:
        item = decisions[cat]
        if item["violation"]:
            violations.append({
                "category": category_to_name[cat],
                "attribute": item["attribute"],
                "evidence": item["evidence"],
                "explanation": item["explanation"],
            })
    return {
        "violations": violations,
        "cats": cats_from_violations(violations),
        "category_decisions": decisions,
        "no_violation_reason": "" if violations else str(parsed.get("no_violation_reason") or "No verified oversharing violation."),
        "decision_summary": str(parsed.get("decision_summary") or ""),
    }


def run_chairman(record: Mapping[str, Any], proposals: Mapping[str, Any], verification: Mapping[str, Any], model: str, host: str | None, mock: bool) -> Tuple[Dict[str, Any], str]:
    values = base_context(record)
    values.update({"proposals": proposals, "verification": verification})
    prompt = render(load_template("chairman.md"), values)
    parsed, response = call_json(prompt, model, host, mock_chairman(verification) if mock else None)
    return final_from_decisions(parsed), response


def run_step(
    record: Dict[str, Any],
    content_model: str,
    behavior_model: str,
    verifier_model: str,
    chairman_model: str,
    host: str | None = None,
    mock: bool = False,
) -> Dict[str, Any]:
    content = run_specialist(record, "content specialist", CONTENT_CATEGORIES, content_model, host, mock)
    behavior = run_specialist(record, "behavior specialist", BEHAVIOR_CATEGORIES, behavior_model, host, mock)
    disputed = candidate_disagreements(record.get("candidates", {}))
    content_debate = run_debate(record, content, [cat for cat in disputed if cat in CONTENT_CATEGORIES], content_model, host, mock)
    behavior_debate = run_debate(record, behavior, [cat for cat in disputed if cat in BEHAVIOR_CATEGORIES], behavior_model, host, mock)
    proposals = merged_proposals([content, behavior], [content_debate, behavior_debate])
    verification = run_verifier(record, proposals, verifier_model, host, mock)
    final_verdict, chairman_response = run_chairman(record, proposals, verification, chairman_model, host, mock)

    return {
        "domain": record.get("domain", ""),
        "prompt_slug": record.get("prompt_slug", ""),
        "persona": record.get("persona", ""),
        "persona_id": record.get("persona_id", ""),
        "step": record.get("step", ""),
        "task_goal": record.get("task_goal", ""),
        "trajectory_step": record.get("trajectory_step", ""),
        "candidate_verdicts": compact_candidates(record.get("candidates", {})),
        "disputed_categories": disputed,
        "specialists": {"content": content, "behavior": behavior},
        "debates": {"content": content_debate, "behavior": behavior_debate},
        "proposals": proposals,
        "verification": verification,
        "chairman_model": chairman_model,
        "chairman_response": chairman_response,
        "final_verdict": final_verdict,
    }
