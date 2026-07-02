# Topologies

A topology decides *what each judge sees and in what order*. It is the single biggest lever on
bias-decorrelation and cost. Pick one per call. All five consume the same `PanelRequest` and emit
the same `JudgeVote[]` (plus, for `council`, a synthesized answer); only the wiring between judges
differs. Anonymized cross-ranking is not a separate topology — it is a *mechanism* (label-strip +
per-judge shuffle) reused inside `council` and inside any K-way tournament; its rules are in
[Anonymized cross-ranking](#anonymized-cross-ranking-mechanism) below.

Lineage: `independent` and `debate` are Du et al. 2023 ("Improving Factuality and Reasoning in
Language Models through Multiagent Debate" — round-1 parallel, then peers-read-and-update rounds);
`chateval` is Chan et al. 2023 (communicative multi-agent debate for evaluation); `council` is
karpathy/llm-council; `hierarchical` is episteme's `JudgePool` hierarchical mode.

---

## 1. Independent (default)

Each judge sees only `candidate + task_context + rubric`. No judge sees any other judge's output.
Run all judges **concurrently** (bounded by `concurrency`). This is Du et al.'s round 1 used as a
terminal answer.

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

## 2. Debate (R rounds, Du et al.)

Round 1 is exactly **independent** — capture each judge's first, uncontaminated vote. Then, for
`R` further rounds (default R=1), each judge is shown the *other* judges' **anonymized rationales**
(not identities, not headline scores) and may revise its vote. Iterate until votes stabilize or `R`
is exhausted. Du et al. find agreement and factuality improve over 2-3 rounds, then plateau.

- **Use for:** high-stakes decisions where a single judge who spotted a real flaw (a subtle
  hallucination, a security hole, a look-ahead bug in a strategy) should be able to *move* the
  panel that missed it. Debate lets correct minority evidence propagate.
- **Guardrail against herding:** show rationales, not scores/decisions, and forbid "I agree with
  judge 2" — a revision must cite *new evidence or a corrected reading*, not social proof. Keep
  every round's votes in the audit trail.
- **Convergence & cost:** stop early when the max per-judge score delta across a round falls below
  `debate.epsilon` (default 0.25 on a 1-5 scale). Cost is `(R+1)·N` calls; only worth it when the
  decision is expensive to get wrong.

```
[Round r]
You previously judged this candidate. Here are anonymized rationales from other judges.
You may REVISE your vote, but ONLY if their evidence changes your reading of the CANDIDATE.
Do not change your vote merely because others disagree. If you revise, state exactly which new
evidence moved you. Output an updated JudgeVote (or your unchanged one).

## Your previous-round vote
{your_vote}
## Other judges' rationales (anonymized, scores hidden)
{rationales}
```

Aggregation runs on the **final-round** votes; `dissent` and `metadata.moved[]` note who moved and
why. Track a per-judge **herding penalty** in the ledger (self-calibration.md): a judge that flips
*toward* the majority and is later realized *wrong* gets down-weighted in debate.

---

## 3. ChatEval (communicative debate, Chan et al.)

Judges hold a *conversation* rather than voting in isolation. Three communication schemes, chosen
by `chateval.mode`:

- **one-by-one** (sequential): judge 1 speaks, judge 2 sees judge 1 and speaks, … . Order matters;
  rotate the speaking order across candidates to average out primacy/recency.
- **simultaneous**: all judges speak each round seeing only the *previous* round's messages (not
  within-round), for `R` rounds. Reduces order bias vs one-by-one.
- **simultaneous + summarizer**: as above, but a dedicated **summarizer** condenses the debate each
  round so the context stays bounded; the final summary feeds the vote.

Each judge carries a **persona/role** (e.g. "general public", "critic", "domain expert") to force
diverse angles — the diversity ChatEval relies on comes from *roles*, not sampling. After the
conversation, each judge emits a normal evidence-before-score `JudgeVote`; aggregate as usual.

- **Use for:** nuanced qualitative rubrics (open-ended generation quality, helpfulness) where
  cross-talk surfaces considerations a lone judge misses.
- **Cost:** `R·N` (+1 per round if a summarizer runs). More expensive and *less* decorrelated than
  `independent` — do not use it for a simple gate.

```
[ChatEval turn — role: {persona}, round {r}/{R}, mode: {mode}]
You are debating the quality of the candidate with other judges. Your assigned perspective: {persona}.
## Task
{task_context}
## Candidate
{candidate.content}
## Debate so far ({mode}: prior turns / prior-round summary)
{transcript_or_summary}
Contribute ONE substantive turn: raise or rebut a specific, evidence-cited point about the CANDIDATE
(not about other judges). At the FINAL round, additionally output your JudgeVote.
```

---

## 4. Council (3-stage, karpathy/llm-council)

For K candidates *and* a synthesized answer. Three stages:

1. **First opinions** — each council member answers/scores the task **privately and in parallel**
   (an `independent` round). Uncontaminated.
2. **Anonymized cross-review + rank** — each member receives *all* members' stage-1 outputs with
   identities stripped and neutral labels (`Response A/B/…`), evaluates each, and returns a
   best-to-worst **ranking**. Anonymization is the **anti-sycophancy keeper**: a member cannot
   defer to a high-status model because it does not know which response is whose (nor favor its own).
3. **Chairman synthesis** — a designated `chairman` model reads the stage-1 responses and the
   stage-2 rankings and writes one final answer representing the council's collective judgment.

- **Use for:** producing a *single best answer* from a panel while also getting a ranking — the
  fusion-judging case. Distinct from `consciousness-council`, which is human-facing insight, not a
  synthesized deliverable + rank.
- **Verdict:** `decision` = the aggregated ranking's winner (rank stage-2 via Borda/median-rank,
  see aggregation.md); `metadata.synthesis` = the chairman's answer; every stage retained for audit.
