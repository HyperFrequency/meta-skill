# Topologies

A topology decides *what each judge sees and in what order*. It is the single biggest lever on
bias-decorrelation and cost. Pick one per call. All three consume the same `PanelRequest` and
emit the same `JudgeVote[]`; only the wiring between judges differs.

---

## 1. Independent (default)

Each judge sees only `candidate + task_context + rubric`. No judge sees any other judge's output.
Run all judges **concurrently** (bounded by `concurrency`).

- **Why it is the default:** independence is what makes a panel better than one judge. If judges
  can see each other, their errors correlate and the "panel" collapses toward a single opinion.
- **Use for:** direct scoring, PASS/FAIL gates, any single-candidate verdict.
- **Cost:** N judge calls.

Scoring-prompt scaffold (author the criteria via `ce-advanced-evaluation`; this is the wrapper):

```
You are one judge on a panel. Judge ONLY on the rubric. You cannot see other judges.

## Task the candidate must satisfy
{task_context}

## Candidate
{candidate.content}

## Rubric  (scale {min}-{max})
{for each criterion: name, description}

## Instructions
For EACH criterion, in this order:
  1. Quote/point to specific evidence in the candidate.   <-- required before scoring
  2. Give a score on the {min}-{max} scale.
  3. Justify the score from the evidence.
Then give an overall weighted score, a decision, and your confidence (0-1).

Output STRICT JSON matching the JudgeVote schema. Do not prefer longer or more confident-sounding text.
```

---

## 2. Anonymized cross-ranking

For K candidates. Each judge receives **all K candidates with identity stripped and order
shuffled per judge**, and returns a full ranking. This is the topology for tournaments and
"which of these is best" — it is dramatically more reliable than K independent absolute scores
because judges are good at *relative* comparison and bad at *absolute* calibration.

Anonymization + shuffle rules (these are the whole point — do not skip):

- **Strip provenance.** Remove model names, "Response A/B", author tags, and any watermark. Label
  candidates with neutral tokens (`X1`, `X2`, …) assigned *fresh per judge*.
- **Shuffle order per judge** using `hash(seed, judge_id)` so position bias averages out across the
  panel rather than compounding.
- **Record the permutation** so the judge's ranking over neutral labels can be mapped back to real
  candidate ids before aggregation.

```
You are one judge. Below are {K} candidate answers to the same task, in random order and
with all identifying information removed. Rank them best-to-worst on the rubric.

## Task
{task_context}
## Candidates
X1: {...}
X2: {...}
...
## Rubric ({min}-{max})
{criteria}

## Instructions
Evaluate each candidate independently first (evidence -> per-criterion score), THEN produce a
strict best-to-worst ranking of the labels. Do not favor a candidate for length or position.
Output STRICT JSON: per-candidate per_criterion evidence+scores, and a `ranking` of labels.
```

Rankings are aggregated by rank-based methods (Borda / Copeland / median rank) — see
aggregation.md. Pairwise position-swap (the classic 2-pass A/B from `ce-advanced-evaluation`) is
just the **K=2** special case of this topology; run both orders and require consistency.

---

## 3. Debate (two-round)

Round 1 is exactly **independent** — capture each judge's first, uncontaminated vote. Then, in
Round 2, each judge is shown the *other* judges' **anonymized rationales** (not their identities or
scores headline) and may revise its vote **once**.

- **Use for:** high-stakes decisions where a single judge who spotted a real flaw (a subtle
  hallucination, a security hole, a look-ahead bug in a strategy) should be able to *move* the
  panel that missed it. Debate lets correct minority evidence propagate.
- **Guardrail against herding:** show rationales, not scores/decisions, and forbid "I agree with
  judge 2" — a Round-2 revision must cite *new evidence or a corrected reading*, not social proof.
  Keep the Round-1 votes in the audit trail alongside Round-2.
- **Cost:** 2N calls. Only worth it when the decision is expensive to get wrong.

```
[Round 2]
You previously judged this candidate. Here are anonymized rationales from other judges.
You may REVISE your vote once, but ONLY if their evidence changes your reading of the CANDIDATE.
Do not change your vote merely because others disagree. If you revise, state exactly which new
evidence moved you. Output an updated JudgeVote (or your unchanged one).

## Your Round-1 vote
{your_vote}
## Other judges' rationales (anonymized, scores hidden)
{rationales}
```

Aggregation runs on the **Round-2** votes; `dissent` and `metadata` note who moved and why.

---

## Choosing

```
Single candidate, need a verdict/gate?          -> independent
Comparing / ranking K candidates?               -> cross_ranking (K=2 => position-swap pairwise)
High-stakes, want minority evidence to win?     -> debate  (else independent — debate costs 2x)
```

## Cross-topology invariants

- Judges are **independent within a round**. Never stream one judge's output into another's Round-1.
- Always run at `temperature: 0`; the diversity you want comes from *different models/prompts*,
  not from sampling noise.
- Every intermediate vote (Round-1 in debate, per-judge permutation in cross-ranking) is retained
  for audit — the Verdict must be reconstructible.
