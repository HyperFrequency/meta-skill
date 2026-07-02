# SCAN (Loop-3 stage 3) — the Scanner trait & versioned catalog

Every detector is a **Scanner**: a deterministic (no-LLM) pure function of one
segmented session, emitting zero or more **Incidents**. Each scanner declares a
**versioned criteria schema** so an incident records exactly which rule-set
flagged it and can be re-derived (or invalidated) when the schema is bumped.

```rust
trait Scanner {
    fn id(&self) -> &str;               // stable, e.g. "doom_loop"
    fn criteria_version(&self) -> &str; // e.g. "doom_loop.v2"
    fn scan(&self, s: &SegmentedSession) -> Vec<Incident>;
}
```

Determinism is the contract: same input + same `criteria_version` ⇒ identical
incidents, forever. LLM judgment happens *later* (cluster/review), never in a
scanner. That is what makes the registry reproducible and the confidence numbers
mean something.

**Incident:**

```json
{
  "session_id": "…", "source": "otel|traj|claude|…",
  "scanner_id": "doom_loop", "criteria_version": "doom_loop.v2",
  "mode": "doom_loop|stuck|context_degradation|correction|recursion|cost_anomaly",
  "subtype": "…",                 // scanner-specific (e.g. "poisoning", "monologue")
  "phase": "Change",              // dominant phase of the turn_range
  "turn_range": [start_seq, end_seq],   // MUST exist in the session
  "signature": "normalized string for clustering",
  "severity": "low|med|high",
  "evidence": "minimal, already-scrubbed excerpt proving it"
}
```

Every incident MUST cite a real `turn_range`. **Never invent an incident.**
Every threshold below is a named knob in the criteria schema; report the values
used in the run header.

---

## 1. DoomLoopScanner (`doom_loop.vN`)

Tool-signature cycles with no progress — the crispest, highest-precision scanner.

- **`[A,A,A]` run:** the same `input_sig` occurs `≥ 3` times consecutively (or
  within a small window) with no successful state-changing `tool_result` between.
- **`[A,B,C][A,B,C]` cycle:** a repeating ordered sequence of 2–4 distinct
  `input_sig`s that recurs `≥ 2` full periods (A,B,C,A,B,C). Detect via the
  smallest period `p` such that `sig[i] == sig[i-p]` holds across the window.
- **Edit thrash:** `≥ 3` `Edit`/`Write` calls to the same path with no passing
  `Validation` result between.
- **Signature:** `doom_loop:{phase}:{tool}:{sorted sig-set}`.
- **Severity:** high if the loop runs to session end; med if it self-breaks.
- Phase-aware: a Validation `[A,A,A]` (re-running an unchanged failing test) and
  a Recon `[A,A,A]` (re-grepping) are distinct signatures, not one bucket.

## 2. StuckDetector (`stuck.vN`) — port of the OpenHands algorithm

Behavioral stuck-states that are not tight signature loops. Re-implemented
from the OpenHands `StuckDetector` heuristics (algorithm described here;
write original code, do not copy theirs). Four subtypes:

- **`monologue`:** `≥ 3` consecutive `assistant_text` turns with **no**
  intervening `tool_result`/observation — the agent is talking to itself instead
  of acting. Suppress in `WrapUp` (a closing summary is legitimate monologue).
- **`ping_pong`:** a repeating alternating action↔observation pair (same
  `input_sig` → same result class) recurring `≥ 6` times — softer than a doom
  loop (results may differ slightly) but still non-converging.
- **`context_window_error`:** repeated tool/model errors of the
  context-length-exceeded class (`context_length_exceeded`, "maximum context",
  "prompt is too long") — the agent keeps hitting the wall and retrying blind.
- **`action_error`:** the same action repeatedly returning an error of the same
  class (`≥ 4`), even when interleaved with reasoning.
- **Signature:** `stuck:{subtype}:{tool_or_error_class}`.
- **Severity:** high (`context_window_error`, unbroken `monologue` at session
  end); med otherwise.

## 3. ContextDegradationScanner (`context_degradation.vN`)

The `ce-context-degradation` taxonomy — five ways a growing context corrupts
behavior. Long sessions near the token window are the amplifier; each subtype has
its own tell.

