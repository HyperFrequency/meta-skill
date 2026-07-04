# Trajectory-detection composite (behavioral spec)

The "trajectory detection" the autoresearch spec (§ a.7) names is a **two-stage
cheap first-pass** over a recorded session: **phase segmentation** followed by a
**session-quality gate**. It runs *before* any expensive LLM judging so that
low-value sessions are filtered out early. It feeds D12 loop-3 and is the cheap
pre-gate for D13 classes 3 (agent/session) and 7 (context/compaction). Clean-room
behavioral description; re-derive.

## Stage 1 — phase segmentation

A session is a sequence of messages/tool-calls. Segmentation classifies each
message into one of four **session phases** and coalesces contiguous same-phase
messages into `SessionSegment`s, producing a `SegmentedSession`:

| Phase | Meaning | Signals used to classify |
|---|---|---|
| **Reconnaissance** | understanding the problem, reading code | read/grep/list tools; exploratory bash (`ls`, `cat`, `find`, `grep`) |
| **Change** | editing, writing, applying patches | edit/write tools; `apply_patch`; file mutation |
| **Validation** | running tests, verifying it works | test/build commands; `cargo test`, `pytest`, `npm test`, lints |
| **WrapUp** | committing, cleanup, final summary | `git commit`/`git push`; summary/closing messages |

Behavioral rules the reimplementation must honor:

- The **first message initializes** the current phase (do **not** default the
  whole session to Reconnaissance) — a session that opens mid-edit starts in
  Change.
- Bash commands are classified by inspecting the command string
  (`classify_bash_command`): WrapUp indicators (commit/push) are checked before
  Validation indicators (test/build) before Change/Recon.
- A **phase transition** starts a new segment; the first message is not
  double-counted as a transition.
- `SegmentedSession` exposes `segments_for_phase(phase)` and a
  `dominant_phase()` (the phase holding the most messages) — the latter is a
  cheap session-shape feature (e.g. a session that is 90% Reconnaissance never
  reached Change, a strong "abandoned exploration" tell).

Phase segmentation is also the substrate for pattern *extraction* — the mining
layer classifies extracted patterns by `PatternType` (command-sequence, code,
workflow, decision, error-handling, refactoring, configuration, tool-usage),
each carrying evidence, an observation count, and a confidence.

## Stage 2 — session-quality gate

A `QualityScorer` (configured by `QualityConfig`) produces a `SessionQuality`
{ normalized `score ∈ [0,1]`, contributing `signals`, `missing_signals`,
computed-at timestamp }. A session **passes** iff `score >= min_score`.

### Default configuration (parity constants)

```
min_score              = 0.3    # gate cutoff
min_turns              = 3      # shorter → penalized as "too short"
max_turns              = 500    # longer  → penalized as "excessively long" (thrash)
require_code_changes   = false

# positive signal weights
weight_tests_passed    = 0.25
weight_clear_resolution= 0.25
weight_code_changes    = 0.15
weight_user_confirmed  = 0.15

# negative penalties
penalty_backtracking   = 0.10
penalty_abandoned      = 0.20
```

Scoring is additive-with-penalties: sum the positive signal weights that are
present, subtract `penalty_backtracking` for backtracking evidence and
`penalty_abandoned` for an abandoned session, then normalize/clamp into `[0,1]`.
Sessions with **excessive turns** (`> max_turns`) are treated as thrashing;
sessions with **too few turns** (`< min_turns`) are too short to be meaningful.

### Missing-signal reporting (`MissingSignal`)

Rather than only a scalar, the scorer names *why* a session scored low so a
reviewer (or loop-4) can act:

- **NoTests** — no test execution/results found.
- **NoUserConfirmation** — no explicit user "that worked".
- **NoResolution** — no clear resolution marker at the end.
- **NoCodeChanges** — nothing was actually edited.
- **TooShort** — below `min_turns`.
- **TooLong** — above `max_turns` (thrash suspicion).

A human-readable **grade band** is derived from the score: `>=0.8` excellent,
`>=0.6` good, `>=0.4` fair, `>=0.2` poor, else very-poor — used only for display,
never for gating (the gate is the numeric `min_score`).

## Why the composite matters (neuro-centrifuge wiring)

- **Cost control.** LLM-judge passes (D13) are expensive; running the composite
  first drops junk (abandoned / no-resolution / thrash) sessions so only
  representative trajectories reach a judge panel.
- **Loop-3 input.** Segmented, quality-passed sessions are the unit the
  anti-pattern miner clusters over; the phase labels sharpen "failed-action
  similarity" clustering.
- **Class 3/7 realism check.** The composite validates that a session being used
  as an eval fixture is *representative* (reached Validation, has a resolution)
  before it is promoted into a dataset via trace→dataset promotion.
- **Guided mining (P2).** Low-confidence findings feed an `UncertaintyQueue`
  that generates 3–7 targeted human questions — the HITL loop-3 interview step.

The composite is deterministic (pure function of the session log) — no clock or
network — so its outputs are reproducible and themselves gateable.
