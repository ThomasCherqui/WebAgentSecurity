# llm_council

Minimal council layer over `jury_explainability_and_prompts` outputs.

Input layout expected:

```text
jury_explainability_and_prompts/results_ollama/<domain>/<prompt_slug>/<model_slug>/<Persona>.json
```

Output layout:

```text
llm_council/results/<domain>/<prompt_slug>/<council_slug>/
  <Persona>.json
  predictions.csv
  summary.json
```

Quick plumbing test without calling Ollama:

```bash
python3 spillage_framework/jury_step_by_step/llm_council/main.py \
  --domain shopping_Amazon_chat \
  --prompt-slug violations_only_fewshot \
  --candidate-models 'gemma4:31b' \
  --reviewer-models 'gemma4:31b' \
  --chairman-model 'gemma4:31b' \
  --limit-personas 1 \
  --limit-steps 1 \
  --mock
```

Real run:

```bash
python3 spillage_framework/jury_step_by_step/llm_council/main.py \
  --domain shopping_Amazon_chat \
  --prompt-slug violations_only_fewshot \
  --candidate-models 'gemma4:31b' 'llama3.3:70b' \
  --reviewer-models 'gemma4:31b' 'llama3.3:70b' \
  --chairman-model 'gemma4:31b'
```
