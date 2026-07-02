---
name: judge-panel
version: 0.2.0
description: "Reusable multi-judge VERDICT primitive: one auditable verdict/score from N LLM judges on any candidate (a response, diff, strategy, or plan). ONE contract — PanelRequest, evidence-before-score JudgeVote (autoevals templates, choice_scores, optional CoT, DAG composite judges), aggregated Verdict — over FIVE topologies (parallel-independent, R-round debate, ChatEval, 3-stage anonymized council, hierarchical cheap→escalate) and five aggregators (median/mean/weighted/majority/Borda) with sigma confidence + unanimity, a predicted-vs-realized calibration ledger, and an Align-Evals correction loop that de-bias judges. Judges are evolvable functions-with-variants. Use when a skill needs a multi-judge verdict: LLM-as-jury, PoLL, scoring gates, tournament ranking. NOT an app/eval-harness (returns a verdict; owns no datasets/CI/UX). NOT for single-judge design (ce-advanced-evaluation), human deliberation (consciousness-council), backtest verification (strategy-verify), or purged-CV/PBO/DSR scoring (model-evaluation)."
allowed-tools: Read Write Edit Bash
license: MIT
---

# Judge Panel

A single reusable primitive that turns N LLM judges into one **scored, auditable verdict** on
any candidate. It is a building block other skills *call* — not an application, not an eval
harness, not a deliberation experience. Its whole job: take a candidate + a rubric, run a chosen
topology, aggregate the votes, and return a typed `Verdict`.

It unifies the judge patterns scattered across the library behind **one contract**. The primary
donor is **episteme**'s ensemble `JudgePool` (`src/pool/judge.rs`) — the most complete existing
impl (weighted-round-robin model selection, median/average/weighted aggregation, sigma-based
confidence, hierarchical escalation). The 3-stage **council** preset is lifted from
**karpathy/llm-council** (opinions → anonymized peer ranking → chairman synthesis). Verdict shape
borrows autoevals-style `{template, choice_scores, CoT}` per judge and DeepEval-style DAG judges.

## When to use

Reach for judge-panel when a caller needs a **structured multi-judge score or verdict**:

- LLM-as-a-jury / Panel-of-LLMs (PoLL) to reduce single-judge bias on a high-stakes call.
- A scoring **gate** ("does this candidate clear the bar?") with an auditable rationale.
- **Tournament / ranking** of K candidates (fusion outputs, prompt variants, model outputs).
- Any sibling skill that says "get a panel verdict" and wants a drop-in contract instead of
  hand-rolling judge prompts, position-swaps, and vote math again.

## When NOT to use (anti-triggers)

- **Designing a single judge** (one direct-scoring or pairwise prompt, rubric calibration, bias
  mechanisms) → `ce-advanced-evaluation`. judge-panel *consumes* those judges.
- **Human-facing multi-perspective deliberation** (archetypes, "core tension", advice) →
  `consciousness-council`. That optimizes for insight; this optimizes for a *number*.
- **Verifying a quant backtest** against a baseline → `strategy-verify`.
- **Purged-CV / PBO / deflated-Sharpe model scoring** → `model-evaluation`.
- **Running a dataset sweep / CI wiring / trace logging** → `opik` or `recursive-batch-eval`.
  This primitive scores *one* candidate (or one K-way tournament) per call; a harness loops it.

## The contract (read this first)

Every call is `judge(PanelRequest) -> Verdict`. Full field-by-field schema, JSON examples, the
`JudgeVote` object, autoevals-style templates, and DAG composite judges are in
[references/contract.md](references/contract.md). The shape:

```
PanelRequest {
  candidate | candidates[]      # one candidate, or K for tournament
  rubric    { criteria[], scale, evidence_required: true, choice_scores? }
  judges[]  { id, model, temperature=0, weight?, system?, variant? }   # >= 3, prefer odd
  topology     "independent" | "debate" | "chateval" | "council" | "hierarchical"
  aggregation  "median" | "mean" | "weighted" | "majority" | "borda"
  calibration? { ledger_path, apply_weights, align_evals? }            # optional de-bias
}
Verdict {
  decision       # PASS/FAIL, winner id, or ranked[]
  score          # aggregated scalar (aggregator-dependent; null for pure ranking)
  confidence     # High/Med/Low OR 0..1, from sigma + unanimity + calibration
  votes[]        # every JudgeVote, verbatim, for audit
  dissent        # judges that disagreed with the decision
  agreement      # 1 - normalized sigma (scalars) / Krippendorff alpha (ranks)
  calibration_delta?  # predicted-vs-realized gap if a ledger is attached
}
```

