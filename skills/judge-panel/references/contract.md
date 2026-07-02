# The Judge-Panel Contract

One function: `judge(PanelRequest) -> Verdict`. This file is the authoritative schema.
Everything downstream (topologies, aggregation, calibration) operates on these objects.

## PanelRequest

```jsonc
{
  // Exactly one of `candidate` or `candidates` is required.
  "candidate":  { "id": "cand-1", "content": "...", "meta": {} },   // single-item scoring/gating
  "candidates": [ { "id": "A", "content": "..." }, { "id": "B", "content": "..." } ], // K-way ranking

  // What is being judged, and how.
  "task_context": "The original prompt / question / spec the candidate answers.",
  "rubric": {
    "criteria": [
      { "name": "accuracy",   "description": "Factual correctness vs task_context.", "weight": 0.5 },
      { "name": "completeness","description": "Covers every asked-for element.",       "weight": 0.3 },
      { "name": "clarity",     "description": "Unambiguous, well-structured.",         "weight": 0.2 }
    ],
    "scale": { "min": 1, "max": 5 },        // 1-3 / 1-5 / 1-10; 1-5 is the default. See ce-advanced-evaluation.
    "evidence_required": true,               // MUST be true; ungrounded votes are rejected.
    "pass_threshold": 3.5,                   // optional; only for gate decisions.

    // Optional autoevals-style CLASSIFY rubric: instead of a numeric scale, a judge picks a named
    // choice; each choice maps to a fixed score. Makes verdicts stable and self-documenting.
    "choice_scores": { "great": 1.0, "ok": 0.5, "bad": 0.0 },
    "cot": true                              // ask the judge to reason step-by-step BEFORE choosing.
  },

  // The panel. >= 3 judges; prefer an ODD count so majority cannot deadlock.
  "judges": [
    // `variant` names an evolvable prompt variant of the judge (see SKILL.md "functions-with-variants").
    // `composite` optionally points at a DAG-composite judge spec (see composite-judges.md).
    { "id": "j-opus",  "model": "claude-opus-4-8",  "temperature": 0, "weight": 1.0, "variant": "strict-v3" },
    { "id": "j-gpt",   "model": "gpt-5.2",          "temperature": 0, "weight": 1.0 },
    { "id": "j-gemini","model": "gemini-3.1-pro",   "temperature": 0, "weight": 1.0 }
  ],

  "topology":    "independent",              // "independent" | "debate" | "chateval" | "council" | "hierarchical"
  "aggregation": "median",                   // "median" | "mean" | "weighted" | "majority" | "borda"
  "aggregation_params": { "trim_k": 1 },     // only for "trimmed"; ranking uses borda/copeland/median_rank

  // Per-topology knobs (only the block for the chosen topology is read):
  "debate":       { "rounds": 1, "epsilon": 0.25 },
  "chateval":     { "mode": "simultaneous", "rounds": 2, "roles": ["expert","critic","public"] },
  "council":      { "chairman": "gemini-3.1-pro" },
  "hierarchical": { "uncertain_range": [0.4, 0.7] },   // episteme default; escalate to full panel inside it

  // Optional self-calibration. If present, per-judge reliability weights and bias offsets
  // learned from the ledger are folded into aggregation. See self-calibration.md.
  "calibration": { "ledger_path": ".judge-panel/ledger.jsonl", "apply_weights": true },

  "seed": 7,                                 // passed to providers that support it, for reproducibility.
  "concurrency": 8                           // max simultaneous judge calls.
}
```

### Field rules

- **`weight`** on a judge is the *caller-supplied prior*. Calibration weights (learned) are
  multiplied on top; the effective weight is `w_caller * w_calibrated`.
- **`scale`** must match rubric detail: never use 1–10 without a per-level rubric (calibration
  is unreliable at high granularity). Delegate rubric design to `ce-advanced-evaluation`.
- **`weight`s across criteria** need not sum to 1; the panel normalizes them.
- A judge's **`model`** family is recorded so the panel can flag self-enhancement (a judge
  grading a candidate produced by its own family) — see failure-modes.md.

## JudgeVote (one per judge, per candidate)

