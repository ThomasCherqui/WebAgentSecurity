#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 DOMAIN TRAJECTORIES_ROOT PROMPT_FILE [MODEL ...]" >&2
  exit 2
fi

domain=$1
trajectories=$2
prompt=$3
shift 3
models=("$@")
if [[ ${#models[@]} -eq 0 ]]; then
  models=(gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud)
fi

python3 steps/aggregation/generate_votes.py \
  --domain "$domain" \
  --trajectories-dir "$trajectories" \
  --tasks-dir data/input/tasks/less_sensitive \
  --models "${models[@]}" \
  --prompt-template "$prompt" \
  --reuse-existing-single-runs

prompt_slug=${prompt##*/}
prompt_slug=${prompt_slug%.md}
models_slug=""
for model in "${models[@]}"; do
  safe=$(printf '%s' "$model" | sed -E 's/[^A-Za-z0-9_.-]+/_/g; s/^_+|_+$//g')
  [[ -n "$models_slug" ]] && models_slug+="__"
  models_slug+="$safe"
done

python3 steps/aggregation/run.py \
  --raw-run "data/output/aggregation/raw_votes/$domain/$prompt_slug/$models_slug" \
  --method all

