# Verification & Candidate Comparison

The gate that turns a generated string into a trustworthy candidate, plus the
side-by-side comparison used to rank survivors. Called from `SKILL.md` and
`references/optimization-protocol.md`. All calls are RDKit (BSD-3-Clause).

## 1. SMILES Validation

Parse first; everything else is meaningless on an unparseable string.

```python
mol = Chem.MolFromSmiles(smiles)
if mol is None:
    # invalid — inspect cheaply before giving up
    unbalanced_parens   = smiles.count('(') != smiles.count(')')
    unbalanced_brackets = smiles.count('[') != smiles.count(']')
```

When it parses, record the canonical form and basic sanity signals:

- `Chem.MolToSmiles(mol)` — canonical SMILES (dedupe candidates on this).
- `Chem.SanitizeMol(mol)` — surfaces unusual-valence / aromaticity warnings.
- `Chem.rdMolDescriptors.CalcMolFormula(mol)` — molecular formula.
- `mol.GetNumAtoms()`, `mol.GetNumBonds()` — flag < 3 atoms (degenerate) or
  > 100 atoms (likely runaway generation).

## 2. Similarity to Parent (ECFP4 / Tanimoto)

Optimization means *staying near* the hit. Use Morgan fingerprints, radius 2
(ECFP4), 2048 bits:

```python
fp_parent = AllChem.GetMorganFingerprintAsBitVect(parent, 2, nBits=2048)
fp_cand   = AllChem.GetMorganFingerprintAsBitVect(cand,   2, nBits=2048)
tanimoto  = DataStructs.TanimotoSimilarity(fp_parent, fp_cand)
```

Interpretation bands used to classify an edit:

| Tanimoto | Classification |
|----------|----------------|
| ≥ 0.6 | optimization (close analog) |
| 0.4 – 0.6 | significant modification |
| < 0.4 | de novo design — outside the optimization regime |

Default gate: reject (or at least flag) anything below **0.4**. Loosen it
deliberately for scaffold hopping.

## 3. Scaffold Preservation (Murcko)

Compare **generic** Murcko scaffolds so the test is about topology, not the
specific heteroatoms:

```python
from rdkit.Chem.Scaffolds import MurckoScaffold
def generic_scaffold(m):
    return Chem.MolToSmiles(
        MurckoScaffold.MakeScaffoldGeneric(MurckoScaffold.GetScaffoldForMol(m)))
preserved = generic_scaffold(parent) == generic_scaffold(cand)
```

`preserved is False` is a warning during optimization and an *expectation*
during scaffold hopping — interpret it against your intent, don't hard-fail on
it blindly.

## 4. Maximum Common Substructure (MCS)

To quantify how much of the parent survived, and to visualize the edit:

```python
from rdkit.Chem import rdFMCS
mcs = rdFMCS.FindMCS([parent, cand], timeout=10)
mcs_atoms  = mcs.numAtoms
mcs_smarts = mcs.smartsString
```

Always pass a `timeout`; MCS is NP-hard and can hang on large pairs. A small MCS
relative to the parent is another signal the edit drifted too far.

## 5. Claimed-Modification Check

The highest-value check: does the structure actually contain the change that was
*described*? This is a heuristic matcher keyed on the claim text — it maps
keywords in the claim to concrete substructure or atom-count assertions on the
product. Examples of the assertions it makes:

| Claim mentions | Assertion on the candidate |
|----------------|----------------------------|
| "add hydroxyl / OH" | `HasSubstructMatch([OH])` true in product, false in parent |
| "fluorine / fluoro" | `[F]` present in product |
| "remove chlorine" | `[Cl]` in parent, absent in product |
| "pyridine" | `HasSubstructMatch('c1ccncc1')` in product |
| "add nitrogen / amine" | atomic-number-7 count increased vs parent |

```python
had = parent.HasSubstructMatch(Chem.MolFromSmarts('[OH]'))
has = cand.HasSubstructMatch(Chem.MolFromSmarts('[OH]'))
hydroxyl_added = has and not had
```

Result semantics: `verified = True` (all matched assertions passed),
`verified = False` (a claim contradicts the structure — reject), or
`verified = None` (no keyword matched, so the claim is unchecked — do not treat
`None` as a pass). This catches the phantom-modification failure mode where a
model narrates an edit it never made. It is deliberately conservative: extend
the keyword→assertion table for the modifications your pipeline actually claims;
an unrecognized claim returns `None`, not silent approval.

## 6. Candidate Comparison Table

For ranking survivors, build a per-property comparison against the reference and
tag each property with a status:

```python
for prop in ref_props:
    delta  = cand_props[prop] - ref_props[prop]
    ref_ok = in_band(prop, ref_props[prop])
    new_ok = in_band(prop, cand_props[prop])
    status = ('FIXED'     if (not ref_ok and new_ok) else
              'BROKEN'    if (ref_ok and not new_ok) else
              'still_out' if (not ref_ok and not new_ok) else 'ok')
```

Roll the statuses into `improvements` (count of `FIXED`) and `regressions`
(count of `BROKEN`) and a `net_score = improvements − 0.5 * regressions`, then
sort candidates descending. This is the same asymmetric weighting the loop uses
in Step 5 — a fix is worth twice what a regression costs.

## RDKit Import Reference

```python
from rdkit import Chem
from rdkit.Chem import Descriptors, QED, AllChem, DataStructs, rdFMCS, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit import RDLogger
RDLogger.logger().setLevel(RDLogger.ERROR)   # silence parse-failure noise
```
