# SEGMENT & GATE (Loop-3 stage 2)

Between ingest and scan, do two cheap deterministic passes over each scrubbed
`TurnEvent[]`: **segment** it into phases, and **gate** out junk sessions before
any expensive scanning or LLM judging. Both are pure functions of the normalized
stream — no model calls.

Order matters: segment first (the gate reads phase labels), gate second (scanners
only ever see sessions that passed).

---

## 1. Phase segmentation → {Recon, Change, Validation, WrapUp}

Label each `TurnEvent` with a phase, then coalesce contiguous same-label runs into
**phase spans** `{phase, start_seq, end_seq, wall_ms, tokens}`. Phase is inferred
from tool + intent, not hard-coded per tool — the same tool can serve different
phases (a `Bash grep` is Recon; a `Bash pytest` is Validation).

| Phase          | Signals                                                              |
|----------------|---------------------------------------------------------------------|
| **Recon**      | `Read`, `Grep`, `Glob`, `WebFetch`, `ls`/`cat`/`grep`/`find` Bash, questions to the user, "let me look/understand/search". No mutation. |
| **Change**     | `Edit`, `Write`, mutating `Bash` (`git apply`, `mv`, `sed -i`, package installs), file-writing MCP tools. |
| **Validation** | test/build/lint/type-check runs (`pytest`, `cargo test/build`, `npm test`, `tsc`, `ruff`, CI-like Bash), and the assistant reading their results. |
| **WrapUp**     | final summary, `git commit`/`push`, PR creation, closing message with no further tool calls. |

Rules of thumb:
- A phase span starts when its label persists past a single event (one stray
  `Read` inside a Change run is not a new Recon span).
- Sessions cycle: Recon→Change→Validation→(back to Change)→WrapUp is normal.
  **Repeated** Change↔Validation bouncing without convergence is itself a signal
  the scanners key on — segmentation is what makes "6 failed Validation returns
  to Change" legible.
- Store phase on each `TurnEvent` AND as the coalesced span list; scanners use
  both (phase per event for filtering, spans for durations/cost).

**Why segment at all:** most scanners are phase-relative. A 3-message monologue
in **WrapUp** is a normal summary; the same in **Change** is a stuck agent. A
doom loop in **Validation** (re-running a failing test unchanged) is a different
anti-pattern than one in **Recon** (re-grepping the same term). Feeding scanners
raw, unsegmented streams produces both false positives (WrapUp monologue) and
false negatives (a Validation loop that looks like normal iteration).

---

## 2. Session-quality gate (min_score, default 0.3)

Score each session `session_quality ∈ [0,1]` from cheap structural signals, then
**drop sessions below `min_score` before scanning**. This filters stubs, aborted
runs, and empty shells so expensive scanning and (especially) any LLM-judged
step is spent only on sessions worth mining.

Additive score (clamp to `[0,1]`), all knobs:

| Signal (present ⇒ add)                                          | weight |
|----------------------------------------------------------------|--------|
| has a non-empty `goal_text`                                     | +0.20  |
| ≥ `min_events` real turns (default 6, excl. bookkeeping)       | +0.20  |
| reached at least the **Change** phase                          | +0.20  |
| reached **Validation** (agent tried to verify)                 | +0.15  |
| ≥ 1 successful `tool_result` (`ok=true`)                       | +0.15  |
| session ended cleanly (not an ingest-truncated fragment)       | +0.10  |

A session that is only a greeting, a single failed call, or a 2-line stub scores
< 0.3 and is gated out. A session that got a goal, made changes, and ran tests
scores ≥ 0.75 and is always mined.

**Do not silently drop.** Emit a gate summary — `sessions_in`, `sessions_gated`,
`gate_reasons` histogram, `min_score` used — into the run header so results are
reproducible and a mis-set threshold (gating half the corpus) is visible.

**Edge:** a session that *failed hard and fast* (agent refused on turn 2, then
nothing) may score low yet be exactly the failure you want. Guard: never gate a
session that trips the **refusal**, **error-cascade**, or **quarantine** signal
even if its quality score is low — route those to a `low_quality_but_flagged`
lane that still gets scanned. The gate removes *junk*, not *short failures*.

Both passes are versioned alongside the scanners: record `segmenter_version` and
`gate_version` (+ `min_score`, `min_events`) in the run header so a corpus
re-mined later is comparable.
