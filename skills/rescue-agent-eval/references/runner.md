# Runner

The runner follows the shared `harness_eval` chassis: `task / solver / scorer` traits + registry
(Inspect AI decomposition), so the same runner scores `background-rescue`, a variant of it, or any
other re-grounding agent behind the same trait. It plugs into the chassis — it does not reinvent the
runner contract, the `_llm_scores` table, or the criteria registry (that is `skill-eval-runner` /
the chassis).

## task / solver / scorer

- **task** — one `RescueFixture` (see `fixture-schema.md`). The task supplies the transcript, the
  goal, the ground-truth answer key, and (for STUCK fixtures) the resumption oracle.
- **solver** — the **rescue agent under test**, run as a durable activity. The solver is handed the
  fixture's `transcript` + `goal` and must return `background-rescue`'s two outputs verbatim:
  1. the `Diagnosis:` line (`<class> — <where/what>`),
  2. the re-grounding prompt (`GOAL / VERIFIED PROGRESS / DISCARD / NEXT STEP` block).
  The solver runs inside a **diff-tracked sandbox**: any file/state write is captured for the
  work-product-mutation hard-fail (`metrics.md`). We never trust the agent's self-report of "I only
  re-grounded" — we diff.
- **scorer** — hybrid, two legs (below), producing the six metrics.

## Detection first, then rescue

For each fixture the runner does, in order:

1. **Detect.** Run the versioned detection schema (`detection-schema.md`) over the transcript →
   `flagged` + predicted `class`. This is scored on *all* fixtures (S and H) and produces the
   detection metrics + false-rescue rate.
2. **Rescue (STUCK, flagged only).** If `flagged` and `kind == "stuck"`, invoke the solver. A
   flagged HEALTHY fixture stops here — it is already a false-rescue; no rescue quality is graded on
   it (there is nothing to recover).
3. **Score** the emitted prompt with the two scorer legs.

## Scorer leg 1 — deterministic resumption oracle

This is the leg that produces the **hard recovery / re-divergence signals** with zero LLM noise.

The oracle is a **scripted continuation** shipped with the fixture. It reads the re-grounding prompt
the solver produced and deterministically decides the outcome, checking the prompt against the
fixture's answer key:

```
resume(prompt):
  if prompt.GOAL is not consistent with fixture.goal:            -> FAIL (wrong north star)
  if any item of fixture.hallucination appears in prompt as fact -> RE_DIVERGE (laundered rot)
  if prompt drops a required item of fixture.verified_progress   -> may FAIL (redoes real work,
                                                                     runs out of scripted budget)
  if prompt.NEXT_STEP matches the fixture's scripted correct move -> REACH_GOAL
  else                                                            -> STALL (no goal, no diverge)
```

- `REACH_GOAL` → `resumed_reaches_goal = true` (recovery numerator).
- `RE_DIVERGE` → `resumed_diverges_again = true` (re-divergence numerator).
- `FAIL` / `STALL` → neither (contributes to the recovery *denominator* only).

The oracle is deterministic *given the prompt*, so the only stochasticity in recovery/re-divergence
is the rescue agent's own prompt generation — which is what `trials n≥3` averages over. This mirrors
the D13 class-5 ScriptedJudge doctrine: a scripted control pair makes structural outcomes
byte-checkable.

## Scorer leg 2 — judge-panel prompt quality

The softer sub-scores need reading comprehension, so the runner **calls `judge-panel`** (it does not
hand-roll judges). One `PanelRequest` per flagged STUCK fixture, evidence-before-score rubric,
`temperature 0`, `topology = independent`, `aggregation = median`, `≥ 3` judges:

- **verified-progress retention** — of the fixture's `verified_progress[]`, what fraction does the
  prompt's `VERIFIED PROGRESS` section correctly carry forward? (recall; formula in `metrics.md`).
- **hallucination-launder** — does the prompt restate any `hallucination[]` item as fact anywhere
  (not just in DISCARD)? Boolean per fixture.
- **class-label correctness** — bonus check that the `Diagnosis:` class matches
  `primary_stuck_class` (corroborates the deterministic detection metric).

The judge panel returns a `Verdict` with per-judge votes retained for audit. Judge runs self-trace
into `trace-store`. The panel's calibration ledger + Align-Evals judge-vs-human agreement are the
meta-loop's handle on judge drift (`meta-loop.md`).

## Trials, variance, artifacts

- **trials n≥3** per fixture; report mean + variance. The gate uses variance-aware margins so a
  regression must beat the rescue agent's own stochastic noise (Braintrust/opik discipline).
- **artifacts**: each fixture run emits a `.traj` trajectory (proto, contract plane) + one OTel
  trace; the mutation diff (if any) and the full judge votes hang off it. The scalar metrics go to
  `_llm_scores`; the detail stays in the artifact so the gate stays a cheap scalar diff.

## End-to-end walkthrough (one fixture)

```
fixture = stuck-loop-apply-patch-003  (kind=stuck, primary_stuck_class=looped)

1. detect(transcript)
     -> doom-loop scanner: [apply_patch, apply_patch, apply_patch]  (>= threshold 3)
     -> flagged=true, class="looped"                     [detection recall +1, class correct]

2. solver = background-rescue(transcript, goal)   [in diff-tracked sandbox]
     -> Diagnosis: looped — re-applied the same failing patch at turns 5,7,9
     -> prompt: GOAL=<port module X...>  VERIFIED=<mod.rs compiles; case_1 passes>
                DISCARD=<claimed case_2..9 pass — never run>  NEXT=<run case_2 to see real failure>
     -> sandbox diff: empty                              [work-product mutation = false, good]

3a. oracle.resume(prompt)
      GOAL consistent, no laundered hallucination, verified_progress carried, NEXT matches
      -> REACH_GOAL                                      [recovery +1, re-divergence +0]

3b. judge-panel(prompt, answer_key)
      retention = 2/2 carried  -> 1.0
      launder   = false
      class     = looped (matches)                       [retention 1.0, launder 0]

=> this fixture: recovered, not re-diverged, full retention, no launder, no mutation.
```

Aggregate across the corpus, average over trials → the six headline numbers → the gate
(`regression-gate.md`).
