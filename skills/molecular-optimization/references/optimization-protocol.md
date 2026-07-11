# Optimization Protocol — Full Detail

The six-step loop, thresholds, structural-edit library, scoring rule, stopping
conditions, and batch handling. Called from `SKILL.md`.

## Step 1 — Analyze

Parse and canonicalize the input, then compute descriptors. Abort immediately if
`Chem.MolFromSmiles` returns `None` — do not attempt to "repair" the string.

Core RDKit descriptors (all from `rdkit.Chem.Descriptors` unless noted):

| Descriptor | Call |
|-----------|------|
| Molecular weight | `Descriptors.MolWt(mol)` |
| LogP (Crippen) | `Descriptors.MolLogP(mol)` |
| TPSA | `Descriptors.TPSA(mol)` |
| H-bond acceptors | `Descriptors.NumHAcceptors(mol)` |
| H-bond donors | `Descriptors.NumHDonors(mol)` |
| Rotatable bonds | `Descriptors.NumRotatableBonds(mol)` |
| Aromatic rings | `Descriptors.NumAromaticRings(mol)` |
| Ring count | `Descriptors.RingCount(mol)` |
| QED (drug-likeness) | `rdkit.Chem.QED.qed(mol)` |

Also capture the **generic Murcko scaffold** so later steps can test whether an
edit preserved the core:

```python
from rdkit.Chem.Scaffolds import MurckoScaffold
scaffold = MurckoScaffold.GetScaffoldForMol(mol)
generic  = MurckoScaffold.MakeScaffoldGeneric(scaffold)   # atoms→C, bonds→single
scaffold_smiles = Chem.MolToSmiles(generic)
```

## Step 2 — Identify Liabilities

Flag every descriptor outside its target band and sort by severity. These
default bands follow the DrugR thresholds; treat them as a starting rule set and
override per project or per delivery route (CNS vs oral vs topical differ).

| Property | Target band | Severity |
|----------|-------------|----------|
| hERG inhibition | < 0.3 | critical |
| DILI (hepatotox) | < 0.5 | critical |
| CYP inhibition | < 0.5 | high |
| LogP | 1.0 – 3.0 | medium |
| TPSA | 20 – 130 | medium |
| MW | 150 – 500 | medium |
| Solubility (LogS) | > −4.0 | medium |
| HBA | ≤ 10 | low |
| HBD | ≤ 5 | low |
| QED | > 0.5 | low |

Severity ordering for sorting: `critical(0) < high(1) < medium(2) < low(3)`.
Address the most severe flag first — a fix that trades an hERG liability for a
QED dip is usually worth it; the reverse is not.

**Note on toxicity endpoints.** hERG, DILI, and CYP are *predicted* endpoints,
not RDKit descriptors. Source them from `admet-prediction` (PyTDC / ADMET-AI
models) or a SMARTS structural-alert catalogue (see `admet-reasoning`). The
physicochemical bands (MW, LogP, TPSA, HBA, HBD, QED) are computed directly.

## Step 3 — Generate Candidates

Turn each liability into concrete structural edits. The primary engine is
**bioisosteric replacement** via substructure matching and swap:

```python
patt = Chem.MolFromSmarts(old_pattern)          # e.g. 'c1ccccc1'
if mol.HasSubstructMatch(patt):
    products = AllChem.ReplaceSubstructs(mol, patt, Chem.MolFromSmiles(new_pattern))
    for p in products:
        smi = Chem.MolToSmiles(p)               # then re-parse to confirm validity
```

A practical starter library (pattern → replacement → rationale):

| From | To | Effect |
|------|----|--------|
| phenyl `c1ccccc1` | pyridine `c1ccncc1` | ↑ polarity, ↓ LogP |
| aromatic `[cH]` | `[n]` | ↓ LogP, add H-bond acceptor |
| `Cl` | `F` | ↓ MW, ↓ lipophilicity |
| amide `C(=O)N` | sulfonamide `S(=O)(=O)N` | metabolic/property shift |
| methoxy `OC` | hydroxy `O` | ↓ LogP, add HBD |
| ethyl→methyl `CC` | `C` | ↓ MW, ↓ LogP |
| naphthalene | indole | add HBD, change electronics |

