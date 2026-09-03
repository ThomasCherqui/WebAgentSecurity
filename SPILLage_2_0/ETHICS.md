# Ethics, data handling, and limitations

## Intended use

This repository supports academic research on unnecessary disclosure by web agents. It is intended for reproducible evaluation, error analysis, and privacy research—not for consequential decisions about individuals or covert monitoring.

## Data handling

Task and trajectory datasets contain persona attributes and browser-like interactions. Treat them as potentially sensitive research data even when personas or examples are synthetic. Do not add credentials, session cookies, real identifiers, or unredacted private browsing records.

The HAR uploader parses HAR content locally and sends only selected, reconstructed events to the configured analysis service. Obtain appropriate consent before analysing real browsing data, minimise retained fields, and verify that HAR files do not contain authentication material.

## Gold annotations and evaluation

`data/input/gold/gold.csv` is a corrected reference set, not an objective or exhaustive definition of privacy harm. Implicit content (`CI`) and implicit behaviour (`BI`) have low support and involve interpretive judgement. Accuracy can therefore overstate performance; report per-label precision, recall, F1, coverage, and qualitative errors together.

LLM judges may be sensitive to prompt wording, model version, provider behaviour, and nondeterminism. Saved predictions document the evaluated runs, but future reruns may differ. Human review remains necessary for ambiguous disclosures.

## External components

AgentDAM-derived code retains its original attribution and non-commercial licensing constraints. Users must review the terms of external models, providers, datasets, and agent frameworks before redistribution or commercial use.

