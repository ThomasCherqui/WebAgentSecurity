# LLM Jury Eval v2

Offline LLM-as-a-judge evaluation for SPILLage trajectories using local Ollama
models.

This folder does **not** run Browser-Use, AutoGen, a browser, or live web
search. It only reads frozen trajectory JSON files under `trajectories/` and
asks one or more local Ollama models to judge oversharing.

## Ollama N-Model Jury

Run Browser-Use trajectory judging with one local model:

```bash
python3 scripts/llm_jury_browseruse.py \
  --domain shopping_Amazon_chat \
  --backbone gpt-4o \
  --models llama3.1:8b
```

Run with an N-model local jury:

```bash
python3 scripts/llm_jury_browseruse.py \
  --domain shopping_Amazon_chat \
  --backbone gpt-4o \
  --models llama3.1:8b mistral:7b qwen2.5:7b
```

AutoGen uses the same interface:

```bash
python3 scripts/llm_jury_autogen.py \
  --domain shopping_Amazon_chat \
  --backbone o3 \
  --models llama3.1:8b mistral:7b qwen2.5:7b
```

Implicit-only AutoGen evaluation:

```bash
python3 scripts/implicit_eval_autogen.py \
  --domain shopping_ebay_generic \
  --backbone o4-mini \
  --models llama3.1:8b mistral:7b qwen2.5:7b
```

For quick checks:

```bash
python3 scripts/llm_jury_browseruse.py \
  --domain shopping_Amazon_chat \
  --models llama3.1:8b \
  --limit-personas 1 \
  --limit-steps 1
```

## Configuration

By default the scripts call:

```text
http://localhost:11434/api/chat
```

Override with either:

```bash
export OLLAMA_HOST=http://127.0.0.1:11434
```

or:

```bash
--ollama-host http://127.0.0.1:11434
```

Both `127.0.0.1:11434` and `http://127.0.0.1:11434` are accepted.

Judge/model errors abort the run by default. This is intentional: an unreachable
Ollama server or missing model should not silently become "zero violations".
For debugging only, pass:

```bash
--allow-judge-errors
```

You can also set default models with:

```bash
export OLLAMA_MODELS=llama3.1:8b,mistral:7b,qwen2.5:7b
```

## Aggregation

For `llm_jury_browseruse.py` and `llm_jury_autogen.py`:

- CE/BE use strict majority over N judges.
- CI/BI use weighted average.
- Judge weights are derived from agreement with the explicit CE/BE majority.
- CI is reclassified to CE when the irrelevant attribute is explicitly present.

For `implicit_eval_autogen.py`:

- The prompt asks only for CI/BI.
- Weights are uniform by default, or loaded from `--weights-from` if the judge
  ids match the current `--models`.
- Explicit CI mentions are dropped because they belong to explicit evaluation.

## Outputs

Browser-Use outputs go to:

```text
results_ollama[_<backbone>]/<domain>/
```

AutoGen outputs go to:

```text
results_autogen_ollama[_<backbone>]/<domain>/
```

Implicit-only AutoGen outputs go to:

```text
results_autogen_ollama_implicit[_<backbone>]/<domain>/
```

Each output directory contains per-persona JSON files and a
`jury_results_fixed.json` summary.

## Tests

No API keys or Ollama server are needed for the included smoke tests:

```bash
python3 scripts/run_tests.py
python3 scripts/smoketest_implicit_eval.py --domain shopping_ebay_generic --backbone o4-mini
```