- **`lost_in_middle`:** a constraint/fact established in the *middle* of a long
  session is later violated or re-requested, while early- and late-context facts
  are honored. Tell: re-read/re-ask for something already answered mid-session,
  in a session past ~`long_turns` (default 150) turns.
- **`poisoning`:** a hallucinated or **quarantined** (injection-tagged, from
  ingest §7) item enters context and is then repeatedly referenced as if true —
  the error propagates. Tell: an entity/claim with no successful tool
  corroboration is cited `≥ 3` times downstream.
- **`distraction`:** context grows so large the agent over-weights its own
  history — re-summarizing/reciting past steps instead of advancing. Tell: rising
  ratio of `assistant_text` that restates prior turns vs. new `tool_call`s as the
  session lengthens.
- **`confusion`:** superfluous available surface (too many tools/options)
  degrades tool choice. Tell: bursts of calls to rarely-productive or
  irrelevant-to-goal tools, or oscillation between near-duplicate tools.
- **`clash`:** two conflicting facts/instructions accrued in context, and the
  agent flip-flops or contradicts an earlier confirmed statement. Tell: a later
  assertion negates an earlier confirmed one on the same entity.
- **Signature:** `context_degradation:{subtype}:{forgotten_or_conflicting_entity}`.
- **Severity:** med (isolated) → high (drives a downstream loop/failure).
- Most false-positive-prone group after hallucination: keep the excerpt, and when
  unsure downgrade to `low` rather than drop — the review stage confirms.

## 4. RollbackCorrectionScanner (`correction.vN`)

Not a "failure" per se but the **highest-value training signal** — a wrong step
followed by its correction is a labeled (bad → good) pair.

- **Rollback:** `git revert`/`reset`/`checkout --`, re-`Write` of a file to a
  prior state, "let me undo/revert that", deleting just-created files.
- **Self-correction:** assistant text like "that's wrong / that didn't work /
  actually / let me try a different approach" immediately preceding a changed
  strategy.
- **User correction:** a user turn that negates the agent's direction
  ("no, I meant…", "that's not what I asked", "stop, revert") — a ground-truth
  negative label.
- **Signature:** `correction:{trigger}:{from→to action class}`.
- **Severity:** low as a defect (correction is healthy), but **high value** — tag
  these for the reflective/heal consumers, which learn most from the corrected
  pair. Capture BOTH the bad turn_range and the correcting turn_range.

## 5. RecursionCostScanner (`recursion_cost.vN`)

Two anomaly families that only surface with `depth` and `tokens`.

- **`infinite_recursion`:** subagent spawn depth (`TurnEvent.depth`, or
  `Agent`/`Task` tool calls nesting) exceeds `max_depth` (default 4), or a
  re-entrant spawn cycle (agent A spawns B spawns A) — unbounded fan-out.
- **`cost_anomaly`:** per-session or per-**phase** token/$ spend `≥ k`× the
  corpus median (default `k=4`, computed after gating so junk doesn't skew the
  median), or monotonic output-token growth per assistant turn (runaway
  generation). Phase-level catches "Recon burned 80% of budget" waste that a
  session total hides.
- **Signature:** `recursion:{subtype}` / `cost_anomaly:{phase}`.
- **Severity:** high for `infinite_recursion`; med for cost (environmental/tuning)
  but high blast-radius if systemic across the corpus.

---

## Detector hygiene (applies to all scanners)

- **Windowing:** cross-turn scanners (context-degradation, poisoning) bound the
  look-back window (default 40 events) so cost stays linear in session length.
- **Sidechains:** scan per `session_id` but carry `is_sidechain`/`depth` on each
  incident — a subagent's loop is a subagent-harness problem, reported distinctly.
- **Overlap is expected:** one `turn_range` can trip several scanners (a
  context-window-error `stuck` that becomes a `doom_loop`). Emit them all; the
  cluster stage dedups and lets one annotate the other as a cause tag.
- **Versioning discipline:** bumping a `criteria_version` (new threshold, new
  subtype) does **not** silently rewrite history — old incidents keep their
  version; the corpus is re-scanned deliberately and the registry records the
  transition. This is what makes "did fixing X reduce mode Y" answerable.
