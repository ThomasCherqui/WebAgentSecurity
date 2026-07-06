from __future__ import annotations

import json
import re
from typing import Any, Dict, List

CATEGORIES = ("CE", "CI", "BE", "BI")
CAT_MAP = {
    "direct_content": "CE",
    "indirect_content": "CI",
    "direct_behavioral": "BE",
    "indirect_behavioral": "BI",
}


def empty_counts() -> Dict[str, int]:
    return {cat: 0 for cat in CATEGORIES}


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("_") or "run"


def csv_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_json(text: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(text or "")
        return parsed if isinstance(parsed, dict) else {"violations": []}
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text or "")
        if match:
            try:
                parsed = json.loads(match.group())
                return parsed if isinstance(parsed, dict) else {"violations": []}
            except Exception:
                pass
    return {"violations": []}


def normalize_violation(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {"category": "", "attribute": "", "evidence": "", "explanation": ""}
    return {
        "category": str(value.get("category") or ""),
        "attribute": str(value.get("attribute") or ""),
        "evidence": str(value.get("evidence") or ""),
        "explanation": str(value.get("explanation") or ""),
    }


def normalize_violations(values: Any) -> List[Dict[str, str]]:
    if not isinstance(values, list):
        return []
    return [normalize_violation(value) for value in values]


def cats_from_violations(violations: List[Dict[str, str]]) -> Dict[str, int]:
    cats = empty_counts()
    for violation in violations:
        cat = CAT_MAP.get(violation.get("category", ""))
        if cat:
            cats[cat] += 1
    return cats
