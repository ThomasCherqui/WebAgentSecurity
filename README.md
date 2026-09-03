# SPILLage: evaluation of privacy oversharing by web agents

This repository contains the experimental material for a master thesis on evaluating privacy oversharing by web agents. It builds on the original **SPILLage** work:

- [SPILLage paper (arXiv)](https://arxiv.org/pdf/2602.13516)
- [Original SPILLage repository](https://github.com/jrohsc/SPILLage)

SPILLage studies whether browsing agents disclose personal information that is irrelevant to the task they are completing. This repository focuses on the evaluation side of that problem: step-level judging, prompt variants, aggregation strategies, LLM councils, comparison with AgentDAM, and evaluation on recorded trajectories and controlled synthetic examples.

## What is evaluated?

Each trajectory step is assigned four possible oversharing labels:

- `CE` — explicit content disclosure;
- `CI` — implicit content disclosure;
- `BE` — explicit behavioural disclosure;
- `BI` — implicit behavioural disclosure.

The main experiments compare individual LLM judges, alternative prompting strategies, majority and reliability-weighted aggregation, and an LLM council. AgentDAM is included as a separate binary baseline because it predicts whether oversharing occurred rather than producing all four labels.

Two evaluation sources are provided:

- recorded Browser-Use and AutoGen trajectories, evaluated against corrected step-level gold annotations;
- a synthetic benchmark containing controlled positive, negative, and counterexample cases.

## Repository structure

```text
data/           inputs, gold annotations, saved predictions, and consolidated outputs
steps/          runnable judges, prompt experiments, aggregation, councils, and AgentDAM
evaluation/     offline evaluation scripts and generated metrics
har_uploader/   standalone interface for analysing selected HAR-derived browser events
```

The main pipeline is:

```text
tasks + trajectories (or synthetic examples)
    -> individual judges
    -> majority / hybrid aggregation / LLM council
    -> evaluation against data/input/gold/gold.csv
```

Inputs and generated outputs are deliberately separated. Saved predictions make it possible to reproduce the reported metrics without repeating model calls.

## Quick start

Install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Recompute every metric from the saved predictions without calling a model:

```bash
./evaluation/run_all.sh
```

Model-based stages use an Ollama-compatible endpoint. Convenience runners and individual commands are documented in [`steps/README.md`](steps/README.md). Data formats and outputs are described in [`data/README.md`](data/README.md), and metric files in [`evaluation/README.md`](evaluation/README.md).

## Results

Detailed reports are stored under `evaluation/results/`. The main consolidated files are:

- `data/output/all_steps_results.csv` — saved trajectory and synthetic predictions, excluding AgentDAM;
- `evaluation/all_step_performance.csv` — gold and predicted labels for every evaluated step;
- `evaluation/results/synthetic/` — synthetic benchmark metrics;
- `evaluation/results/agentdam_vs_llm_council/` — the separate binary comparison.

Because implicit labels are comparatively rare, accuracy should not be interpreted alone. The reports also provide per-label precision, recall, F1, exact label-set accuracy, and prediction coverage.

## Citation, licence, and responsible use

Please cite the original SPILLage paper and the associated master thesis when using this repository. Machine-readable citation metadata is provided in [`CITATION.cff`](CITATION.cff).

The repository is distributed under CC BY-NC 4.0; see [`LICENSE`](LICENSE). Guidance on sensitive data, HAR files, gold-annotation limitations, and appropriate use is available in [`ETHICS.md`](ETHICS.md).
