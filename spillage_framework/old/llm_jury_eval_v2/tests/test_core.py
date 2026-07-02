import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ollama_jury_common import (  # noqa: E402
    aggregate,
    compute_weights,
    extract_cats,
    make_judges,
    parse_json,
    parse_models,
)


def test_parse_json_with_model_chatter():
    parsed = parse_json('Here is the result:\n{"violations": []}\nDone.')
    assert parsed == {"violations": []}


def test_violation_counts():
    text = json.dumps({
        "violations": [
            {"category": "direct_content"},
            {"category": "indirect_behavioral"},
            {"category": "unknown"},
        ]
    })
    counts = extract_cats(text)
    assert counts == {"CE": 1, "CI": 0, "BE": 0, "BI": 1}


def test_parse_models_repeated_and_commas():
    assert parse_models(["llama3.1:8b,mistral:7b", "qwen2.5:7b"]) == [
        "llama3.1:8b",
        "mistral:7b",
        "qwen2.5:7b",
    ]


def test_n_model_aggregate_majority_and_weighted_implicit():
    judges = [j for j, _ in make_judges(["a", "b", "c"])]
    steps = [
        {
            judges[0]: {"CE": 1, "CI": 0, "BE": 0, "BI": 0},
            judges[1]: {"CE": 1, "CI": 1, "BE": 0, "BI": 0},
            judges[2]: {"CE": 0, "CI": 1, "BE": 0, "BI": 0},
        }
    ]
    weights = compute_weights(steps, judges)
    verdict = aggregate([steps[0][j] for j in judges], weights, judges)
    assert verdict["CE"] == 1
    assert verdict["BE"] == 0
    assert verdict["CI"] in (0, 1)
