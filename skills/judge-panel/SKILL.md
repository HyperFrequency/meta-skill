---
name: judge-panel
version: 0.1.0
description: "Reusable SCORED judge-panel primitive: get a verdict from N LLM judges on any candidate (a response, a diff, a strategy, a plan, an artifact). Defines ONE contract — request schema, per-judge JudgeVote, aggregated Verdict — over three TOPOLOGIES (independent, anonymized cross-ranking, debate), four AGGREGATORS (majority, mean, median, trimmed), and a predicted-vs-realized CALIBRATION LEDGER that de-biases judges over time. Use when a skill needs a structured multi-judge score/verdict as a building block: LLM-as-jury, panel-of-LLMs (PoLL), scoring gates, tournament ranking, fusion judging. NOT an app or eval harness — it returns a verdict, it does not own datasets, CI wiring, or human deliberation UX. NOT for single-judge scoring design (use ce-advanced-evaluation), human-facing multi-perspective deliberation (use consciousness-council), quant backtest verification (use strategy-verify), or purged-CV/PBO/DSR model scoring (use model-evaluation)."
allowed-tools: Read Write Edit Bash
license: MIT
---

# Judge Panel

A single reusable primitive that turns N LLM judges into one **scored verdict** on any
candidate. It is a building block other skills *call* — not an application, not an eval
harness, not a deliberation experience. Its whole job: take a candidate + a rubric, run
a chosen topology, aggregate the votes, and return a typed `Verdict`.

This skill unifies five previously incompatible judge patterns found across the library
(`opik` `LLMJuriesJudge` / PoLL, `ce-advanced-evaluation` direct+pairwise+bias, and
`consciousness-council` deliberation scoring) behind **one contract**.

## When to use

Reach for judge-panel when a caller needs a **structured multi-judge score or verdict**:

- LLM-as-a-jury / Panel-of-LLMs (PoLL) to reduce single-judge bias on a high-stakes call.
- A scoring **gate** ("does this candidate clear the bar?") with an auditable rationale.
- **Tournament / ranking** of K candidates (fusion outputs, prompt variants, model outputs).
- Any sibling skill that says "get a panel verdict" and wants a drop-in contract instead
  of hand-rolling judge prompts, position-swaps, and vote math again.

## When NOT to use (anti-triggers)

- **Designing a single judge** (one direct-scoring or pairwise prompt, rubric calibration,
  bias mechanisms) → `ce-advanced-evaluation`. judge-panel *consumes* those judges.
- **Human-facing multi-perspective deliberation** (archetypes, "core tension", advice) →
  `consciousness-council`. That optimizes for insight; this optimizes for a *number*.
- **Verifying a quant backtest** against a baseline → `strategy-verify`.
- **Purged-CV / PBO / deflated-Sharpe model scoring** → `model-evaluation`.
- **Running a dataset sweep / CI wiring / trace logging** → `opik` or `recursive-batch-eval`.
  This primitive scores *one* candidate (or one K-way tournament) per call; a harness loops it.

## The contract (read this first)

Every call is `judge(PanelRequest) -> Verdict`. Full field-by-field schema, JSON examples,
and the `JudgeVote` object are in [references/contract.md](references/contract.md). The shape:

```
PanelRequest {
  candidate      | candidates[]     # one candidate, or K for tournament
  rubric         { criteria[], scale, evidence_required: true }
  judges[]       { id, model, temperature=0, weight?, system? }   # >= 3, prefer odd
  topology       "independent" | "cross_ranking" | "debate"
  aggregation    "majority" | "mean" | "median" | "trimmed"
  calibration?   { ledger_path, apply_weights: bool }             # optional de-bias
}
Verdict {
  decision       # PASS/FAIL, or winner id, or ranked[]
  score          # aggregated scalar (aggregator-dependent)
  confidence     # 0..1, from inter-judge agreement + calibration
  votes[]        # every JudgeVote, verbatim, for audit
  dissent        # judges that disagreed with the decision
  agreement      # Krippendorff-style alpha or simple concordance
  calibration_delta?  # predicted-vs-realized gap if a ledger is attached
}
```

**Non-negotiable invariants** (the failures each prevents are in references):

1. **Evidence before score.** Every `JudgeVote` must cite observable features of the
   candidate *before* emitting a number. Reject ungrounded votes.
2. **Judges are independent by default.** No judge sees another's vote unless the topology
   is `debate`. Run them concurrently.
3. **Temperature 0** for scoring judges; use `seed` when the provider supports it.
4. **Odd panel size** (3, 5, 7) so `majority` cannot deadlock.
5. **Never 1.0 confidence.** Cap at 0.99 — a panel is still a panel.

