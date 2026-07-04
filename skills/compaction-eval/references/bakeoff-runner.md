# Bake-off runner & meta-loop

The end-to-end procedure: how a bake-off is run, how the regression gate turns
it into a merge decision, and the anti-gaming meta-loop that keeps the whole
thing from being gamed by the policy under test.

## The run, start to finish

```
1. PIN        Freeze the run manifest: {corpus_version, baseline_policy,
              candidate_policies[], replay_mode, trials n>=3, seeds}.
              Hash it. Every _llm_scores row records these pins.

2. REPLAY     For each policy P in {baseline} ∪ candidates:
                for each session S in corpus (respecting held-out split):
                  for trial in 1..n:
                    replay S under P (see session-corpus.md replay modes),
                    emitting a CompactionRecord per compaction event and one
                    .traj + one OTel trace per run.

3. SCORE      For each run:
                deterministic first — tokens-per-task, per-turn cost, growth
                exponent, keyed-entry survival probe, degradation-threshold
                checks, retention probes;
                then judges — retention, context precision/recall,
                information-loss on summaries (metrics-and-gates.md).
              Write every quantity to _llm_scores with pins.

4. AGGREGATE  Per policy: mean + variance across trials and sessions, split by
              difficulty tier (Easy/Med/Hard). Variance is not optional — it is
              what separates a real regression from LLM noise.

5. GATE       Compare each candidate to the baseline experiment on the SAME
              corpus_version with variance-aware margins (see below). Emit a
              pass/fail per candidate + a scorecard.

6. FEEDBACK   Route degraded transcripts to the loop-3 degradation taxonomy;
              route summary information-loss findings to ce-context-compression
              gotchas. (meta-loop, below.)
```

## Regression gate mechanics

The gate is candidate-vs-baseline on a pinned dataset version — never an
absolute threshold in isolation, because "good tokens-per-task" only means
something relative to the `none` arm and the current prod policy.

- **Baseline = the labelled `prod` policy** (or `none` for a first bake-off).
  The candidate must *beat or match* it; a tie does not flip the label.
- **Variance-aware margin.** With n≥3 trials, a candidate only "wins" a metric
  if its advantage exceeds the combined trial variance (Braintrust/opik
  discipline). A 3% token win inside a 5% noise band is not a win.
- **Hard breaches short-circuit.** Any failed hard assertion (solve-rate parity,
  keyed-entry survival, token budget, degradation breach — see
  `metrics-and-gates.md`) fails the candidate immediately; judge floors are
  evaluated only on candidates that clear the hard gates.
- **Held-out split decides.** Tuning may use the visible split; the *gate* runs
  on the held-out split. A candidate that wins only on the visible split is
  rejected as overfit to the corpus.

**Exit codes** (for CI wiring, mirroring `skill-eval-runner`'s gate):

- `0` — candidate admitted (beats/matches baseline within margin on the held-out
  split, no hard breach, judge floors clear).
- `1` — candidate rejected (a hard breach, a variance-aware regression, or a
  judge floor miss). The scorecard names the failing dimension with cited
  evidence.

A rejected policy is reported, not rewritten — tuning it is the harness author's
job. The runner's contract ends at the gated scorecard.

## The label flip

Admitting a candidate is a **deployment-label move** (Langfuse-style): the
candidate becomes the new `prod` compaction policy only after a green gate on the
held-out split. CI blocks the label move on a red gate. The prior `prod` policy's
scorecard is retained as the new baseline reference so the next bake-off has a
pinned point of comparison.

## Anti-gaming meta-loop

Per the class-7 spec, the eval must not be gameable by the thing it evaluates.
Three disjointness rules enforce this:

- **The policy cannot edit its own gate or corpus.** Scorer criteria, the
  degradation-threshold schema, and the session corpus are versioned registry
  entities with **write scope disjoint** from the compaction policies under test
  (the swe-loop disjoint-write-scope pattern; `ce-harness-engineering` surface
  locks). A policy author changes the `Condenser` impl and the run manifest —
  never the scorer or the pinned corpus.
- **New policies enter only via the bake-off on the pinned corpus.** There is no
  side door. A policy that has not won a bake-off on the current pinned corpus
  version is not in the harness.
- **Judges are calibrated, not trusted.** The retention / precision / recall /
  information-loss judges are themselves regression-gated: judge-vs-human
  agreement from HITL corrections is a tracked metric (Align-Evals), and a
  judge-prompt change requires a criteria-version bump gated on a held-out
  calibration set. The loop that might want to loosen a judge can never loosen
  its own.

## Two feedback edges (the loop closes)

The bake-off is not a dead-end scorer; it feeds two upstream loops:

- **Degraded transcripts → degradation taxonomy (loop 3).** Any run that
  crosses a degradation threshold *because of* compaction is promoted into the
  loop-3 evidence set. If a new failure mode recurs, it justifies a
  degradation-threshold schema version bump — and, per `session-corpus.md`, the
  transcript becomes a new Hard-tier corpus fixture. The next policy must survive
  the failure this one caused.
- **Information-loss findings → compaction guidance.** Systematic summary
  failures the information-loss judge surfaces (e.g. a policy that reliably drops
  modified-file references) are the empirical backing for
  `ce-context-compression`'s gotchas. Guidance stays grounded in what the
  bake-off actually measured, not in intuition.

## Where this sits among the runners

- **`compaction-eval`** (this) — holds the recorded session fixed, varies the
  **compaction policy**. D13 class 7.
- **`agent-session-eval`** — holds context handling fixed, varies the **agent**;
  scores general session quality (task completion, tool correctness, coherence)
  over recorded + simulated-user sessions. D13 class 3. Shares the corpus, replay
  machinery, and `_llm_scores` shape with this skill.
- **`skill-eval-runner`** — scores a **`SKILL.md`** against the frontier rubric
  and gates CI. D13 class 1. Different subject entirely; shares only the
  gate-and-baseline discipline and the "one hard breach fails" rule.

Reach across these by subject: *what am I varying?* If it is the compaction
policy, you are in the right place.
