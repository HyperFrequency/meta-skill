# Risk tiering — MANUAL by default, auto-apply only under bounds

A confirmed anti-pattern is not automatically a green light to *act* on it. This
skill assigns every finding a **tier** — `manual` or `auto-apply` — that governs
whether the downstream fix loop may run unattended. The rule is deliberately
asymmetric:

> **Everything defaults MANUAL. Auto-apply is a narrow, bounded exception.**

You never widen a finding to auto-apply to save the human a click. The cost of a
wrong auto-applied fix (a bad prompt change, a deleted skill) dwarfs the cost of
one more manual approval.

## The auto-apply lane — only under `hyper-sleep` bounds

A finding may be tiered `auto-apply` **only** when it clears the same hard bounds
`hyper-sleep` enforces for unattended work. All must hold; any one failing forces
`manual`:

1. **Confidence cap.** `confidence_after` is at or above the auto-apply cap AND at
   or below `hyper-sleep`'s ceiling of **0.6** for *what gets auto-written*. Read
   this precisely: `hyper-sleep` only auto-writes low-stakes artifacts capped at
   confidence 0.6; anything it is *more* sure matters gets staged for human
   review, not auto-applied. So the auto-apply lane here is for **low-blast-radius,
   reversible** fixes, not for the scariest high-confidence findings. A
   high-severity finding is *never* auto-apply, however confident.
2. **No deletions.** The finding's `proposed_fix` must not delete anything — not a
   file, not a skill, not a KB page, not an ontology node. Any deletion → `manual`
   (and routes to `neuro-surgery`, which is the only surface allowed to delete,
   per-item and thumbs-up gated).
3. **Within the timeout window.** The verdict was recorded before the gate's
   `expires_at`. A finding adjudicated on the timeout path (`default-on-timeout`)
   is **never** auto-apply — a default is a guess, and you do not auto-act on
   guesses.
4. **Low blast radius.** The fix touches only allowed, reversible targets (regen
   an index, normalize a signature, add a stop-condition to a prompt) — the same
   whitelist class `hyper-sleep` uses. A fix that edits agent topology, elevates a
   permission, or rewrites a schema-bound file is `manual`.
5. **Source is not a bare timeout.** `source: human` or `source: auto-confirm`
   (above-threshold miner confidence) only. `default-on-timeout` and `UNRESOLVED`
   are `manual`/parked.

If **every** bound holds, tier `auto-apply`: the fix loop may apply it during a
`hyper-sleep` pass and log it in the morning report. If **any** bound fails, tier
`manual`: it waits for a human, no matter how clean it looks. This is the
auto-apply-creep failure mode from SKILL.md — resist it.

## The three enforcement patterns

Three sibling disciplines make the MANUAL default trustworthy. Apply whichever
fits the finding; they are not mutually exclusive.

### Pattern 1 — `neuro-surgery` per-item approval (NEVER batch-silent)

The default and the strictest. Every manual-tier finding is approved **one at a
time**, showing the reviewer the evidence and (if any) the before/after diff,
waiting for an explicit verdict before the next finding. This is
`neuro-surgery`'s non-negotiable rule imported wholesale:

- **Never** approve a batch with one action. A "confirm all" button is the
  cardinal sin — it is exactly what per-item approval exists to prevent.
- Show the diff; wait for the thumb; then (downstream) apply via a schema-aware
  tool, never a bare `Write`.
- Log every decision (including skips) — an unlogged approval can't be graded
  tomorrow.

Use for anything touching a schema-bound or human-trusted surface (`02-KB-main/`,
`03-Ontology-main/`, skills, prompts).

### Pattern 2 — `recursive-self-improvement` consortium pre-vote

For findings whose fix is a **behavioral change** (a prompt/skill/topology edit),
route through a 3+ agent consortium **before** the human sees it. The consortium
grades whether the proposed fix actually addresses the confirmed anti-pattern;
only proposals with `count >= 2` agreeing graders reach the human, and the human
still approves (default `manual`). This filters reviewer load: the human
adjudicates *findings* here; the consortium pre-screens *fixes* so the human is
not hand-grading every candidate change. Single-grader auto-apply is never
allowed — one grader is overfit to its own biases.

### Pattern 3 — `meta_skill` UncertaintyQueue

Findings the reviewer could not cleanly resolve — `UNRESOLVED` verdicts, split
inter-annotator disagreements, findings whose confidence hovers right at
`review_threshold` after the evidence event — go to a persistent
**UncertaintyQueue** rather than being force-decided. The queue:

- **Persists across gates.** An unresolved finding is not dropped; it re-surfaces
  next review with any new evidence accumulated since.
- **Batches the genuinely-hard ones.** Instead of blocking a whole scan on one
  ambiguous cluster, park it and let the confident findings flow.
- **Escalates on repeat.** A finding that hits the queue twice is flagged for a
  human deep-look or a consortium adjudication — repeated uncertainty is itself a
  signal the taxonomy or the evidence is inadequate.

This is the pressure-release valve that keeps the MANUAL default from becoming a
bottleneck: hard calls queue, they do not force a coin-flip verdict.

## Tiering summary

| Finding shape | Tier | Route |
| --- | --- | --- |
| Human CONFIRM, low-blast, reversible, no deletion, in-window, conf ≤ 0.6 cap | `auto-apply` | fix loop during `hyper-sleep`; morning report |
| Human CONFIRM, behavioral fix (prompt/skill/topology) | `manual` | consortium pre-vote (Pattern 2) → per-item approval (Pattern 1) |
| Human CONFIRM, touches schema-bound / high-trust surface | `manual` | per-item approval (Pattern 1), schema-aware apply |
| Any deletion proposed | `manual` | `neuro-surgery` only (per-item, rollback-gated) |
| `default-on-timeout` verdict | `manual` | never auto-apply a guess |
| `UNRESOLVED` / split / at-threshold | parked | UncertaintyQueue (Pattern 3) |

The through-line: **auto-apply is small, bounded, and reversible; everything with
stakes is a human decision, made one finding at a time.**
