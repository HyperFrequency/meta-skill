# Pareto Method: Objectives, Dominance, Selection

Depth for `multi-objective-optimization`. This file defines how objectives are
encoded, how Pareto dominance is computed, how the non-dominated front is
extracted, and how to pick a molecule off that front.

## 1. Encode every objective as a "gap" (all-minimize normal form)

An objective is a triple `(property, direction, target)`. Different directions
are all reduced to a single **gap** where `0` means the target is satisfied and
larger means worse. This lets one dominance test work across a mixed bag of
minimize / maximize / range goals.

| Direction | Spec syntax | Gap (0 = satisfied, higher = worse) |
| --------- | ----------- | ----------------------------------- |
| `minimize` | `LogP:minimize:3.0` | `max(0, value - target)` |
| `maximize` | `QED:maximize:0.5` | `max(0, target - value)` |
| `range` | `TPSA:range:20:130` | `0` inside `[lo,hi]`; else distance to the nearest bound |

The gap is a **one-sided hinge**, not a signed error. A molecule that beats a
`minimize` target (value already below it) gets gap `0`, not a negative reward —
overshooting a satisfied objective must not buy dominance over another objective
that is still violated. This is deliberate: it keeps the search from trading a
solved property for slack on an unsolved one.

Objectives are free scalars: any per-molecule number you can compute is a valid
objective. The built-in property set below is physicochemical / drug-likeness
descriptors. For true ADMET endpoints (hERG, aqueous solubility, microsomal
clearance, CYP inhibition) compute them with `admet-prediction` and feed the
returned scalar in as the objective value — the Pareto machinery is agnostic to
where the number came from.

### Built-in property functions (RDKit)

| Key | RDKit call | Measures |
| --- | ---------- | -------- |
| `MW` | `Descriptors.MolWt` | molecular weight |
| `LogP` | `Descriptors.MolLogP` | lipophilicity (Crippen cLogP) |
| `TPSA` | `Descriptors.TPSA` | topological polar surface area |
| `HBA` | `Descriptors.NumHAcceptors` | H-bond acceptors |
| `HBD` | `Descriptors.NumHDonors` | H-bond donors |
| `RotBonds` | `Descriptors.NumRotatableBonds` | rotatable bonds (flexibility) |
| `QED` | `QED.qed` | quantitative estimate of drug-likeness |
| `AromaticRings` | `Descriptors.NumAromaticRings` | aromatic ring count |
| `FractionCSP3` | `Descriptors.FractionCSP3` | sp3 fraction (3D character) |
| `NumRings` | `Descriptors.RingCount` | total ring count |

## 2. Pareto dominance on gap vectors

Given two molecules with gap vectors `a` and `b` over the same ordered
objectives, **A dominates B** when A is no worse on every objective and strictly
better on at least one:

```
dominates(a, b)  ⇔  (∀i: a[i] ≤ b[i])  AND  (∃i: a[i] < b[i])
```

A molecule is **non-dominated** (on the Pareto front) if no other candidate
dominates it. Extract the front by testing each candidate against all others;
anything dominated drops to the dominated set. This is O(n²) in candidates,
which is fine for the tens-to-hundreds of molecules this skill handles — do not
reach for fast non-dominated sorting (NSGA-II style) unless a front grows into
the thousands.

Key property: the front contains **every worthwhile trade-off**. A candidate
with the best LogP and a candidate with the best QED can both sit on the front
even though neither is "best overall" — that is the point of not collapsing to a
scalar.

## 3. Why not a weighted sum

Collapsing objectives to `w1·g1 + w2·g2 + …` looks simpler but is the wrong
tool here:

- **It hides trade-offs.** One number cannot tell you that molecule A is the
  solubility-favoring option and B the potency-favoring one — information a
  medicinal chemist actually wants.
- **The weights are unknowable up front.** You rarely know the exchange rate
  between "one log unit of LogP" and "0.1 of QED" before seeing the candidates.
- **A weighted sum can only ever find the convex hull of the front.** Solutions
  on a concave region of the true Pareto front are unreachable by *any* choice
  of positive weights. Pareto ranking finds them.

Report the front; let the human (or a downstream skill) apply preferences after
seeing the shape of the trade-off, not before.

## 4. Selecting from the front

The front is the deliverable, but you often need a shortlist:

- **Total-gap tiebreak.** Sort the front by `sum(gaps)` ascending to surface the
  most balanced candidates first. This is a *presentation* order, not a
  re-collapse — the full front is still returned.
- **Similarity to the parent.** In optimize mode, ECFP4 Tanimoto to the input
  (`AllChem.GetMorganFingerprintAsBitVect`, radius 2, 2048 bits →
  `DataStructs.TanimotoSimilarity`) tells you how far each front member drifted.
  Keep a floor (default ≥ 0.4) or you have quietly slipped into de novo design —
  see `denovo-design`.
- **Crowding / diversity.** When two front members are near-identical in gap
  space, prefer the one that adds structural diversity so the shortlist is not
  three copies of one idea.
- **Hypervolume** is the standard single-number *quality metric for a whole
  front* (dominated volume relative to a reference point). Use it to compare two
  runs or track progress across iterations — not to rank molecules within one
  front.

## 5. Edge cases and failure modes

- **Invalid input SMILES.** `Chem.MolFromSmiles` returns `None`; abort with a
  clear error rather than scoring garbage.
- **Front collapses to one point.** If a single candidate dominates all others,
  the front has size 1 — that is a legitimate result (one candidate is
  unambiguously best), not a bug. Report it as such.
- **No candidate beats the reference.** The reference itself can sit on the
  front. If nothing dominates it, say so honestly; do not manufacture an
  "improvement".
- **Objectives that no available edit can move.** Bioisosteric replacement has a
  limited reach; a target may be unreachable from this parent. Surface the gap
  that never closed instead of pretending progress.
- **Degenerate objectives.** Two objectives that are near-perfectly correlated
  (e.g. `MW` and `HBA` on a homologous series) inflate the front without adding
  real trade-off. Prune redundant objectives before running.
- **Descriptors are proxies.** RDKit `LogP`, `TPSA`, `QED` are cheap estimates,
  not measured values. A Pareto-optimal set under these proxies still needs
  experimental or ML confirmation (`admet-prediction`) before you trust it.

## Method provenance

The generate-then-rank framing with scaffold preservation follows **MultiMol**
(Yu et al., 2025); using an LLM as a genetic/mutation operator over molecules
follows **MOLLM** (Ran et al., 2025); reasoning about property groups before
generating follows **DrugR** (Liu et al., 2026). This skill re-implements the
Pareto-ranking core over RDKit; it does not wrap those systems.
