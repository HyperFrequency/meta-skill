# Anti-pattern mining (behavioral spec)

The anti-pattern subsystem turns **failure evidence** observed in agent/coding
sessions into versioned, reviewable **negative rules** ("NEVER do X when Y").
It is the backbone of D12 loop-3 (trajectory & anti-pattern analysis) and the
schema for the HITL anti-pattern review surface. Clean-room: behaviors and
constants below are the parity targets; re-derive, do not copy.

## Data model

An **AntiPattern** carries:

- a unique id (generatable);
- a `NegativeRule` — the synthesized "do not" statement plus the **conditions**
  under which it applies and the **consequence** (what goes wrong when violated);
- a **link to the positive pattern it constrains** — an anti-pattern with no
  positive counterpart is *orphaned* and flagged as such (orphans are a lint
  finding, not silently kept);
- a list of **evidence** items;
- a **confidence** in `[0.0, 1.0]`;
- categorization **tags**;
- `first_detected` / `last_updated` timestamps.

Each **AntiPatternEvidence** item records its **source**, the session id it came
from, the specific failure/correction incident, optional user-supplied context,
and a collection timestamp.

### Evidence sources (`AntiPatternSource`)

1. **Explicit marker** — the session was tagged by a human (e.g. "anti-pattern",
   "wrong approach"); the marker string is retained.
2. **Rollback** — detected from an undo sequence; carries a `RollbackType`
   (`git reset`, `git revert`, file-restore, manual undo, or an explicit
   in-conversation correction).
3. **Wrong-then-corrected** — an original (wrong) action paired with the
   correction that replaced it.
4. **Failure signal** — a `FailureSignalType` in the session (test failure,
   build/compile error, runtime exception/crash, and similar).
5. **Uncertainty counter-example** — surfaced while resolving an item on the
   uncertainty queue (active-learning path, P2).

## Confidence formula (parity-critical)

Confidence is recomputed every time evidence is added, from two terms:

```
base       = min( n / (n + 2), 0.9 )          # n = evidence count
confidence = min( base + diversity_bonus, 1.0 )
```

- `n/(n+2)` is a saturating count curve: 1 item → 0.33, 2 → 0.50, 3 → 0.60,
  5 → 0.71, capped at **0.9** so evidence count alone can never assert certainty.
- **diversity_bonus** rewards evidence drawn from *distinct source types* (a
  rollback + a failure signal + an explicit marker is stronger than three
  rollbacks). Count unique `AntiPatternSource` variants, not raw items.
- Zero evidence ⇒ confidence 0.0. Adding evidence is **monotone non-decreasing**
  (an invariant the reimplementation must preserve).

Severity is a separate axis (floors per rule class) — confidence measures *how
sure*, severity measures *how bad*. Blocking-severity findings require explicit
user confirmation before they gate anything (never auto-applied).

## Detection pipeline

A `DefaultDetector` (implementing an `AntiPatternDetector` trait) scans a
structured session and emits `AntiPatternSignal`s, each with a **context window**
(summarized messages and actions around the signal) so reviewers see evidence in
situ. It carries a **minimum confidence threshold** below which signals are
dropped. Detection covers:

- **Marked anti-patterns** — extract the human annotation and the flagged span.
- **Rollback sequences** — recognize `git reset`/`git revert`, backup restores,
  and manual undos; classify the `RollbackType`.
- **Corrections** — locate a wrong action followed by its fix in the trailing
  context window; compute a per-correction confidence.
- **Failure signals in messages and tool results** — test/build/runtime failures.
- A **read-only-tool guard** so that inspecting code (read/grep) is never itself
  scored as a failing action.

Content is truncated **UTF-8-safely** (character-aware) when summarized, so
multi-byte content never panics the summarizer.

Detected signals, rollbacks, and corrections are converted into
`AntiPatternEvidence` (`signals_to_evidence`, `rollbacks_to_evidence`,
`corrections_to_evidence`) and attached to (new or existing) anti-patterns,
which recomputes confidence.

## Mining pipeline (5 stages)

Over a batch of sessions (sourced through a `SessionSource` abstraction so the
harness's own OTel/LLM logs replace the donor's external `cass` binary):

1. **Detection** — run the detector over each session → raw signals.
2. **Signals** — normalize signals with their context windows and sources.
3. **Context** — extract the applicability **conditions** from each signal's
   context window (the "when Y" clause) and find the trailing correction.
4. **Clustering** — group evidence by source-type + failed-action similarity so
   the same underlying mistake across sessions coalesces.
5. **Synthesis** — LLM-summarize each cluster into a candidate
   `AntiPattern{ rule: NEVER X when Y, instead, severity, confidence n/(n+2) }`,
   and the parallel opik-style `Issue{ cause, suggestedFix, tracesQuery,
   severity, occurrences, firstSeen/lastSeen }` for the observability surface.

**Safety before storage:** every session is run through the secret scanner +
ACIP injection quarantine + PII anonymizer *before* it enters the store or the
LLM synthesis step. Untrusted content carries a **taint label** (`Untrusted`
/ `Redacted`) that forces human review downstream.

## Where it plugs in (neuro-centrifuge)

- **D12 loop-3** consumes the whole pipeline; confirmed anti-patterns land in a
  **versioned anti-pattern registry** (`harness_skills`).
- Registry entries are then consumed by: skill heals (loop-4), prompt mutations
  (loop-1), judge criteria (loop-2), rescue-agent triggers (D13 class 6), and
  `BeforeToolCall` guard hooks.
- Each HITL review decision is itself logged as a `_llm_scores` record
  (`source_type = annotation`) so the review process is regression-gateable, and
  raises/lowers the finding's confidence as an evidence event.
