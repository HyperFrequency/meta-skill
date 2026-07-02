# Failure modes, edge cases & boundaries

A panel that only works on the happy path is worse than one judge, because it *looks* rigorous
while hiding correlated error. Handle every case below explicitly.

## Degenerate inputs

| Case | What happens if ignored | Handling |
|---|---|---|
| **Empty / whitespace candidate** | Judges hallucinate a candidate or score noise. | Reject before dispatch; return `FAIL` / lowest rank with `reason: "empty candidate"`. |
| **Empty rubric / no criteria** | Judges invent their own bar; scores incomparable. | Reject: at least one criterion with a description is required. |
| **Single judge (N=1)** | It is not a panel; agreement and calibration are meaningless. | Refuse or warn loudly; route to `ce-advanced-evaluation` for single-judge scoring. |
| **Even N + majority** | PASS/FAIL can deadlock. | Warn; on a tie return `ABSTAIN` and escalate. Prefer odd N. |
| **K=1 in cross_ranking** | Nothing to rank. | Fall back to single-candidate scoring. |

## Judge-behavior failures

- **All judges abstain** (all votes malformed after retries): return `decision: ABSTAIN`,
  `confidence: 0.5`, and surface the raw errors. Never fabricate a score.
- **Tie storm** (scores/ranks with no separation): report the tie honestly with low confidence and
  the tiebreaker that fired; do not manufacture a winner the data doesn't support.
- **Correlated judges (same base model).** Three judges that are all GPT-family are *one* judge
  wearing three hats — their errors correlate and the panel's apparent agreement is fake confidence.
  **Compose the panel from different model families/vendors.** The ledger's agreement→accuracy map
  will eventually expose the inflation, but prevention beats detection: diversify at request time.
- **Self-enhancement bias.** A judge grades a candidate produced by its own model family and
  favors it. Flag any judge whose `model` family matches the candidate's `meta.producer`;
  down-weight it for that candidate, or exclude it. (Mechanism owned by `ce-advanced-evaluation`.)
- **Position / length / verbosity bias.** Longer or first-placed candidates score higher.
  Mitigated structurally by `cross_ranking` (anonymize + per-judge shuffle) and by length-neutral
  prompt instructions; validate with length-controlled pairs.
- **Sycophancy / herding in debate.** Judges cave to the majority in Round 2 without new evidence.
  Guardrail: show rationales not scores, forbid social-proof revisions, keep Round-1 votes, and
  track a herding penalty in the ledger.
- **Overconfidence.** Judges self-report 0.95 while disagreeing with each other. Never trust
  self-reported confidence as the panel's confidence — derive it from agreement (aggregation.md).

## Operational failures

- **Rate limit / timeout mid-panel.** A judge fails after others succeeded. Retry with exponential
  backoff; if it still fails, record it as an abstention and aggregate over the survivors —
  **provided** enough judges remain for a valid decision (≥3 for majority; else escalate/re-run).
  Do not block the whole verdict on one slow provider.
- **Malformed vote JSON.** Reparse once with a stricter instruction; then abstain. A malformed vote
  is an **abstention, not a zero** — a zero silently swings the aggregate.
- **Non-deterministic providers.** Even at temperature 0 some providers vary run to run. Record
  `seed` + model ids in `metadata`; for reproducibility-critical gates, run each judge twice and
  require self-consistency before trusting the vote.
- **Cost blowup.** `debate` is 2N and large K in `cross_ranking` is N× a long prompt. Budget: use
  `independent` by default, reserve `debate` for high-stakes calls, cap K, and consider a cheap
  screening panel before an expensive one (hierarchical evaluation).

## Calibration edge cases

- **Cold start** (< `min_reconciled` reconciled rows): do not apply learned weights; use equal
  weights. Applying a weight learned from 3 samples entrenches noise.
- **Circular ground truth**: never reconcile a judge against a "large panel" that contains that same
  judge — exclude it from its own ground truth. Prefer human/market/test signals.
- **Regime change**: a model version bump invalidates that judge's history — key rows by `model` id
  and reset on change.

## Boundaries (what this primitive does NOT do)

- It scores **one candidate or one K-way tournament per call.** Looping over a dataset, logging
  traces, and CI gating belong to `recursive-batch-eval` / `opik`.
- It does **not design the individual judge** (rubric wording, scale choice, single-judge bias
  proofs) — that is `ce-advanced-evaluation`.
- It does **not produce human-facing insight or advice** — that is `consciousness-council`.
- It does **not compute quant ground truth** (Sharpe, PBO, deflated Sharpe) — it *consumes* those
  from `model-evaluation` / `strategy-verify` as the realized side of the ledger.
