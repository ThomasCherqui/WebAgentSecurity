# SPILLage evaluation repository

This repository contains the evaluation material used for a master's thesis on privacy oversharing by web agents.

The central question is whether an agent reveals personal information that is not necessary to complete the user's task. Predictions are made at the trajectory-step level using four labels:

- `CE`: explicit content disclosure;
- `CI`: implicit content disclosure;
- `BE`: explicit behavioural disclosure;
- `BI`: implicit behavioural disclosure.

## Structure

- `data/`: tasks, trajectories, synthetic benchmark, gold annotations, and model outputs.
- `steps/`: runnable judges, prompt experiments, aggregation methods, councils, and AgentDAM.
- `evaluation/`: scripts and metrics comparing predictions with the gold annotations.
- `har_uploader/`: standalone interface for analysing HAR-derived browser events with the LLM council.

The evaluation pipeline is:

```text
tasks + trajectories (or synthetic examples)
    -> individual judges
    -> majority / hybrid / LLM council
    -> evaluation against data/input/gold/gold.csv
```

Two complementary evaluation sources are included. The trajectory dataset measures performance on recorded Browser-Use and AutoGen interactions, while Synthetic2 provides controlled positive, negative, and counterexample cases. AgentDAM is retained as a separate binary baseline because it does not produce the four labels above.


## Reproducibility

Inputs are kept separate from generated outputs. Model calls write under `data/output/`; evaluation scripts compare these predictions with immutable gold annotations and write reports under `evaluation/results/`. Evaluation is offline and can be rerun without calling a model.

## Quick start

From this directory, use the runners in `steps/` for model stages. Rebuild every saved-output evaluation without model calls with:

```bash
./evaluation/run_all.sh
```

Install the pinned dependencies before running model or HAR stages:

```bash
python3 -m pip install -r requirements.txt
```

## Citation and responsible use

Citation metadata is provided in `CITATION.cff`. The repository uses CC BY-NC 4.0; see `LICENSE`. Data-handling guidance and evaluation limitations are documented in `ETHICS.md`.

See the README in each directory for commands and file details.

