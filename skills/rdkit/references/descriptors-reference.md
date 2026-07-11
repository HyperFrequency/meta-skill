# RDKit Descriptors Reference

Catalogue of the molecular descriptors in `rdkit.Chem.Descriptors`, grouped by
family. RDKit ships ~210 2D descriptors; every name below is callable as
`Descriptors.<Name>(mol)` and also appears as a key in the batch dictionary.

## Batch calculation

```python
from rdkit import Chem
from rdkit.Chem import Descriptors

mol = Chem.MolFromSmiles("CCO")
all_desc = Descriptors.CalcMolDescriptors(mol)   # dict of every descriptor
mw = all_desc["MolWt"]

names = [name for name, _fn in Descriptors._descList]   # enumerate the full set
```

Prefer `CalcMolDescriptors` when you need many values — it avoids recomputing
shared intermediates. Some descriptors can raise or return `nan` on pathological
inputs (e.g. partial-charge descriptors on unusual elements); wrap in try/except
when scanning an untrusted library.

## Physicochemical

| Name | Meaning |
|---|---|
| `MolWt` | average molecular weight |
| `ExactMolWt` | monoisotopic weight |
| `HeavyAtomMolWt` | weight ignoring hydrogens |
| `MolLogP` | Wildman–Crippen logP (lipophilicity) |
| `MolMR` | Wildman–Crippen molar refractivity |
| `TPSA` | topological polar surface area |
| `LabuteASA` | Labute approximate surface area |

## Hydrogen bonding & polarity

`NumHDonors`, `NumHAcceptors`, `NOCount` (# N+O), `NHOHCount` (# N-H and O-H bonds).

## Atom / electron counts

`HeavyAtomCount`, `NumHeteroatoms`, `NumValenceElectrons`, `NumRadicalElectrons`.

## Rings

`RingCount`, `NumAromaticRings`, `NumSaturatedRings`, `NumAliphaticRings`,
`NumAromaticCarbocycles`, `NumAromaticHeterocycles`, `NumSaturatedCarbocycles`,
`NumSaturatedHeterocycles`, `NumAliphaticCarbocycles`, `NumAliphaticHeterocycles`.

## Flexibility & shape

`NumRotatableBonds`, `FractionCsp3`, `HallKierAlpha`, `Kappa1`, `Kappa2`, `Kappa3`.

## Topological / connectivity

`BertzCT` (complexity), `BalabanJ` (branching), `Ipc` (information content),
and the connectivity indices `Chi0`–`Chi4`, `Chi0n`–`Chi4n`, `Chi0v`–`Chi4v`.

## Electronic

E-state indices: `MaxEStateIndex`, `MinEStateIndex`, `MaxAbsEStateIndex`,
`MinAbsEStateIndex`. Partial charges: `MaxPartialCharge`, `MinPartialCharge`,
`MaxAbsPartialCharge`, `MinAbsPartialCharge` (Gasteiger; can be `nan` for some atoms).

## Fingerprint density

`FpDensityMorgan1`, `FpDensityMorgan2`, `FpDensityMorgan3`.

## MOE-style VSA families

Surface-area contributions binned by an atomic property:

- `PEOE_VSA1`–`PEOE_VSA14` (partial charge)
- `SMR_VSA1`–`SMR_VSA10` (molar refractivity)
- `SLogP_VSA1`–`SLogP_VSA12` (logP)
- `EState_VSA1`–`EState_VSA11` and `VSA_EState1`–`VSA_EState10` (E-state)

## BCUT2D

Burden-matrix eigenvalue descriptors: `BCUT2D_MWHI/MWLOW`, `BCUT2D_CHGHI/CHGLO`,
`BCUT2D_LOGPHI/LOGPLOW`, `BCUT2D_MRHI/MRLOW`.

## MQN & drug-likeness

- `qed` — Quantitative Estimate of Drug-likeness (0–1)
- MQN (Molecular Quantum Numbers): 42 integer feature counts, keys `mqn1`–`mqn42`
  in the batch dict.

## Filtering patterns

**Lipinski Rule of Five** (drug-like small molecules):

```python
def passes_lipinski(mol):
    return (Descriptors.MolWt(mol) <= 500
            and Descriptors.MolLogP(mol) <= 5
            and Descriptors.NumHDonors(mol) <= 5
            and Descriptors.NumHAcceptors(mol) <= 10)
```

**Lead-like** (tighter, for hit-to-lead):

```python
def is_leadlike(mol):
    return (250 <= Descriptors.MolWt(mol) <= 350
            and Descriptors.MolLogP(mol) <= 3.5
            and Descriptors.NumRotatableBonds(mol) <= 7)
```

**Complexity / diversity snapshot:**

```python
def complexity(mol):
    return {
        "BertzCT": Descriptors.BertzCT(mol),
        "NumRings": Descriptors.RingCount(mol),
        "RotBonds": Descriptors.NumRotatableBonds(mol),
        "FractionCsp3": Descriptors.FractionCsp3(mol),
        "AromaticRings": Descriptors.NumAromaticRings(mol),
    }
```

## Tips

- Select a relevant subset — most of the ~210 descriptors are redundant for any
  one task; feeding all of them to a model invites collinearity.
- Normalize/standardize before ML use.
- 3D descriptors (e.g. from `rdkit.Chem.Descriptors3D`) require an embedded
  conformer; the values above are 2D and need only a parsed graph.
