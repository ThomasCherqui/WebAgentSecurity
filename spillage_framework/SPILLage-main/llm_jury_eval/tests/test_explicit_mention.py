import runpy
import json
import os
import sys

# Import the module under test by executing the script namespace
module_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'llm_jury_browseruse.py')
namespace = runpy.run_path(module_path)

explicit_mention = namespace.get('explicit_mention')
parse_json = namespace.get('parse_json')


def test_explicit_exact():
    step = {"action": "Clicked on " , "evaluation": "User selected: John Doe, 1985", "memory_update": "", "next_goal": ""}
    irrelevant = ["John Doe"]
    assert explicit_mention(step, irrelevant) is True


def test_explicit_partial_tokens():
    step = {"action": "Typed: I live in New York City", "evaluation": "", "memory_update": "", "next_goal": ""}
    irrelevant = ["New York"]
    assert explicit_mention(step, irrelevant) is True


def test_non_mention():
    step = {"action": "Clicked on 'Stainless Steel' product", "evaluation": "", "memory_update": "", "next_goal": ""}
    irrelevant = ["John Doe"]
    assert explicit_mention(step, irrelevant) is False


def test_parse_json_with_text():
    text = 'Some leading text\n{"violations": [{"category": "direct_content"}] }\nTrailing'
    out = parse_json(text)
    assert isinstance(out, dict)
    assert out.get('violations') and out['violations'][0]['category'] == 'direct_content'
