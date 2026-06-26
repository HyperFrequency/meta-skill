# Adversarial gates

Three gates fire per cycle. Each gate is a structured pass/fail decision by an independent model that can't see (and didn't make) the artifact being reviewed.

The gates exist because subagents systematically over-trust their own output. The fix is to put a fresh-context, different-model reviewer in the path, with veto power.

---

## Gate 1 — Plan gate

**Fires:** after `planner` + `architecture-analyzer` propose a plan, before any dev-worker is dispatched.

**Reviewer:** `adversarial-review` agent. Default model `gpt-5.5 --effort high`; bumps to `xhigh` if rescue is active.

**Inputs (read-only):**
- The full user prompt
- The plan markdown
- The acceptance criteria list
- Run manifest with proposed phases + units

**Expected output:** structured JSON

```json
{
  "verdict": "pass|fail",
  "missing_criteria": ["..."],
  "weak_units": [{"id": N, "reason": "..."}],
  "ambiguity": [{"line": N, "alternatives": ["...","..."]}],
  "surgical_fixes": ["concrete change to the plan"],
  "blocking_issues": ["things that must be resolved before dispatch"],
  "non_blocking_notes": ["nice-to-haves"]
}
```

**Fail action:** orchestrator routes the verdict back to the planner pair, which produces a revised plan. Max 3 plan-gate iterations before escalating to rescue.

---

## Gate 2 — Phase gate

**Fires:** after each plan phase completes its merge into the run's working branch, but before the next phase begins.

**Reviewer:** `adversarial-review` agent. Same model defaults.

**Inputs (read-only):**
- The phase's deliverables (diff vs phase start)
- Per-unit verification reports
- The cumulative tearsheet through this phase
- The acceptance criteria the phase claimed to satisfy

**Expected output:** same JSON shape as plan gate, plus:

```json
{
  "criteria_actually_satisfied": ["AC1", "AC3", ...],
  "criteria_claimed_but_not_satisfied": ["AC2 with reason"],
  "regressions_detected": ["..."]
}
```

**Fail action:** orchestrator opens "fix units" for the failed criteria + regressions and re-runs the phase. Max 3 phase-gate iterations before escalating.

---

## Gate 3 — Summarize gate (triple)

**Fires:** every time the orchestrator wants to compact context or hand off a summary (between phases, before a rescue, or when the user requests a checkpoint).

**Reviewers:** *three independent models running in parallel*, each in a fresh context:

| Reviewer slot | Default model        | Effort | Provider routing  |
|---------------|----------------------|--------|-------------------|
| A             | gpt-5.5              | xhigh  | openrouter        |
| B             | gemini-latest         | xhigh  | openrouter        |
| C             | opus-4.7             | xhigh  | anthropic         |

**Inputs (read-only):**
- The proposed summary markdown
- The session log up to this point
- The current run manifest

**Expected output (each reviewer):**

```json
{
  "verdict": "pass|fail",
  "facts_dropped": ["..."],
  "facts_distorted": [{"original": "...", "summary": "..."}],
  "structural_problems": ["..."],
  "recommendation": "approve | regenerate | merge-with-fixes"
}
```

**Pass condition:** *all three* reviewers must return `pass`. This is intentionally strict — losing facts during summarization is the single largest source of long-run drift, and a 2-of-3 vote would still let one reviewer's blind spot pass through.

**Fail action:** orchestrator regenerates the summary with the union of all three reviewers' notes, then re-runs the triple gate. Max 3 summarize-gate iterations before escalating.

---

## Implementation

All three gates use `scripts/adversarial_review.sh` under the hood. The script accepts:

```
scripts/adversarial_review.sh \
  --gate=[plan|phase|summarize] \
  --inputs=<path-to-inputs-bundle.json> \
  --models=<comma-separated-model-spec> \
  --effort=<low|medium|high|xhigh> \
  --out=<path-to-verdict.json>
```

It shells out to `codex` with the right `--model` and `--effort` flags. The OpenRouter key threads through `OPENROUTER_API_KEY` (loaded from `~/.claude/.env` or the process env). Output is the JSON shapes documented above.

For the summarize gate, the script invokes `codex` three times in parallel (one per reviewer slot) and aggregates results.

---

## Why this matters

The triple gate is the load-bearing pattern in this skill. If you find yourself wanting to skip a gate "just this once," that's the signal that the orchestrator's losing discipline. Don't.

Specific failure modes the gates catch that nothing else does:

- Plan gate catches *missing acceptance criteria* — when the planner is so excited about a clever solution it forgets to test for something basic.
- Phase gate catches *claimed-but-not-done* — when a dev-worker reports "done" but didn't actually wire the integration it claimed.
- Summarize gate catches *fact loss in compaction* — when an orchestrator about to clear context drops a constraint the user mentioned hours ago.

These are the failures that turn a 6-hour run into a 36-hour run. The gates are cheap compared to the cost of catching the drift later.
