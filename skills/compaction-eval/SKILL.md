---
name: compaction-eval
version: 0.1.0
description: >-
  Replay a recorded agent session under several context-compaction policies and
  score task completion vs token budget, so a policy enters the harness only by
  winning a bake-off on a pinned session corpus (D13 eval class 7). Use when
  choosing or gating a Condenser strategy (none / keep-first+LLM-summarize /
  provider-native / token-prune), or on "which compaction policy should we use",
  "does compaction hurt solve rate", "measure tokens-per-task under
  summarization", "test keyed-context survival". Scores tokens-per-task incl. re-fetch,
  degradation-taxonomy thresholds, knowledge-retention and context
  precision/recall judges, an information-loss judge on summaries, and a
  keyed-entry-survival hard assertion. Do NOT use to author compression guidance
  (ce-context-compression) or diagnose one live degradation failure
  (ce-context-degradation), to score general session quality
  (agent-session-eval), or to grade a SKILL.md (skill-eval-runner) — it bakes
  off and gates compaction policies only.
---

# compaction-eval

Turn "we changed how the agent compacts its context" from a vibe into a
**gated experiment**. This skill owns exactly one thing: take a *recorded*
agent session, replay it under N compaction policies that all sit behind one
`Condenser` trait, and score whether each policy still finishes the downstream
task — measured in **tokens-per-task**, not raw tokens saved. A new compaction
policy enters the harness only after it wins this bake-off against the pinned
baseline on the pinned session corpus. This is the runner for **D13 eval class
7 (context use / compaction)**; it makes the guidance in `ce-context-compression`
and the failure taxonomy in `ce-context-degradation` measurable and enforceable.

The one idea that everything else follows from: **the optimization target is
tokens-per-task, including re-fetch cost — never raw tokens per request.** A
policy that halves the prompt but forces the agent to re-read three files it
already saw is *worse*, and this runner is built to catch exactly that.

## When to reach for this

