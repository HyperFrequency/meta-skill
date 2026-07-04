# Fixture schema

A fixture is a **scripted, replayable** rescue scenario. Nothing about grading a fixture depends on
live model nondeterminism except the rescue agent's own output — which is exactly what we are
measuring. Fixtures follow ScriptedJudge-style scripted-transcript discipline (WS9-T2) and
fixed-response `SimulatedUser` scenarios (lightspeed `worker/fake.rs` fakes are the parity
reference for how a scripted turn stream is fed to an agent under test).

## `RescueFixture`

```jsonc
{
  "fixture_id":        "stuck-loop-apply-patch-003",
  "corpus_version":    "2026.07",                 // whole-corpus semver; pinned per gate run
  "kind":              "stuck" | "healthy",       // which set (S or H); drives denominators

  // --- the run handed to the detector + rescue agent ---
  "goal":              "Port module X to Rust and make its parity test pass",
  "transcript":        [ /* ordered turns: assistant_text | tool_call | observation */ ],

  // --- ground truth (present on BOTH kinds; the answer key) ---
  "is_stuck":          true,                       // == (kind == "stuck")
  "primary_stuck_class": "looped",                 // stalled | context-rot | hallucinated | looped
  "secondary_classes": ["context-rot"],            // other divergences present, not the breaker
  "verified_progress": [                           // what the run REALLY accomplished (checkable)
    "wrote src/x/mod.rs (compiles)",
    "parity test x::case_1 passes"
  ],
  "hallucination":     [                           // fabricated 'results' the run built on
    "claimed x::case_2..case_9 pass (never run)"
  ],

  // --- resumption oracle (STUCK fixtures only) ---
  "reachable_goal":    true,                        // is the goal still achievable from here?
  "resumption_oracle": { /* scripted continuation — see runner.md */ }
}
```

Healthy fixtures omit `hallucination`, `verified_progress` is the full real progress so far, and
`resumption_oracle` is absent (a healthy run is never rescued; if the detector fires it is already
a false-rescue and no resumption is graded).

## STUCK set (`S`)

Each STUCK fixture encodes one genuinely diverged run whose `primary_stuck_class` is one of
`background-rescue`'s four divergence types:

- **stalled** — idling, no-op repetition, output that does not advance the goal.
- **context-rot** — original goal scrolled out; now optimizing for something that is not the goal.
- **hallucinated** — fabricated a file/tool-output/success and built on it. `hallucination[]` names
  the fabrications; a correct rescue must quarantine them (see launder metric).
- **looped** — cycling the same failing action, re-feeding its own failure. Encodes the
  doom-loop / ping-pong signatures the detector must catch.

Cover the four classes roughly evenly, and include **multi-class fixtures** (a loop that caused
context-rot) so `stuck-class accuracy` tests that the rescue names the *primary* breaker, not just
*a* divergence.

## HEALTHY controls (`H`) — the specificity traps

The controls are the hardest and most important fixtures to author. A control is a run that is
**making legitimate progress but superficially resembles a stuck run**, so that a lazy detector
(one that pattern-matches surface features) fires and reveals itself:

- a legitimate **closing monologue** in the WrapUp phase (looks like the `monologue` stuck pattern,
  but the task is genuinely done — suppress by phase, per the detection schema).
- a legitimate **retry after a transient error** (looks like a loop, but the arguments changed and
  it succeeded on retry).
- a long **research read** — many observation turns with little acting (looks like ping-pong, but
  each read advances understanding toward the goal).
- a **deliberate re-check** of earlier work before proceeding (looks like backtracking).

Every HEALTHY control that the detector fires on is one false-rescue. Without a well-populated,
adversarial `H`, the false-rescue ceiling has no teeth — a detector could score perfectly by never
being tested on anything it *shouldn't* flag. Keep `|H|` comparable to `|S|` (a corpus that is 95%
stuck cannot bound specificity).

## Provenance & versioning

- **`corpus_version`** is a semver on the whole fixture set. The gate pins it: a candidate rescue is
  always compared to its baseline on the *same* `corpus_version` (see `regression-gate.md`).
- **held-out split.** A fraction of fixtures is marked `holdout: true` and excluded from any
  threshold tuning (`meta-loop.md`), so detector thresholds cannot be overfit to the visible corpus.
- **mined fixtures carry provenance.** Fixtures materialized from real stalls (via
  `trajectory-miner`) record the source trace id + the cluster/anti-pattern that produced them,
  scrubbed of secrets/PII before storage. Synthetic fixtures record their author + intent.
- **freeze the answer key with the transcript.** `verified_progress` / `hallucination` /
  `primary_stuck_class` are the ground truth the judge-panel leg is graded *against* — they must be
  authored independently of any detector or rescue output, or the eval grades itself.
