# Metrics & gates

Every dimension the bake-off scores, defined precisely enough to be
reproducible. The governing principle from `ce-context-compression`: **the
optimization target is tokens-per-task, never raw tokens per request.** A policy
that shrinks the prompt but degrades the task loses.

## 1. Tokens-per-task (incl. re-fetch) — the primary metric

Not "tokens in the compacted prompt." The **total tokens consumed to complete
the task**, summed across all turns of the replayed run, *including the tokens
spent re-fetching information a lossy compaction discarded*.

```
tokens_per_task = Σ_turns (prompt_tokens + completion_tokens)
                  over the full replayed run to the completion oracle
```

Why re-fetch is the whole point: a policy can report a beautiful per-request
token reduction and still cost *more* end-to-end because the agent has to
re-read three files it already saw. The only way this shows up is the **live
re-drive** replay mode (see `session-corpus.md`), where re-fetch tool calls
actually happen and their tokens land in the sum. Report tokens-per-task as the
headline; report per-request tokens only as a secondary diagnostic.

Two derived curves accompany it:

- **Per-turn cost.** Target from the OpenHands methodology: a shipping policy's
  per-turn cost is **< ½** the `none` control arm.
- **Context-growth shape.** The `none` arm grows quadratically (every turn
  re-sends the whole history); a good policy bends this toward **linear**. Fit
  and report the growth exponent — "linear-vs-quadratic" is a gate signal, not a
  vibe.

## 2. Solve-rate parity — the hard ceiling

Downstream task completion, measured by the session's **ground-truth oracle**
(not a judge). A candidate policy's solve-rate must not drop below baseline by
more than the measured noise band:

```
solve_rate(candidate) >= solve_rate(baseline) - noise_band
```

`noise_band` comes from the variance of n≥3 trials on the same corpus version.
Saving tokens by failing tasks is a **loss**, full stop. This is why `none` is a
mandatory arm: it fixes the achievable ceiling so "parity" means something.

## 3. Keyed-entry survival — a HARD assertion

Every managed/keyed context entry present pre-compaction must be resolvable
post-compaction. This is a **hard fail**, never traded against a token win.

Mechanics: each keyed entry carries a stable `key` (lightspeed
`ContextAppendEntry`). After `condenser.compact(...)`, independently verify —
do **not** trust the condenser's self-reported preserved set — that every key in
`protected_keys` still resolves to its content:

```
for key in protected_keys:
    assert resolves_post_compaction(key), f"keyed entry {key} lost to compaction"
```

Protected keys are the skill catalog, VFS/snapshot manifests, and any pinned
facts the harness marked managed. The whole reason lightspeed models context as
keyed entries is so compaction is *survivable* by design; this assertion proves
the property empirically per policy. A policy that drops a keyed entry is
disqualified regardless of every other score.

## 4. Degradation-taxonomy thresholds

Compaction must not *introduce* a context-degradation failure. Score the
post-compaction run against the five patterns from `ce-context-degradation`,
each with a versioned threshold (the taxonomy is a criteria schema, versioned):

| Pattern | Compaction-induced signal to watch |
|---|---|
| **Lost-in-middle** | Summary buries a critical fact mid-block; probe recall drops on U-curve middle |
| **Poisoning** | A hallucinated or wrong claim enters *via the summary* and then compounds |
| **Distraction** | Summary retains irrelevant spans that dilute the live task |
| **Confusion** | Summary merges two task phases so wrong-phase constraints/tools bleed in |
| **Clash** | Summary flattens two contradictory sources into one, hiding the conflict |

Crossing any threshold that the *compaction itself* caused (i.e. absent in the
`none` arm) is a gate breach. Degraded transcripts are not just failures — they
are **routed back to the loop-3 degradation-taxonomy** as new evidence, which
may bump the threshold schema (see `bakeoff-runner.md`).

## 5. Judge set (model-graded, evidence-before-score)

Deterministic checks first; judges only where reading comprehension is
unavoidable. All judges emit the evidence-before-score JSON shape (reasoning,
then score) and are themselves calibrated per the class-7 meta-loop.

- **Knowledge-retention judge.** Corroborates the deterministic probe results
  (from `session-corpus.md`): does the compacted run retain the specific facts,
  decisions, and artifact references the probes target? Probes give the number;
  the judge explains and catches probe gaps.
- **Context precision / recall judges.** Of what the compacted context retained,
  how much was relevant (precision); of what was relevant in the original, how
  much survived (recall). A high-precision/low-recall policy is over-compacting;
  low-precision/high-recall is barely compacting.
- **Information-loss judge (on the summary artifact).** The summary a
  keep-first+summarize policy produces is *itself* graded: does it preserve the
  mandatory sections (intent, files modified, decisions, risks, next steps)
  without silent drops or hallucinated additions? A summary that reads well but
  loses a modified-file reference passes a shallow probe and **fails this
  judge** — this is the check that catches false-confidence summaries.

## The gate (composite)

A candidate policy is **admitted** only if, versus the labelled baseline
experiment on the *same* pinned corpus version, with n≥3 trials and
variance-aware margins:

1. **Solve-rate parity** — Δ ≤ noise band (metric 2). *Hard.*
2. **Keyed-entry survival** — all protected keys resolve post-compaction
   (metric 3). *Hard, no trade.*
3. **Token budget win** — tokens-per-task below baseline; per-turn cost < ½ the
   `none` arm; growth bends toward linear (metric 1). *Hard.*
4. **No compaction-induced degradation breach** — metric 4. *Hard.*
5. **Judge floors** — retention / precision / recall / information-loss judges
   clear their calibrated floors (metric 5). *Soft-but-gated:* a judge miss
   blocks admission but is reviewed, not auto-failed, because judges carry
   noise.

No averaging across dimensions — a single hard breach disqualifies the policy,
mirroring the frontier-rubric "one 3 fails" discipline that `skill-eval-runner`
enforces for skills. Exit-code semantics and the baseline-diff mechanics are in
`bakeoff-runner.md`.

## Score record shape

Every scored quantity is written to the shared `_llm_scores` table (the same
one all ten D13 classes use), so a compaction score is queryable alongside every
other eval:

```
_llm_scores {
    level:          span | trace | session | experiment,
    value:          numeric | categorical | boolean,
    scorer_id:      e.g. "compaction.tokens_per_task" / "compaction.keyed_survival",
    scorer_version: pinned,
    source_type:    "eval",
    policy_id:      the Condenser id under test,
    policy_version: pinned,
    corpus_version: pinned,
    reasoning:      evidence-before-score text (for judged rows),
}
```

Pinning `policy_version` **and** `corpus_version` on every row is what lets a
past win stay interpretable after either the policy or the corpus moves.