**Non-negotiable invariants** (the failures each prevents are in references):

1. **Evidence before score.** Every `JudgeVote` cites observable features of the candidate
   *before* emitting a number. Reject ungrounded votes.
2. **Judges are independent by default.** No judge sees another's vote unless the topology is
   `debate`, `chateval`, or `council` (round ≥ 2). Run round 1 concurrently.
3. **Temperature 0** for scoring judges; diversity comes from *different models/prompts/variants*,
   not sampling noise. Use `seed` where the provider supports it.
4. **Odd panel size** (3, 5, 7) so `majority` cannot deadlock.
5. **Never 1.0 confidence.** Cap at 0.99 (or `High`, never "certain") — a panel is still a panel.

## Topologies (pick one)

A topology decides *what each judge sees and in what order* — the biggest lever on
bias-decorrelation and cost. Mechanics, prompt scaffolds, anonymization rules, and shuffle-seed
handling: [references/topologies.md](references/topologies.md).

| Topology | What judges see | Use when | Cost |
|---|---|---|---|
| **independent** | Only candidate + rubric; vote in parallel (Du et al round-1). | Default. Direct scoring / PASS-FAIL gates. Maximal decorrelation. | N |
| **debate** | Round 1 independent, then R rounds where each judge reads peers' anonymized rationales and may revise. | High-stakes calls where a lone correct judge should move the panel. | (R+1)·N |
| **chateval** | Judges converse: one-by-one (sequential), simultaneous (each sees the prior round), or simultaneous+summarizer. | Nuanced qualitative rubrics that benefit from cross-talk. | R·N (+1) |
| **council** | 3 stages: private opinions → anonymized peer cross-review + rank → chairman synthesis (karpathy). | Ranking K + producing one synthesized answer; anti-sycophancy via anonymization. | 2N + 1 |
| **hierarchical** | Cheap judge first; escalate to the full ensemble only if its score lands in `uncertain_range` (episteme). | Cost control at scale — most items are easy. | 1 → N on the hard tail |

## Aggregation (pick one)

Match the aggregator to the *decision type* (categorical vs scalar vs ranking) and the *noise
profile*. Weighting, tie-breaks, sigma-based confidence, and the confidence/unanimity rules:
[references/aggregation.md](references/aggregation.md).

| Aggregator | Rule | Use for | Guards |
|---|---|---|---|
| **median** | Middle score. | **Default for scalars**; robust to one outlier. | Even N → mean the two middles. |
| **mean** | Arithmetic mean. | Well-behaved rubrics, no rogue judge. | One outlier drags it. |
| **weighted** | Weighted mean with effective weight `w_caller · w_calibrated`. | Judges of known unequal reliability (from the ledger). | Normalize weights; keep raw votes. |
| **majority** | Modal `decision`. | Categorical (PASS/FAIL, winner). | Odd N; ties → abstain/escalate. |
| **borda** | Rank points summed over judges (also Copeland / median-rank). | Ranking K candidates (council / tournament). | Record the tiebreaker that fired. |

**Confidence is derived, never self-reported.** Following episteme: from score **sigma** across
judges — `sigma >= threshold` → **Low** (no consensus, a valuable signal); else **High** iff the
verdict is **unanimous**, otherwise **Medium** (scalar form: `1 - normalized_sigma`, ledger-folded,
capped 0.99). `dissent[]` is always populated — suppressed dissent is how bad panels hide being wrong.

## Self-calibration ledger + Align-Evals