Every judge returns this exact object. Parse strictly; a malformed vote is a *retry*, and after
`max_retries` it is recorded as an **abstention**, not a zero.

```jsonc
{
  "judge_id": "j-opus",
  "candidate_id": "cand-1",
  "per_criterion": [
    {
      "name": "accuracy",
      "evidence": ["Cites 100C at sea level, which matches the task's physics."], // REQUIRED, non-empty
      "score": 5,
      "justification": "All stated facts are correct and relevant."
    }
    // ... one entry per rubric criterion
  ],
  "cot": "...",               // optional chain-of-thought, emitted BEFORE `choice`/`score` when rubric.cot=true
  "choice": "great",          // autoevals CLASSIFY mode only: the named choice picked
  "score": 4.6,               // judge's own weighted rollup on the rubric scale (or choice_scores[choice])
  "decision": "PASS",         // gate mode: PASS/FAIL. tournament mode: rank or winner label.
  "ranking": ["B","A","C"],   // ranking/council topologies only: this judge's ordering of candidates
  "confidence": 0.82,         // 0..1, the judge's self-reported certainty
  "abstained": false,
  "raw": "..."                // verbatim model text, kept for audit
}
```

**autoevals-style scoring.** A judge is essentially an autoevals `LLMClassifier`: a **template**
(the scoring prompt), a **choice → score map** (`rubric.choice_scores`), and an optional **CoT**
step. In CLASSIFY mode the judge outputs a `choice`; `score = choice_scores[choice]`. In SCALAR mode
it outputs a numeric `score` on `scale`. Either way the evidence-before-score rule (invariant #1)
holds: `cot`/`per_criterion.evidence` must precede the number. A judge whose verdict is itself a
decision tree is a **DAG composite judge** — see [composite-judges.md](composite-judges.md).

**Enforced at parse time:** `evidence` non-empty for every criterion (invariant #1); `score`
within `scale`; `confidence` in `[0,1]`. Violations → reparse, then abstain.

## Verdict (returned to the caller)

```jsonc
{
  "mode": "gate",             // "gate" | "score" | "tournament"
  "decision": "PASS",         // PASS/FAIL, or winner id, or full ranked list for tournaments
  "score": 4.4,              // aggregated scalar per the chosen aggregator (null for pure ranking)
  "confidence": 0.86,         // level "HIGH"|"MEDIUM"|"LOW" (episteme) OR scalar 0..0.99; from sigma + unanimity + calibration
  "score_sigma": 0.21,        // stddev of judge scores — the dispersion the confidence level is computed from
  "agreement": 0.71,          // inter-judge concordance (Krippendorff alpha for ranks; 1-normalized-sigma for scalars)
  "votes": [ /* every JudgeVote verbatim */ ],
  "dissent": [                // judges whose decision != panel decision
    { "judge_id": "j-gpt", "decision": "FAIL", "score": 2.0, "reason": "flagged an unsupported claim" }
  ],
  "abstentions": ["j-x"],     // judges that could not produce a valid vote
  "calibration_delta": 0.12,  // present only if a ledger is attached: |predicted - realized| running estimate
  "metadata": {
    "topology": "independent", "aggregation": "median", "n_judges": 3, "seed": 7,
    "rounds": 1,                // debate/chateval: rounds actually run
    "moved": [],                // debate: judges that revised, with from/to/reason
    "escalated": false,         // hierarchical: did the cheap judge trigger the full panel?
    "synthesis": null           // council: the chairman's synthesized final answer
  }
}
```

## Modes are inferred, not configured

- `candidate` present, `rubric.pass_threshold` set → **gate** (`decision` = PASS/FAIL).
- `candidate` present, no threshold → **score** (`decision` = the scalar's band, `score` populated).
- `candidates[]` present → **tournament** (`decision` = winner or ranked list).

## Determinism & auditability

- The complete list of `votes` is always returned verbatim. The panel never discards a vote,
  even an abstention or an outlier — aggregation may *down-weight* it, but the audit trail is total.
- With `temperature: 0` and a fixed `seed`, an independent-topology panel is reproducible up to
  provider nondeterminism. Record the seed and model ids in `metadata` so a verdict can be replayed.
