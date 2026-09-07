# Pipeline steps

Run the commands below from the repository root. Ollama must be available for model-based stages.

The stages are independent: predictions can be inspected before aggregation, and evaluations can be rerun from saved outputs. Use `--limit-personas` and `--limit-steps` for small checks before a complete run.

## Convenience runners

The shell runners use Gemma, GPT-OSS, and Nemotron by default. Additional model arguments override this list:

```bash
./steps/run_dummy_judges.sh shopping_Amazon_chat data/input/trajectories/browseruse_gpt4o_parsed
./steps/run_prompt_experiment.sh shopping_Amazon_chat data/input/trajectories/browseruse_gpt4o_parsed comparative_counterexamples_fewshot.md
./steps/run_aggregation.sh shopping_Amazon_chat data/input/trajectories/browseruse_gpt4o_parsed comparative_counterexamples_fewshot.md
./steps/run_council.sh shopping_Amazon_chat comparative_counterexamples_fewshot
```

The sections below show the corresponding individual commands.

## Individual judge

```bash
python3 steps/dummy_judges/run.py \
  --domain shopping_Amazon_chat \
  --trajectories-dir data/input/trajectories/browseruse_gpt4o_parsed \
  --tasks-dir data/input/tasks/less_sensitive \
  --model gemma4:31b
```

The baseline applies one model and the fixed `violations_only_fewshot` prompt to every step. Outputs are written under `data/output/dummy_judges/<domain>/<model>/`.

## Prompt experiment

```bash
python3 steps/prompt_judges/run.py \
  --domain shopping_Amazon_chat \
  --trajectories-dir data/input/trajectories/browseruse_gpt4o_parsed \
  --tasks-dir data/input/tasks/less_sensitive \
  --model gemma4:31b-cloud \
  --prompt-template comparative_counterexamples_fewshot.md
```

Templates live in `prompt_judges/prompts/`; results are separated by domain, prompt, and model. Add `--resume-existing` to continue an interrupted run.

## Majority and hybrid aggregation

First generate the raw votes, then aggregate them:

```bash
python3 steps/aggregation/generate_votes.py \
  --domain shopping_Amazon_chat \
  --trajectories-dir data/input/trajectories/browseruse_gpt4o_parsed \
  --tasks-dir data/input/tasks/less_sensitive \
  --models gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud

python3 steps/aggregation/run.py \
  --raw-run data/output/aggregation/raw_votes/shopping_Amazon_chat/balanced_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud \
  --method all
```

`majority` uses categorical voting. `hybrid` uses majority voting for explicit labels and reliability-weighted aggregation for implicit labels. `--method all` produces both.

## LLM councils

The standard and agentic councils are available under `aggregation/llm_council/` and `aggregation/llm_council_agentique/`. Both consume outputs produced by `prompt_judges`:

```bash
python3 steps/aggregation/llm_council/main.py \
  --domain shopping_Amazon_chat \
  --prompt-slug comparative_counterexamples_fewshot \
  --candidate-models gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud
```

The standard council ranks anonymised candidate verdicts before chairman arbitration. The agentic variant separates content analysis, behaviour analysis, verification, and arbitration. Use `--mock` to validate paths without model calls.

## Synthetic benchmark

```bash
python3 steps/synthetic/run.py --stage all
```

The default input is `data/input/synthetic/spillage_eval_set.jsonl`. Stages may be run separately with `--stage gemma`, `gpt-oss`, `nemotron`, `aggregate`, `council`, or `evaluate`; the last option makes no model calls.

## AgentDAM

```bash
pip install -r steps/agentdam/requirements.txt
python3 steps/agentdam/run.py
```

AgentDAM produces a binary leakage score rather than separate CE/CI/BE/BI labels. Its comparison with the council is handled by `evaluation/compare_agentdam.py`.

Shared Ollama utilities live in `steps/common/ollama_jury_common.py`.