## Topologies (pick one)

| Topology | What judges see | Use when | Cost |
|---|---|---|---|
| **independent** | Only the candidate + rubric. Votes in parallel. | Default. Direct scoring or PASS/FAIL gates. Maximal bias-decorrelation. | N calls |
| **cross_ranking** | K **anonymized** candidates (labels stripped, order shuffled per judge) to rank. | Comparing/ranking K candidates; picking a tournament winner. Kills position + provenance bias. | N calls |
| **debate** | Round 1 independent, then each judge sees the *others'* anonymized rationales and may revise once. | High-stakes calls where a lone correct judge should be able to move the panel. | 2N calls |

Mechanics, exact prompt scaffolds, anonymization rules, and shuffle-seed handling:
[references/topologies.md](references/topologies.md).

## Aggregation (pick one)

| Aggregator | Rule | Use for | Guards |
|---|---|---|---|
| **majority** | Modal decision across judges. | Categorical verdicts (PASS/FAIL, winner id). | Odd N; ties → abstain/escalate. |
| **mean** | Arithmetic mean of scalar scores. | Well-behaved 1–5 rubrics, no outliers. | Sensitive to one rogue judge. |
| **median** | Middle score. | Default for scalars; robust to one outlier. | Even N → average the two middles. |
| **trimmed** | Drop top+bottom k, mean the rest. | N ≥ 5 with a known flaky judge. | Needs N ≥ 2k+1. |

Weighting (from calibration or caller-supplied), tie-breaking, and confidence-from-agreement
formulas: [references/aggregation.md](references/aggregation.md).

## Self-calibration ledger

A judge that is *consistently* wrong is worse than a noisy one. The panel keeps an append-only
**predicted-vs-realized ledger**: each judge's prediction is later paired with a realized
outcome (human label, market/PnL result, downstream test pass, or majority-of-a-larger-panel).
Over time this yields per-judge **reliability weights** and **bias offsets** that feed back into
aggregation, so drifting or sycophantic judges are automatically down-weighted.

Ledger schema, the de-biasing update rule, cold-start defaults, and how to (optionally) wrap
the user's MIT **`gepa`** crate to *evolve* judge prompts against the ledger's realized signal:
[references/self-calibration.md](references/self-calibration.md).

## Minimal usage

```
1. Build a PanelRequest: candidate + rubric + >=3 judges, topology=independent, aggregation=median.
2. Run each judge concurrently at temperature 0; parse JudgeVote (evidence, score, confidence).
3. Aggregate -> Verdict; compute agreement; attach every vote for audit.
4. (optional) Append (judge, prediction) rows to the ledger; reconcile when the realized
   outcome arrives; recompute reliability weights for next call.
```

Concrete request→verdict walkthroughs (a PASS/FAIL gate, a 4-way fusion tournament, a debate
that flips a majority): [references/examples.md](references/examples.md).

## Failure modes & edge cases

Empty/degenerate candidates, all-judges-abstain, tie storms, correlated judges (same base
model), self-enhancement when a judge grades its own family, position/length/verbosity bias,
malformed vote JSON, provider rate limits mid-panel, and ledger cold-start:
[references/failure-modes.md](references/failure-modes.md).

## Cross-links

- **`consciousness-council`** — human-facing deliberation for insight; call it when the goal is
  *understanding a trade-off*, not producing a score. judge-panel can score a council transcript.
- **`ce-advanced-evaluation`** — designs the *individual* judge (rubrics, scales, single-judge
  bias). Author judges there, then hand them to this panel.
- **`model-evaluation`** — statistical quant scoring (purged CV, PBO, deflated Sharpe). Use it
  for the realized-outcome side of the ledger when the candidate is a strategy.
- **`strategy-verify`** — end-to-end backtest verification vs a baseline.
- **`recursive-batch-eval`** / **`opik`** — the *harness* layer that loops this primitive over a
  dataset and logs traces; judge-panel is the per-item scorer they invoke.

## References

- [references/contract.md](references/contract.md) — full PanelRequest / JudgeVote / Verdict schema.
- [references/topologies.md](references/topologies.md) — independent, cross-ranking, debate mechanics + prompts.
- [references/aggregation.md](references/aggregation.md) — aggregators, weighting, tie-breaks, confidence.
- [references/self-calibration.md](references/self-calibration.md) — the ledger, de-biasing, `gepa` wrap.
- [references/failure-modes.md](references/failure-modes.md) — edge cases and boundaries.
- [references/examples.md](references/examples.md) — worked request→verdict walkthroughs.