- Choosing between compaction policies for the harness ("keep-first+summarize
  vs provider-native — which one?").
- Proving a new/tuned policy does not regress solve-rate before it ships.
- Measuring the token-budget win of compaction *net of re-fetch cost*.
- Asserting that keyed/managed context entries (skill catalog, VFS manifest,
  pinned facts) survive compaction — a hard, non-negotiable check.
- Feeding degraded-run transcripts back into the degradation taxonomy.

Do **not** reach for it to:

- Write or tune compression *strategy* guidance → `ce-context-compression`.
- Diagnose/mitigate one live degradation failure in a running agent →
  `ce-context-degradation`.
- Score general agent-session quality (task completion, tool correctness,
  coherence) with no compaction variable → `agent-session-eval`.
- Grade a `SKILL.md` against the frontier rubric → `skill-eval-runner`.

The distinction from `agent-session-eval` is sharp and load-bearing: that skill
varies the *agent* and holds context handling fixed; **this skill holds the
recorded session fixed and varies the compaction policy.** The session corpus,
the replay machinery, and the score-record shape are shared; the independent
variable is different.

## The bake-off in one pass

```
                    pinned recorded session (a .traj transcript)
                                     │
        ┌────────────┬──────────────┼──────────────┬─────────────────┐
        ▼            ▼               ▼              ▼                 ▼
   Condenser:    keep-first+     provider-       token-prune      (baseline =
     none        summarize        native         LLMLingua-2       whichever is
   (control)   (OpenHands-style) (lightspeed)    (P2, optional)    labelled prod)
        │            │               │              │                 │
        └────────────┴───── replay the SAME session under each ───────┘
                                     │
              per policy: re-drive the recorded turns, apply the
              condenser at its trigger, let the agent re-fetch if it
              must, run to the recorded goal
                                     │
                                     ▼
        score each run → tokens-per-task, solve-rate parity,
        degradation thresholds, retention/precision/recall judges,
        information-loss judge on summaries, keyed-entry survival
                                     │
                                     ▼
        GATE: a policy is admitted only if it beats baseline on the
        pinned corpus with variance-aware margins (see the gate ref)
```

Read the references in the order you need them:

- **`references/condenser-policies.md`** — the `Condenser` trait and the four
  concrete policies, with the *verified* donor APIs behind each: forge-code's
  `CompactionStrategy` Evict/Retain/Min/Max algebra, lightspeed's
  `CompactionPolicyInput` (Disabled / ProviderTriggered / ProviderStandalone),
  the OpenHands keep-first+summarize recipe, and the LLMLingua-2 token-prune
  candidate. Read first when adding or configuring a policy.
- **`references/session-corpus.md`** — how a recorded session is captured,
  scrubbed, pinned, split (Easy/Med/Hard), and deterministically *replayed*
  under a policy, plus probe injection for retention scoring. Read when building
  or extending the corpus.
- **`references/metrics-and-gates.md`** — every scored dimension defined
  precisely: tokens-per-task (with the re-fetch accounting that makes it
  honest), the five degradation-taxonomy thresholds, the judge set, the
  keyed-entry-survival hard assertion, and the OpenHands parity gate. Read
  before you assign or interpret a score.
- **`references/bakeoff-runner.md`** — the end-to-end run procedure, the
  `_llm_scores` record shape, the regression gate against a pinned baseline,
  and the anti-gaming meta-loop (information-loss judge on summaries; degraded
  transcripts routed to the degradation taxonomy). Read when wiring the gate
  into CI.

## The four policies (at a glance)

| Policy | What it does | Donor / source | Phase |
|---|---|---|---|
| **none** | No compaction — the control arm; establishes the quadratic-growth and solve-rate ceiling | — | P1 |
| **keep-first + LLM-summarize** | Keep the first K turns verbatim, LLM-summarize the truncated middle span | OpenHands recipe (keep_first=4, max_size=80) | P1 |
| **provider-native** | Delegate compaction to the provider's own context management | lightspeed `CompactionPolicyInput` | P1 |
| **token-prune** | Token-classification prompt compression (drop low-salience tokens) | LLMLingua-2, ONNX via ort/candle | P2 |

All four implement one `Condenser` trait so the runner treats them
interchangeably. The exact trait shape and how forge-code's Evict/Retain/Min/Max
algebra composes a policy are in `references/condenser-policies.md`.

## What "wins" means (the gate, condensed)

A candidate policy is admitted only if, on the pinned corpus versus the
baseline experiment (trials n≥3, variance-aware):

1. **Solve-rate parity** — downstream task completion drops by no more than the
   measured noise band (Δ ≤ noise). Saving tokens by failing the task is a loss.
2. **Token budget win** — per-turn tokens-per-task (incl. re-fetch) below the
   baseline, target < ½ of the `none` arm; context growth bends from quadratic
   toward linear.
3. **Keyed-entry survival (hard assertion)** — every managed/keyed context
   entry that was present pre-compaction is still resolvable post-compaction.
   This is a *hard fail*, never traded against a token win.
4. **No degradation-threshold breach** — the run does not cross any
   ce-context-degradation threshold (lost-in-middle / poisoning / distraction /
   confusion / clash) introduced by the compaction itself.

Full definitions, tolerances, and exit-code semantics live in
`references/metrics-and-gates.md` and `references/bakeoff-runner.md`.

## Boundaries

- **One independent variable: the compaction policy.** Model, tools, prompt,
  and the recorded session are pinned. If you are varying anything else, this is
  the wrong runner.
- **Recorded sessions only.** This replays a captured `.traj`; it does not
  generate fresh sessions. Corpus construction is its own step
  (`references/session-corpus.md`), and simulated-user session generation is
  `agent-session-eval`'s job.
- **Scores and gates; does not rewrite policies.** When a policy loses, tuning
  it is the harness author's job — this runner reports the loss with cited
  evidence and blocks the merge.
- **The gate is disjoint from the thing under test.** Per the class-7 meta-loop,
  a compaction policy can never edit its own gate or corpus; new policies enter
  only through the bake-off on the *pinned* corpus. This prevents a policy from
  being tuned to its own scorer.
- **Original content only.** This skill and its scripts are original work. Donor
  interfaces (lightspeed, forge-code — both Apache-2.0) are named for accuracy
  and reimplemented behaviorally; no code is copied, and nothing is taken from
  noncommercial, BUSL, AGPL, or proprietary sources.
