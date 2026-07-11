# Datamol Scaffolds and Fragments

## Scaffolds

Scaffolds capture the shared core of a molecule — useful for grouping structural
families and for scaffold-based train/test splits in ML.

### Bemis-Murcko

`dm.to_scaffold_murcko(mol)` removes side chains and returns the framework
(ring systems plus the linkers between them) as a `Mol`.

```python
scaffold = dm.to_scaffold_murcko(dm.to_mol("c1ccc(cc1)CCN"))
dm.to_smiles(scaffold)   # benzene ring + linker
```

Frequency analysis over a library:

```python
from collections import Counter
scaf_smiles = [dm.to_smiles(dm.to_scaffold_murcko(m)) for m in mols]
top = Counter(scaf_smiles).most_common(10)
```

### Fuzzy scaffolds

`dm.scaffold.fuzzy_scaffolding(mols, ...)` produces scaffolds with enforceable
groups that must appear in the core — a more flexible definition than strict
Murcko rules for custom series.

### Scaffold split for ML

Keep train and test compounds structurally distinct so metrics don't leak:

```python
groups = {}
for m, s in zip(mols, scaf_smiles):
    groups.setdefault(s, []).append(m)

import random
scaffolds = list(groups); random.shuffle(scaffolds)
cut = int(0.8 * len(scaffolds))
train = [m for s in scaffolds[:cut] for m in groups[s]]
test  = [m for s in scaffolds[cut:] for m in groups[s]]
```

## Fragmentation — `dm.fragment`

Breaks molecules at chemically meaningful bonds; attachment points show up as
`[1*]`, `[2*]`, ... in a fragment's SMILES.

**Return types differ — this bites people:**
- `dm.fragment.brics(mol)` and `dm.fragment.recap(mol)` return a **`list` of `Mol`
  objects**, and — unless you pass `remove_parent=True` — the **parent molecule is
  included** in that list. Convert to SMILES with `dm.to_smiles` before deduping,
  counting, or set operations (two `Mol` objects never compare equal by identity).
- `dm.fragment.mmpa_frag(mol)` returns a **`set` of SMILES strings**.

| Function | Method | Best for |
|---|---|---|
| `dm.fragment.brics(mol, remove_parent=False)` | BRICS — 16 retrosynthetic bond types, preserves rings | Retrosynthetic analysis, fragment recombination |
| `dm.fragment.recap(mol, remove_parent=False)` | RECAP — hierarchical retrosynthetic cleavage | Combinatorial library design |
| `dm.fragment.mmpa_frag(mol, max_cut=1)` | Matched-Molecular-Pair fragmentation | SAR — how a single change shifts a property |

```python
frags  = dm.fragment.brics(dm.to_mol("c1ccccc1CCN"), remove_parent=True)  # list[Mol]
smiles = [dm.to_smiles(f) for f in frags]     # e.g. ['[16*]c1ccccc1', '[4*]CCN', ...]
```

### Fragment analysis across a library

```python
from collections import Counter
all_frags = []
for m in mols:
    # count by SMILES, not Mol identity — brics returns Mol objects
    all_frags.extend(dm.to_smiles(f) for f in dm.fragment.brics(m, remove_parent=True))
common = Counter(all_frags).most_common(20)
```

### Fragment-overlap scoring (simple fragment-based screen)

```python
def brics_smiles(mol):
    # set operations need SMILES strings, not Mol objects
    return {dm.to_smiles(f) for f in dm.fragment.brics(mol, remove_parent=True)}

active_frags = set()
for m in actives:
    active_frags |= brics_smiles(m)

def score(mol):
    fr = brics_smiles(mol)
    return len(fr & active_frags) / len(fr) if fr else 0.0
```

## Concepts

- **Attachment points** (`[1*]`) mark where a fragment reconnects; strip or cap
  them (e.g. replace with `[H]`) before turning a fragment back into a molecule.
- Fragmentation mimics **synthetic disconnections**, so fragments are, in
  principle, recombinable into valid structures.
