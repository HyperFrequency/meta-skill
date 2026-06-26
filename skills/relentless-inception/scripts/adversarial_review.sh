#!/usr/bin/env bash
# adversarial_review.sh — gate evaluator that shells out to codex (plus
# parallel openrouter routes for the summarize gate's triple).
#
# Usage:
#   adversarial_review.sh --gate=plan|phase|summarize \
#                         --inputs=<path-to-inputs-bundle.json> \
#                         --models=<csv-of-models> \
#                         --effort=<low|medium|high|xhigh> \
#                         --out=<path-to-verdict.json>
#
# For --gate=summarize, --models is a CSV of three model names; the script
# invokes codex (or the openrouter route) three times in parallel and
# aggregates results into a single verdict.json with a top-level "reviewers"
# array. Pass = ALL three reviewers approve.

set -euo pipefail

GATE=""
INPUTS=""
MODELS=""
EFFORT="high"
OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --gate=*)    GATE="${1#*=}";;
    --inputs=*)  INPUTS="${1#*=}";;
    --models=*)  MODELS="${1#*=}";;
    --effort=*)  EFFORT="${1#*=}";;
    --out=*)     OUT="${1#*=}";;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
  shift
done

for f in "$INPUTS"; do
  [[ -f "$f" ]] || { echo "missing inputs file: $f" >&2; exit 2; }
done
mkdir -p "$(dirname "$OUT")"

if ! command -v codex >/dev/null 2>&1; then
  echo "error: codex CLI not found. Install via the codex:setup skill." >&2
  exit 3
fi

# Compose the gate prompt from the agents/adversarial-review.md template
# plus the inputs bundle. The script writes a complete prompt file per
# reviewer slot, then shells out to codex with --model and --effort.

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GATE_TEMPLATE="$SKILL_DIR/agents/adversarial-review.md"
[[ -f "$GATE_TEMPLATE" ]] || { echo "error: $GATE_TEMPLATE missing" >&2; exit 3; }

REVIEWER_TIMEOUT="${REVIEWER_TIMEOUT:-180}"   # 3 min default; bumpable via env

run_reviewer() {
  local slot="$1"
  local model="$2"
  local out_file="$3"
  local prompt_file
  prompt_file=$(mktemp)
  {
    printf '# Adversarial review: gate=%s slot=%s model=%s\n\n' "$GATE" "$slot" "$model"
    printf '## Role instructions\n'
    cat "$GATE_TEMPLATE"
    printf '\n\n## Inputs\n'
    cat "$INPUTS"
    printf '\n\n## Required output\n'
    printf 'Return ONLY the JSON verdict. No prose preamble. No trailing text.\n'
  } > "$prompt_file"

  # Bound the reviewer call. A hung reviewer would otherwise stall the gate
  # (and the whole run) indefinitely. On timeout we write an explicit fail
  # JSON so the gate aggregation has something well-formed to consume.
  if ! timeout "$REVIEWER_TIMEOUT" codex --model "$model" --effort "$EFFORT" --no-tools \
        --json --output "$out_file" \
        < "$prompt_file"; then
    rc=$?
    cat > "$out_file" <<EOF
{"verdict":"fail","_runtime":{"slot":"$slot","model":"$model","timeout_or_error":true,"exit_code":$rc,"timeout_seconds":$REVIEWER_TIMEOUT},"recommendation":"regenerate","blocking_issues":["reviewer call did not return within timeout"]}
EOF
  fi

  # Validate the output is parseable JSON with at minimum a `verdict` field.
  # Replace malformed output with an explicit fail so downstream code never
  # reads garbage.
  if ! jq -e 'has("verdict") and (.verdict | type == "string")' "$out_file" >/dev/null 2>&1; then
    cat > "$out_file" <<EOF
{"verdict":"fail","_runtime":{"slot":"$slot","model":"$model","malformed_output":true},"recommendation":"regenerate","blocking_issues":["reviewer returned malformed JSON; treating as fail"]}
EOF
  fi

  rm -f "$prompt_file"
}

case "$GATE" in
  plan|phase)
    # Single reviewer.
    MODEL=$(printf '%s' "$MODELS" | cut -d, -f1)
    run_reviewer "single" "$MODEL" "$OUT"
    ;;

  summarize)
    # Three reviewers in parallel.
    A=$(printf '%s' "$MODELS" | cut -d, -f1)
    B=$(printf '%s' "$MODELS" | cut -d, -f2)
    C=$(printf '%s' "$MODELS" | cut -d, -f3)
    [[ -n "$A" && -n "$B" && -n "$C" ]] || { echo "summarize gate needs 3 models in --models CSV" >&2; exit 2; }

    out_a=$(mktemp); out_b=$(mktemp); out_c=$(mktemp)
    run_reviewer "A" "$A" "$out_a" &
    pid_a=$!
    run_reviewer "B" "$B" "$out_b" &
    pid_b=$!
    run_reviewer "C" "$C" "$out_c" &
    pid_c=$!
    wait $pid_a $pid_b $pid_c

    if command -v jq >/dev/null 2>&1; then
      # Summarize gate is the strictest in the skill: every reviewer must
      # return verdict==pass AND recommendation==approve. Any other state
      # (`merge-with-fixes`, `regenerate`, malformed, timeout) is a fail.
      # See agents/adversarial-review.md "How you decide pass vs fail".
      jq -n \
        --slurpfile a "$out_a" --slurpfile b "$out_b" --slurpfile c "$out_c" \
        --arg A "$A" --arg B "$B" --arg C "$C" \
        'def approves(v): (v.verdict=="pass") and (v.recommendation=="approve");
         {gate:"summarize",
          reviewers:[
            {slot:"A", model:$A, verdict:$a[0]},
            {slot:"B", model:$B, verdict:$b[0]},
            {slot:"C", model:$C, verdict:$c[0]}
          ],
          verdict: (if (approves($a[0]) and approves($b[0]) and approves($c[0])) then "pass" else "fail" end),
          unanimity: (approves($a[0]) and approves($b[0]) and approves($c[0])),
          dissent_reasons: ([$a[0],$b[0],$c[0]] | map(select(approves(.) | not) | {model:.["_runtime"].model // "<unknown>", verdict:.verdict, recommendation:.recommendation, blocking_issues:(.blocking_issues // [])}))
        }' > "$OUT"
    else
      echo "{\"gate\":\"summarize\",\"verdict\":\"fail\",\"error\":\"jq required\"}" > "$OUT"
    fi
    rm -f "$out_a" "$out_b" "$out_c"
    ;;

  *)
    echo "unknown gate: $GATE (expected plan|phase|summarize)" >&2
    exit 2
    ;;
esac

echo "verdict written: $OUT"