- **Cost:** `2N + 1` calls (stage 1 + stage 2 + chairman).

The stage-2 ranking prompt and label mapping follow the anonymized cross-ranking mechanism below.

---

## 5. Hierarchical (cheap-first escalation, episteme)

Run the **cheapest** judge first. If its score falls *inside* the configured `uncertain_range`
(episteme default `(0.4, 0.7)` on a 0-1 scale), the item is ambiguous → **escalate** to the full
ensemble and aggregate normally. If the cheap score is outside the range (confidently high or low),
return it as a single-judge verdict with high confidence and skip the panel.

- **Why:** most items in a large stream are easy; paying for N judges on every one is wasteful.
  Hierarchical spends the panel budget only on the hard tail near the decision boundary.
- **Use for:** cost control at scale (screening thousands of candidates, a cheap pre-filter before
  an expensive gate).
- **Tuning:** widen `uncertain_range` to escalate more (higher quality, higher cost); narrow it to
  escalate less. Calibrate the range from the ledger: it should bracket the score band where the
  cheap judge's realized accuracy drops.
- **Cost:** 1 call on the easy majority, N on the uncertain tail. Report `metadata.escalated: bool`.

```
Hierarchical control flow:
  s = cheap_judge(candidate)
  if s < uncertain_low or s > uncertain_high:
      return single_verdict(s, confidence=High, escalated=False)
  else:
      return ensemble_verdict(full_panel(candidate), escalated=True)
```

Guard: never let a *systematically* miscalibrated cheap judge gate escalation — if its bias offset
(self-calibration.md) is large, subtract it before the range check, or the panel silently rubber-
stamps the cheap judge's error on the easy band.

---

## Anonymized cross-ranking (mechanism)

Used by `council` stage 2 and by any K-way tournament. Each judge receives **all K candidates with
identity stripped and order shuffled per judge**, and returns a full ranking. This is dramatically
more reliable than K independent absolute scores because judges are good at *relative* comparison
and bad at *absolute* calibration.

Rules (these are the whole point — do not skip):

- **Strip provenance.** Remove model names, "Response A/B" real mapping, author tags, watermarks.
  Label candidates with neutral tokens (`X1`, `X2`, …) assigned *fresh per judge*.
- **Shuffle order per judge** using `hash(seed, judge_id)` so position bias averages out across the
  panel rather than compounding.
- **Record the permutation** so each judge's ranking over neutral labels maps back to real ids
  before aggregation.

```
You are one judge. Below are {K} candidate answers to the same task, in random order and with all
identifying information removed. Rank them best-to-worst on the rubric.

## Task
{task_context}
## Candidates
X1: {...}
X2: {...}
## Rubric ({min}-{max})
{criteria}

## Instructions
Evaluate each candidate independently first (evidence -> per-criterion score), THEN produce a strict
best-to-worst ranking of the labels. Do not favor a candidate for length or position.
Output STRICT JSON: per-candidate per_criterion evidence+scores, and a `ranking` of labels.
```

Rankings are aggregated by rank-based methods (Borda / Copeland / median rank) — see
aggregation.md. Pairwise position-swap (the classic 2-pass A/B from `ce-advanced-evaluation`) is the
**K=2** special case; run both orders and require consistency.

---

## Choosing

```
Single candidate, need a verdict/gate?               -> independent
Comparing / ranking K candidates?                    -> cross-ranking mechanism (K=2 => position-swap)
High-stakes, want minority evidence to win?          -> debate  (R rounds; else independent — 2x+ cost)
Nuanced qualitative quality, want cross-talk?         -> chateval (role-diverse; costly)
Want ONE synthesized answer + a ranking?             -> council (3-stage, anonymized stage 2)
Large stream, most items easy, cap cost?             -> hierarchical (cheap -> escalate if uncertain)
```

## Cross-topology invariants

- Judges are **independent within round 1**. Never stream one judge's output into another's round-1.
- Always run at `temperature: 0`; the diversity you want comes from *different models / prompts /
  roles*, not from sampling noise.
- Every intermediate artifact (each debate/ChatEval round, per-judge permutation in cross-ranking,
  the council chairman's inputs) is retained for audit — the Verdict must be reconstructible.
