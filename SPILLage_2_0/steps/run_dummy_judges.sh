#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 DOMAIN TRAJECTORIES_ROOT [MODEL ...]" >&2
  exit 2
fi

domain=$1
trajectories=$2
shift 2
models=("$@")
if [[ ${#models[@]} -eq 0 ]]; then
  models=(gemma4:31b-cloud gpt-oss:20b-cloud nemotron-3-nano:30b-cloud)
fi

for model in "${models[@]}"; do
  python3 steps/dummy_judges/run.py \
    --domain "$domain" \
    --trajectories-dir "$trajectories" \
    --tasks-dir data/input/tasks/less_sensitive \
    --model "$model" \
    --resume-existing
done

