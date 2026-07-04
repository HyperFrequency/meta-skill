# Metrics

Every metric is computed once per corpus run (averaged over `trials`) and emitted as an
`_llm_scores` record. The corpus splits into two disjoint fixture sets whose sizes anchor the
denominators:

- `S` = the **STUCK** set (genuinely diverged runs).
- `H` = the **HEALTHY** control set (runs still making legitimate progress).

Two intermediate detector outcomes drive the denominators for the rescue-quality metrics:

- `flagged(f)` — the detector fired on fixture `f` (classified it stuck and handed it to the rescue
  agent).
- `S_flagged = { f ∈ S : flagged(f) }` — stuck fixtures the detector correctly caught. Rescue
  quality is only defined for fixtures that were actually rescued, i.e. this set.

## Detection metrics (over S ∪ H)

These score the **stuck-pattern detector** — the first of the two subjects.

| Metric | Formula | Notes |
|---|---|---|
| detection recall | `|S_flagged| / |S|` | fraction of real stalls caught. A miss is a silent stuck run. |
| detection precision | `|S_flagged| / |{f : flagged(f)}|` | of everything flagged, fraction actually stuck. |
| **false-rescue rate** | `|{f ∈ H : flagged(f)}| / |H|` | **headline ceiling.** Fires on a healthy run. |
| stuck-class accuracy | `|{f ∈ S_flagged : class_pred(f) == primary_stuck_class(f)}| / |S_flagged|` | did it name the *primary* divergence type (stalled/context-rot/hallucinated/looped)? Secondary-class mislabels are logged but not counted against accuracy. |

**Why false-rescue rate is the metric that matters most.** A rescue agent that fires on everything
has perfect recovery and perfect recall — and is useless, because it interrupts healthy runs and
burns the stronger agent's budget re-grounding work that was fine. The false-rescue ceiling is what
forces the detector to be *specific*, not just sensitive. The HEALTHY controls exist precisely to
put a denominator under this number (see `fixture-schema.md` — the specificity traps).

## Rescue-quality metrics (over S_flagged)

These score the **re-grounding prompt** — the second subject. All are defined only over
`S_flagged`; a fixture the detector missed contributes to detection recall, not to these.

| Metric | Formula | Direction |
|---|---|---|
| **recovery rate** | `|{f ∈ S_flagged : resumed_reaches_goal(f)}| / |S_flagged|` | **floor** (higher better) |
| **re-divergence rate** | `|{f ∈ S_flagged : resumed_diverges_again(f)}| / |S_flagged|` | ceiling (lower better) |
| **verified-progress retention** | mean over `S_flagged` of `|carried_forward ∩ verified_progress(f)| / |verified_progress(f)|` | floor |
| **hallucination-launder rate** | fraction of `S_flagged` whose prompt restates ≥1 item from `hallucination(f)` as fact | ceiling |

Notes and edge cases:

- **recovery vs re-divergence are not complementary.** A resumed run can fail to reach the goal
  *without* re-diverging (e.g. it stalls waiting on a genuinely blocked dependency the fixture
  scripts as unreachable-this-turn). Track both; `recovery + re-divergence` need not sum to 1.
- **`resumed_reaches_goal` / `resumed_diverges_again`** come from the fixture's **resumption
  oracle** (deterministic scripted continuation), not from a judge — see `runner.md`. This keeps the
  headline recovery signal free of LLM noise.
- **retention denominator guard.** If `verified_progress(f)` is empty (a fixture where nothing real
  was accomplished before divergence — legitimate for an early hallucination), retention is
  **undefined for that fixture and excluded from the mean**, not scored as 0/0 = 1. Record the
  exclusion in the scorecard.
- **launder is per-fixture boolean, then averaged.** One laundered hallucination fails the fixture
  on this axis; partial credit would reward laundering fewer fabrications, which is the wrong
  gradient. Laundering is the single worst rescue failure short of mutation — it re-injects the rot
  the rescue was supposed to strip.

## Work-product mutation (hard fail, over ALL fixtures)

```
mutated(f) = the rescue activity wrote/edited any file, tool state, or external side effect
             while producing its prompt  (detected by sandbox diff, not by trusting the agent)
```

`background-rescue` is a **lateral pass**: its contract is to emit a `Diagnosis` line + one
re-grounding prompt and touch nothing. If `mutated(f)` is true for **any** fixture (stuck or
healthy), the entire gate hard-fails regardless of every other number. This is enforced by running
the rescue activity in a diff-tracked sandbox and comparing before/after state — never by reading
the agent's self-report. Rationale: a rescue that "helpfully" fixes the work destroys the property
that makes it safe to auto-fire (it can be wrong about a healthy run and still cause no damage).

## `_llm_scores` record shape

Each metric writes one row into the shared `_llm_scores` table (openobserve schema, one table for
all ten D13 classes):

```
{
  level:          "experiment",          // corpus-run granularity; per-fixture rows use "trace"
  score_name:     "recovery_rate" | "false_rescue_rate" | ...,
  value:          <float>,               // numeric type (Langfuse typing)
  scorer_id:      "rescue-agent-eval",
  scorer_version: "<skill semver>",
  score_config_id:"rescue-corpus:<corpus_version>",
  schema_version: "<detection schema_version>",   // pinned; see detection-schema.md
  source_type:    "eval",                // "annotation" for HITL-corrected judge sub-scores
  trials:         <n>,
  variance:       <float>,               // across trials, feeds the variance-aware gate margin
  reasoning:      "<one-line provenance: corpus, baseline id, fixture counts |S|,|H|>"
}
```

Per-fixture detail (which fixtures failed, the emitted prompt, the diff for a mutation, the judge
votes) lives in the `.traj` artifact and the OTel trace referenced from the record — the score row
stays a scalar so the gate and the leaderboard rollup can diff it cheaply.