A judge that is *consistently* wrong is worse than a noisy one. The panel keeps an append-only
**predicted-vs-realized ledger**: each judge's prediction is later paired with a realized outcome
(human label, market/PnL, downstream test pass, or a larger-panel proxy). Over time this yields
per-judge **reliability weights** and **bias offsets** that feed back into aggregation, so
drifting or sycophantic judges are automatically down-weighted (ledger deltas modeled on
`tournament-autoresearch`'s predicted-vs-realized tracking).

Layered on top, an **Align-Evals loop** turns *human corrections* into **few-shot exemplars** spliced
into the judge prompt, and tracks **judge/human agreement as its own regression-gated metric** — if a
prompt change drops agreement below the gate, it is rejected. Ledger schema, the de-biasing update
rule, cold-start defaults, Align-Evals, and how to (optionally) wrap the MIT **`gepa`** crate to
*evolve* judge prompts against realized signal: [references/self-calibration.md](references/self-calibration.md).

## Composite / DAG judges

A single rubric criterion is sometimes itself a decision tree ("if the answer is off-topic, score
0 regardless of the other axes"). judge-panel supports **DeepEval-style DAG composite judges**: a
judge's verdict is computed by a small directed-acyclic graph of sub-judgments whose leaves are
scores and whose branches are gating conditions. The DAG is per-judge; the panel still aggregates
the resulting scalar/decision normally. Structure, node types, and worked DAGs:
[references/composite-judges.md](references/composite-judges.md).

## Judges are functions-with-variants (evolvable)

A judge is `(candidate, rubric) -> JudgeVote` parameterized by `{model, system-prompt, variant}`.
Because a variant is just a prompt, the **prompt-optimization loop** (`prompt-optimize` / `gepa`)
can breed better judge variants against the ledger's realized-accuracy signal — the panel is the
fitness harness, the judge prompt is the genome. Keep it optional and flagged; the panel must run
with hand-written judges alone.

## Minimal usage

```
1. Build a PanelRequest: candidate + rubric + >=3 judges, topology=independent, aggregation=median.
2. Run round-1 judges concurrently at temperature 0; parse JudgeVote (evidence, score, confidence).
3. Aggregate -> Verdict; compute sigma + unanimity -> confidence; attach every vote for audit.
4. (optional) Append (judge, prediction) rows to the ledger; reconcile on realized outcome;
   recompute reliability weights + Align-Evals exemplars for the next call.
```

Concrete request→verdict walkthroughs (a PASS/FAIL gate, a 4-way anonymized tournament, a debate
that flips a majority, a council synthesis, a hierarchical escalation):
[references/examples.md](references/examples.md).

## Failure modes & edge cases

Empty/degenerate candidates, all-judges-abstain, tie storms, correlated judges (same base model),
self-enhancement, position/length/verbosity bias, herding in debate, malformed vote JSON, rate
limits mid-panel, hierarchical mis-escalation, and ledger cold-start:
[references/failure-modes.md](references/failure-modes.md).

## Cross-links

- **`consciousness-council`** — human-facing deliberation for insight; call it when the goal is
  *understanding a trade-off*, not producing a score. judge-panel can score a council transcript.
- **`ce-advanced-evaluation`** — designs the *individual* judge (rubrics, scales, single-judge
  bias). Author judges there, then hand them to this panel.
- **`model-evaluation`** — statistical quant scoring (purged CV, PBO, deflated Sharpe). Use it for
  the realized-outcome side of the ledger when the candidate is a strategy.
- **`strategy-verify`** — end-to-end backtest verification vs a baseline.
- **`prompt-optimize` / `gepa`** — evolve judge variants against the ledger's realized signal.
- **`recursive-batch-eval`** / **`opik`** — the *harness* layer that loops this primitive over a
  dataset and logs traces; judge-panel is the per-item scorer they invoke.

## References

- [references/contract.md](references/contract.md) — PanelRequest / JudgeVote / Verdict schema, autoevals templates, choice_scores.
- [references/topologies.md](references/topologies.md) — independent, debate (R rounds), ChatEval, council, hierarchical + prompts.
- [references/aggregation.md](references/aggregation.md) — median/mean/weighted/majority/Borda, sigma confidence, unanimity, tie-breaks.
- [references/self-calibration.md](references/self-calibration.md) — the ledger, de-biasing, Align-Evals loop, `gepa` wrap.
- [references/composite-judges.md](references/composite-judges.md) — DeepEval-style DAG composite judges.
- [references/failure-modes.md](references/failure-modes.md) — edge cases and boundaries.
- [references/examples.md](references/examples.md) — worked request→verdict walkthroughs.
