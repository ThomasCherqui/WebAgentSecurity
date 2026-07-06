#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/jury_step_by_step/jury_baseline_dummy_one_judge/main.py"
TRAJ_DIR="$ROOT/data/input/trajectories/browseruse_gpt4o_parsed"
TASKS_DIR="$ROOT/data/input/tasks/less_sensitive"
LOG_DIR="$ROOT/jury_step_by_step/jury_baseline_dummy_one_judge/logs"
mkdir -p "$LOG_DIR"

DOMAINS=(
  "shopping_Amazon_chat"
  "shopping_ebay_chat"
)

# Override from CLI/env, e.g.:
#   MODELS="gemma4:31b llama3.1:8b" ./run_dummy_batch.sh
# Runs are sequential by default to avoid overloading GPU/VRAM.
MODELS=${MODELS:-"gemma4:31b"}

LIMIT_ARGS=()
if [[ "${LIMIT_PERSONAS:-}" != "" ]]; then
  LIMIT_ARGS+=(--limit-personas "$LIMIT_PERSONAS")
fi
if [[ "${LIMIT_STEPS:-}" != "" ]]; then
  LIMIT_ARGS+=(--limit-steps "$LIMIT_STEPS")
fi

for model in $MODELS; do
  model_slug="$(printf '%s' "$model" | sed 's/[^A-Za-z0-9_.-]/_/g; s/^_*//; s/_*$//')"
  for domain in "${DOMAINS[@]}"; do
    log="$LOG_DIR/${domain}_${model_slug}.log"
    echo "Running domain=$domain model=$model log=$log"
    if python3 -u "$APP" \
      --domain "$domain" \
      --trajectories-dir "$TRAJ_DIR" \
      --tasks-dir "$TASKS_DIR" \
      --model "$model" \
      "${LIMIT_ARGS[@]}" \
      > "$log" 2>&1; then
      echo "  ok"
    else
      status=$?
      echo "  failed status=$status (see $log)"
      exit "$status"
    fi
  done
done

echo "All runs finished. Logs: $LOG_DIR"
echo "Results: $ROOT/jury_step_by_step/jury_baseline_dummy_one_judge/results_ollama/<domain>/<model_slug>/"
