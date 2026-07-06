#!/usr/bin/env bash
set -u -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/jury_step_by_step/jury_explainability_and_prompts/main.py"
TRAJ_DIR="$ROOT/data/input/trajectories/browseruse_gpt4o_parsed"
TASKS_DIR="$ROOT/data/input/tasks/less_sensitive"
LOG_DIR="$ROOT/jury_step_by_step/jury_explainability_and_prompts/logs"
RESULTS_DIR="$ROOT/jury_step_by_step/jury_explainability_and_prompts/results_ollama"
mkdir -p "$LOG_DIR"

DOMAINS_STR=${DOMAINS:-"shopping_Amazon_chat shopping_ebay_chat"}
PROMPTS_STR=${PROMPTS:-"balanced_fewshot.md strict_evidence_fewshot.md explainability_rationale_fewshot.md comparative_counterexamples_fewshot.md"}
MODELS_STR=${MODELS:-"gemma4:31b"}
SKIP_DONE=${SKIP_DONE:-1}

read -r -a DOMAINS_ARR <<< "$DOMAINS_STR"
read -r -a PROMPTS_ARR <<< "$PROMPTS_STR"
read -r -a MODELS_ARR <<< "$MODELS_STR"

LIMIT_ARGS=()
if [[ "${LIMIT_PERSONAS:-}" != "" ]]; then
  LIMIT_ARGS+=(--limit-personas "$LIMIT_PERSONAS")
fi
if [[ "${LIMIT_STEPS:-}" != "" ]]; then
  LIMIT_ARGS+=(--limit-steps "$LIMIT_STEPS")
fi

slug() {
  printf '%s' "$1" | sed 's/[^A-Za-z0-9_.-]/_/g; s/^_*//; s/_*$//'
}

models_slug="$(slug "${MODELS_STR// /__}")"
run_stamp="$(date +%Y%m%d_%H%M%S)"
summary="$LOG_DIR/batch_summary_${run_stamp}.log"

echo "Explainability batch started: $(date)" | tee -a "$summary"
echo "Domains: $DOMAINS_STR" | tee -a "$summary"
echo "Prompts: $PROMPTS_STR" | tee -a "$summary"
echo "Models: $MODELS_STR" | tee -a "$summary"
echo "Skip done: $SKIP_DONE" | tee -a "$summary"
echo "Logs: $LOG_DIR" | tee -a "$summary"

for domain in "${DOMAINS_ARR[@]}"; do
  for prompt in "${PROMPTS_ARR[@]}"; do
    prompt_slug="$(slug "${prompt%.md}")"
    out_dir="$RESULTS_DIR/$domain/$prompt_slug/$models_slug"
    done_file="$out_dir/raw_judge_outputs_summary.json"
    log="$LOG_DIR/${domain}_${prompt_slug}_${models_slug}_${run_stamp}.log"

    if [[ "$SKIP_DONE" == "1" && -f "$done_file" ]]; then
      echo "[$(date)] SKIP done domain=$domain prompt=$prompt models=$MODELS_STR out=$out_dir" | tee -a "$summary"
      continue
    fi

    echo "[$(date)] START domain=$domain prompt=$prompt models=$MODELS_STR" | tee -a "$summary"

    python3 -u "$APP" \
      --domain "$domain" \
      --trajectories-dir "$TRAJ_DIR" \
      --tasks-dir "$TASKS_DIR" \
      --models "${MODELS_ARR[@]}" \
      --prompt-template "$prompt" \
      "${LIMIT_ARGS[@]}" \
      > "$log" 2>&1

    status=$?
    if [[ $status -eq 0 ]]; then
      echo "[$(date)] OK domain=$domain prompt=$prompt log=$log out=$out_dir" | tee -a "$summary"
    else
      echo "[$(date)] FAIL status=$status domain=$domain prompt=$prompt log=$log" | tee -a "$summary"
    fi
  done
done

echo "Explainability batch finished: $(date)" | tee -a "$summary"
echo "Raw results: $RESULTS_DIR/<domain>/<prompt_slug>/<models_slug>/" | tee -a "$summary"
