# Detection schema (the versioned SUT)

The stuck-pattern detector is the first of the two subjects this eval grades. Its criteria live in a
**versioned schema** — `detection.vN` — that is the *same* schema `trajectory-miner` scans a corpus
with. Sharing one schema is deliberate: a stall the miner flags at mine-time and the detector fires
on at rescue-time must be the *same* definition, or the two loops drift apart. Every corpus run
records the `schema_version` it graded under (into the `_llm_scores` row) so old scorecards stay
interpretable after a bump.

The schema is a weighted list of **deterministic scanners** over a structured transcript. Each
scanner emits a signal with a subtype and a severity; the detector fires (classifies the run stuck)
when a scanner clears its threshold. Class prediction = the highest-severity firing scanner's
mapped divergence class.

## Scanners

### 1. Doom-loop scanner — class `looped`

Re-implemented from the behavior of forgecode `DoomLoopDetector`
(`crates/forge_app/src/hooks/doom_loop.rs`, Apache-2.0 — behavior described, no code copied). Over
the sequence of `(tool_name, arguments)` signatures:

- **consecutive-identical** `[A,A,A]` — the same tool with the same arguments `≥ threshold` times
  in a row. Default `threshold = 3`.
- **repeating-pattern** `[A,B,C][A,B,C]` — a repeating cyclic subsequence of tool signatures.

Firing on either → `looped`. The threshold is a tunable (see `meta-loop.md`); the eval measures the
precision/false-rescue trade-off as it moves.

### 2. StuckDetector — class `stalled`

Re-implemented from the OpenHands StuckDetector algorithm (described, not copied):

- **`monologue`** — `≥ 3` consecutive `assistant_text` turns with **no** intervening action.
  **Suppressed in the `WrapUp` phase** — a closing summary is a legitimate monologue (this
  suppression is what a HEALTHY control tests; see `fixture-schema.md`).
- **`ping_pong`** — `≥ 6` alternating action↔observation turns that make no progress (same
  action/observation pair recurring).
- **`context_window_error`** — repeated tool/model errors of the context-length family.

### 3. Context-degradation scanner — class `context-rot`

The five `ce-context-degradation` modes, at versioned thresholds:

- **lost-in-middle** — a constraint/goal stated early is contradicted or ignored later.
- **poisoning** — a fabricated fact enters context and later turns treat it as ground truth.
- **distraction** — attention drifts to a rarely-productive tangent (bursts of calls to
  low-yield tools).
- **confusion** — conflicting entities/values held simultaneously.
- **clash** — two retained instructions directly contradict.

These are cross-turn scanners; they window over the whole transcript, not a fixed tail.

### 4. Degeneration metric — modifier

Repetition / entropy collapse in generated text (n-gram repetition ratio above threshold). Rarely
the *primary* class on its own; usually a corroborating signal that raises the severity of a
`monologue` or `looped` firing.

## Class mapping

The detector predicts a **primary** class for the metrics. Mapping from firing scanner → class:

| Firing scanner | Class |
|---|---|
| doom-loop | `looped` |
| StuckDetector `monologue` / `ping_pong` | `stalled` |
| StuckDetector `context_window_error` | `stalled` (or `context-rot` if paired with a degradation firing) |
| context-degradation (any of the five) | `context-rot` |
| poisoning specifically, when a fabricated result is acted on | `hallucinated` |

When multiple scanners fire, the **highest-severity** one sets the predicted primary class;
`stuck-class accuracy` (see `metrics.md`) checks it against the fixture's `primary_stuck_class`.

## Why the version pin is load-bearing (anti-gaming)

The detection schema is a **released, versioned artifact** with its own semver, independent of this
skill's version — mirroring how `skill-eval-runner` versions its frontier rubric. Two rules follow,
both enforced in `meta-loop.md`:

1. **Tightening a threshold or adding a scanner is a `schema_version` bump, not an ad-hoc edit.**
   Every scorecard records the version, so a "recovery went up" claim can't hide a silently loosened
   detector.
2. **The rescue agent under test can never edit this schema.** Detector thresholds are tuned only by
   the external optimizer (TPE/CMA-ES) within gate bounds, on the *training* fixture split, never by
   the subject being scored. This is the disjoint-write-scope that keeps the gate ungameable.
