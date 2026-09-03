#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 DOMAIN PROMPT_SLUG [MODEL ...]" >&2
  exit 2
fi

domain=$1
prompt=$2
shift 2
models=("$@")
if [[ ${#models[@]} -eq 0 ]]; then
  models=(gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud)
fi

python3 steps/aggregation/llm_council/main.py \
  --domain "$domain" \
  --prompt-slug "$prompt" \
  --candidate-models "${models[@]}" \
  --resume-existing