Beyond bioisosteres, the other edit classes are functional-group
addition/removal, ring-system modification, and chain-length adjustment. Cap at
4–8 candidates per iteration so verification and scoring stay cheap. `ReplaceSubstructs`
can return several products per match — treat each as a separate candidate and
verify all of them.

## Step 4 — Verify

Every candidate must clear the verification gate before it is scored. Full
detail (and the exact calls) live in `references/verification.md`. In short:

1. **Parse.** `Chem.MolFromSmiles(candidate)` must not be `None`.
2. **Stay in the optimization regime.** ECFP4 Tanimoto to the parent ≥ 0.4 by
   default; below that the candidate is de novo design, not optimization —
   flag it.
3. **Scaffold check.** Compare generic Murcko scaffolds; a change is allowed for
   scaffold-hopping but must be a deliberate choice, not an accident.
4. **Modification present.** Confirm the intended edit actually appears in the
   product (substructure / atom-count check keyed to the claimed change).

## Step 5 — Score & Rank

Re-derive liabilities for the candidate and compare *sets* against the parent:

```
fixed       = parent_liabilities − candidate_liabilities
introduced  = candidate_liabilities − parent_liabilities
net_score   = 1.0 * len(fixed) − 0.5 * len(introduced)
```

Sort candidates by `net_score` descending. The asymmetric weight (a fix is worth
twice as much as a new liability costs) biases toward net progress while still
penalizing regressions. Keep the full comparison table — per-property delta,
status (`FIXED` / `BROKEN` / `still_out` / `ok`), similarity, and scaffold flag —
for the report; `references/verification.md` covers the candidate-comparison view.

## Step 6 — Iterate & Stop

Adopt the top-scoring candidate as the new parent and repeat from Step 1. Stop
when any of these holds:

- `max_iterations` reached (default 3),
- no candidate in an iteration scores above the current best,
- no liabilities remain to fix,
- no valid candidates could be generated (no matching substructure to edit).

Return the best molecule found across all iterations. **If nothing beats the
input, report that honestly** — "no improvement found; the molecule may already
be well-optimized" — rather than presenting a lateral move as a win.

## Batch Mode

For a CSV of leads, run the single-molecule loop per row and collect the
per-molecule reports into one JSON array. Guard each row independently so one
invalid SMILES does not abort the batch. At scale (thousands of rows) the
fingerprint and MCS work dominate — precompute the parent fingerprint once per
molecule and keep `max_candidates` and `max_iterations` small.

## Failure Modes & Edge Cases

- **Invalid input SMILES** → return an error for that molecule; never guess a
  repair.
- **No substructure match** → the bioisostere library cannot edit the molecule;
  fall back to functional-group edits or report "no modification possible".
- **All candidates fail verification** → return the parent unchanged with the
  reason (usually every edit dropped below the similarity floor).
- **Oscillation** (loop revisits a prior molecule) → the "no score improvement"
  stop condition catches this; optionally de-duplicate on canonical SMILES.
- **Threshold gaming** → a candidate can satisfy a band cosmetically while
  worsening a property the bands don't cover; keep a human or `admet-reasoning`
  in the loop for anything headed to synthesis.

## Method Provenance

- **MT-Mol** (Kim et al., 2025) — multi-agent tool reasoning + verifier;
  motivates Step 4 as a hard gate.
- **DrugR** (Liu et al., 2026) — reason about liabilities before generating;
  motivates Steps 2–3 ordering and the threshold table.
- **MultiMol** (Yu et al., 2025) — generate-then-rank with scaffold
  preservation; motivates Steps 3, 5, and the scaffold check.
