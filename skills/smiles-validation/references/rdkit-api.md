# RDKit API Reference for SMILES Validation

Every check in this skill maps to a small, well-defined set of RDKit calls.
This file documents those calls, their parameters, and the chemistry pitfalls
that make a naive validator wrong. RDKit is BSD-3-Clause licensed.

## Parsing and sanitization

```python
from rdkit import Chem

mol = Chem.MolFromSmiles(smiles)   # returns a Mol, or None on failure
```

`MolFromSmiles` returns `None` for anything it cannot parse. A `None` result is
the primary invalidity signal — always check it before touching `mol`.

By default `MolFromSmiles` already runs full sanitization, so a non-`None`
result is normally valid. Call sanitization explicitly only when you parse with
`sanitize=False` (e.g. to inspect a broken molecule):

```python
mol = Chem.MolFromSmiles(smiles, sanitize=False)
problems = Chem.DetectChemistryProblems(mol)   # list of typed problem objects
Chem.SanitizeMol(mol)                            # raises on valence/kekulization errors
```

`SanitizeMol` raises (commonly a `Chem.rdchem.AtomValenceException` or
`KekulizeException`); wrap it in `try/except` and record the message. Silence
RDKit's C++ logger so warnings do not pollute stdout:

```python
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")     # or: RDLogger.logger().setLevel(RDLogger.ERROR)
```

### Cheap syntactic pre-checks

Before parsing, unbalanced `()` or `[]` counts are a fast, human-readable
diagnostic (RDKit will also reject them, but with a less specific message):

```python
smiles.count("(") == smiles.count(")")
smiles.count("[") == smiles.count("]")
```

These are advisory hints, not a substitute for `MolFromSmiles`.

## Canonicalization and descriptors

```python
from rdkit.Chem import Descriptors

canonical = Chem.MolToSmiles(mol)                       # canonical SMILES
formula   = Chem.rdMolDescriptors.CalcMolFormula(mol)   # e.g. "C6H6"
mw        = Descriptors.MolWt(mol)                       # average molecular weight (float)
n_atoms   = mol.GetNumAtoms()                            # explicit atoms (H implicit)
heavy     = Descriptors.HeavyAtomCount(mol)              # non-H atoms
```

Canonicalization is what makes two different SMILES for the same molecule
compare equal — always compare canonical forms, never raw strings.

Reasonable warning bounds (advisory, do not fail validation):

- `GetNumAtoms() < 3` — degenerate / fragment-like.
- `GetNumAtoms() > 150` — unusually large; likely a peptide/polymer or an error.
- `MolWt > 1000` — outside typical small-molecule / drug-like space.

## Morgan fingerprints and Tanimoto similarity

Prefer the modern generator API (RDKit >= 2022.09). The old
`AllChem.GetMorganFingerprintAsBitVect` still works but emits deprecation
warnings.

```python
from rdkit.Chem import rdFingerprintGenerator
from rdkit import DataStructs

gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
fp1 = gen.GetFingerprint(mol1)
fp2 = gen.GetFingerprint(mol2)
similarity = DataStructs.TanimotoSimilarity(fp1, fp2)    # 0.0 - 1.0
```

Legacy equivalent (use only if the generator import is unavailable):

```python
from rdkit.Chem import AllChem
fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
```

Parameter notes:

- `radius=2` (ECFP4-like) is the standard default for medicinal-chemistry
  similarity. `radius=3` (ECFP6) is more specific.
- `fpSize` / `nBits=2048` balances collision rate vs memory. Both fingerprints
  in a comparison must use identical radius and size.
- Tanimoto is symmetric and bounded in `[0, 1]`; `1.0` means identical bit sets
  (not necessarily identical molecules — different molecules can collide, and
  stereoisomers share a 2D fingerprint).

## Murcko scaffolds

Two scaffold notions matter:

```python
from rdkit.Chem.Scaffolds import MurckoScaffold

bemis_murcko = MurckoScaffold.GetScaffoldForMol(mol)          # rings + linkers, atoms kept
generic      = MurckoScaffold.MakeScaffoldGeneric(bemis_murcko)  # all atoms -> C, bonds -> single
scaffold_key = Chem.MolToSmiles(generic)
```

- `GetScaffoldForMol` returns the Bemis-Murcko scaffold: ring systems plus the
  linkers between them, side chains stripped.
- `MakeScaffoldGeneric` erases element and bond-order identity, leaving pure
  topology. Comparing generic scaffolds asks "is this the same molecular
  framework?" — the right question for judging whether a lead-optimization edit
  kept the core. Comparing plain Bemis-Murcko scaffolds is stricter (element
  identity matters).
- Both can raise on unusual inputs (e.g. acyclic molecules yield an empty
  scaffold); wrap in `try/except` and report `None` rather than crashing.

## Maximum common substructure (MCS)

```python
from rdkit.Chem import rdFMCS

result = rdFMCS.FindMCS([mol1, mol2], timeout=10)
result.numAtoms       # atoms in the common core
result.numBonds
result.smartsString   # SMARTS of the MCS (empty if none / timed out)
result.canceled       # True if the timeout fired before completion
```

Always pass a `timeout` — MCS is NP-hard and can hang on large, symmetric
molecules. Check `canceled`; a timed-out result is a lower bound, not the true
MCS. `FindMCS` accepts tuning args (`atomCompare`, `bondCompare`,
`ringMatchesRingOnly`, `completeRingsOnly`) when you need stricter matching.

## SMARTS substructure matching (modification checks)

```python
pattern = Chem.MolFromSmarts("[OH]")     # SMARTS query; None if the pattern is malformed
present = mol.HasSubstructMatch(pattern)
count   = len(mol.GetSubstructMatches(pattern))
```

Modification verification compares `HasSubstructMatch` on the original vs the
proposed molecule to decide whether a group was added (`present in new, absent
in old`), removed (`absent in new, present in old`), or simply present. See
`cli-reference.md` for the keyword→SMARTS table. Substructure counts (via
`GetSubstructMatches`) catch the case where a group is duplicated rather than
introduced.

## Chemistry gotchas

- **Aromaticity models** — RDKit perceives aromaticity on sanitization;
  lowercase (`c1ccccc1`) and Kekulé (`C1=CC=CC=C1`) inputs canonicalize to the
  same molecule. Do not treat them as different.
- **Stereochemistry** — 2D Morgan fingerprints and generic scaffolds ignore
  `@`/`@@` and `/`,`\`. Two stereoisomers will look identical here; if stereo
  matters, compare canonical SMILES with `Chem.MolToSmiles(mol,
  isomericSmiles=True)` (the default) or use chirality-aware fingerprints.
- **Salts, mixtures, fragments** — a dot-separated SMILES (`CC(=O)O.[Na+]`) is
  multiple fragments. Strip counterions with `rdkit.Chem.SaltRemover` or take
  the largest fragment before comparing if you only care about the parent.
- **Isotopes / charges** — valid but affect formula and MW; they are not
  errors.
- **Tautomers** — RDKit does not auto-canonicalize tautomers by default; two
  tautomers are distinct molecules here. Use `rdMolStandardize.TautomerEnumerator`
  (in the `rdkit`/`datamol` skills) if you need tautomer-insensitive comparison.
- **Radicals / explicit H mismatches** — often the real reason a "valid-looking"
  SMILES fails sanitization; inspect the `SanitizeMol` exception message.
