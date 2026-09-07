# Data organisation

## Inputs

- `input/tasks/`: persona-based web tasks and relevant/irrelevant attributes.
- `input/trajectories/`: parsed Browser-Use and AutoGen trajectories.
- `input/synthetic/`: synthetic evaluation set.
- `input/gold/gold.csv`: corrected step-level reference annotations used for evaluation.

Task files associate each persona with a goal and information classified as relevant or irrelevant. Trajectory files contain parsed actions and reasoning context evaluated at each browser step. The synthetic directory contains independent JSONL examples with explicit expected labels.

`gold.csv` is the canonical copy of the corrected annotations.

## Outputs

- `output/dummy_judges/`: single-judge predictions.
- `output/prompt_judges/`: predictions for each prompt and model.
- `output/aggregation/`: majority, hybrid, and council predictions.
- `output/synthetic/`: individual, aggregated, and council predictions for the synthetic benchmark.
- `output/agentDAM/`: AgentDAM predictions.
- `output/all_steps_results.csv`: consolidated trajectory and synthetic predictions, excluding AgentDAM.

Inputs should remain immutable. Pipeline runs write only under `output/`.

Do not commit credentials, cookies, or unredacted HAR captures. See `../ETHICS.md` for data-handling guidance and limitations of the reference annotations.

Most output directories follow `method / domain / prompt / model / predictions`. Per-person JSON files retain evidence and model responses for auditing, while CSV and JSONL predictions are the canonical inputs to evaluation.
