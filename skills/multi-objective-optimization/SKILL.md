---
name: multi-objective-optimization
version: 0.1.0
description: >-
  Pareto-aware multi-objective optimization for small molecules: balance several
  ADMET / physicochemical objectives (LogP, QED, TPSA, or any scalar from
  `admet-prediction`) at once by ranking candidates on Pareto dominance instead
  of collapsing them to a weighted sum. Each objective is encoded minimize /
  maximize / range toward a target; candidates come from bioisosteric edits
  (RDKit) or a CSV, then split into the non-dominated Pareto front and the
  dominated set — the whole front, not one winner. Use when improving one
  property must not wreck another (raise potency while keeping hERG safe), to
  trade ADMET liabilities (LogP vs solubility, BBB vs safety), or to rank an
  existing candidate set. NOT for single-objective optimization (use
  `molecular-optimization`), raw property prediction (use `admet-prediction`),
  liability interpretation only (use `admet-reasoning`), de novo generation (use
  `denovo-design`), docking / affinity (use `molecular-docking`,
  `binding-affinity`), or biologics, peptides, and PROTACs.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (RDKit)"
---

# Multi-Objective Molecular Optimization

## Overview

Real drug design is never single-objective. A useful molecule has to satisfy
potency, selectivity, solubility, metabolic stability, and safety *at the same
time*, and these pull against each other — lowering LogP for solubility can cost
permeability; adding an aromatic ring for potency can trip an hERG or genotoxic
alert. The naive fix, a weighted sum `w1·objective1 + w2·objective2 + …`, throws
that structure away: it hides trade-offs behind one number, needs weights you
cannot know before seeing the candidates, and provably cannot reach solutions on
a concave part of the trade-off surface.

This skill optimizes **without collapsing**. It scores each candidate against
every objective independently, then ranks by **Pareto dominance**: a molecule is
kept if no other candidate is at-least-as-good on all objectives and strictly
better on one. The deliverable is the **Pareto front** — the full set of
non-dominated trade-offs — not a single "winner". A human or a downstream skill
applies preferences *after* seeing the shape of the front.

Mechanically: each objective is encoded as a one-sided **gap** (`minimize`,
`maximize`, or `range` toward a target; `0` = satisfied, higher = worse);
candidates are grown from a parent by bioisosteric replacement (RDKit
`ReplaceSubstructs`) or supplied as a CSV; then non-dominated sorting splits them
into the front and the dominated set.

**This file is a router.** Depth lives in `references/`:

- `references/pareto-method.md` — objective encoding, the dominance test,
  non-dominated sorting, why not a weighted sum, front selection (total-gap,
  similarity, crowding, hypervolume), the built-in property table, and edge
  cases / failure modes.
- `references/reference-implementation.md` — a runnable RDKit implementation
  (optimize + analyze modes), CLI usage, and the output JSON schema.

## When to Use This Skill

- **Competing objectives.** Improving one property must not wreck another —
  "raise potency while keeping hERG safe", "cut LogP without losing QED".
- **Trading ADMET liabilities.** LogP vs aqueous solubility, BBB penetration vs
  peripheral safety, potency vs molecular weight.
- **Extracting a Pareto front.** You already have a set of candidates (a CSV) and
  want the non-dominated trade-offs identified and the dominated ones filtered.
- **Property-boxed design.** Generate analogs that land inside several target
  bands at once (e.g. `LogP ≤ 3`, `QED ≥ 0.5`, `20 ≤ TPSA ≤ 130`).

## When NOT to Use This Skill

- **A single objective** — use `molecular-optimization`, which runs the
  analyze → generate → verify → score loop for one target and preserves scaffold
  and similarity.
- **Property prediction with no optimization** — use `admet-prediction` to score
  a molecule; this skill *consumes* such scores as objectives.
- **Liability interpretation only** — to explain *why* a feature is a risk and
  what fixes it, use `admet-reasoning`; it steers which objectives matter.
- **De novo generation from scratch** (no starting hit, no similarity floor) —
  use `denovo-design`. This skill modifies an existing molecule.
- **Docking / binding affinity** — use `molecular-docking` and
  `binding-affinity`. Pose and ΔG are not objectives here.
- **Biologics, peptides, PROTACs, inorganics** — the descriptors and bioisostere
  rules assume drug-like small molecules and are out of applicability domain.

## The Method in Brief

Full detail in `references/pareto-method.md`; runnable code in
`references/reference-implementation.md`.

1. **Define objectives.** Each is `property:direction:target`, where direction is
   `minimize`, `maximize`, or `range:lo:hi`. Objectives are any per-molecule
   scalar; physicochemical descriptors are built in, real ADMET endpoints come
   from `admet-prediction`.
2. **Assemble candidates.** Either grow them from a parent SMILES via bioisosteric
   replacement, or load an existing set from CSV.
3. **Score gaps.** For every candidate, reduce each objective to a one-sided gap
   (`0` = target met, higher = worse) so mixed directions share one scale.
4. **Rank by dominance.** Non-dominated sort into the **Pareto front** (kept) and
   the **dominated set** (filtered). Front size 1 is a valid result; the
   reference molecule may itself be non-dominated.
5. **Select.** Present the front sorted by total gap; break ties with
   similarity-to-parent and structural diversity. Report the whole front, and be
   honest when nothing dominates the reference.

## Why the Front, Not a Winner

The single most common misuse of multi-objective design is re-collapsing the
result to one molecule too early — reintroducing exactly the weighted-sum blind
spot the method exists to avoid. A candidate that is best on solubility and one
that is best on potency can *both* be Pareto-optimal; discarding either loses a
real option a chemist would want to weigh. Return the front. Apply preferences
last, explicitly, and only after the trade-off shape is visible.

## References

- `references/pareto-method.md` — dominance, objective encoding, selection,
  edge cases.
- `references/reference-implementation.md` — runnable RDKit code, CLI, JSON
  output.

## Related Skills

- `molecular-optimization` — single-objective / scaffold-preserving lead
  optimization loop; delegate here when objectives genuinely compete.
- `admet-prediction` — computes the ADMET / drug-likeness scalars used as
  objectives.
- `admet-reasoning` — maps each liability to cause and fix; use it to choose
  *which* objectives to trade.
- `denovo-design` — generation without a starting hit or similarity floor.
- `molecular-docking`, `binding-affinity` — pose and binding-strength estimation,
  downstream of property optimization.
