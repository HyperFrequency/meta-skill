# RDKit-Native Helpers

These functions take RDKit `Mol` objects, handle submission and waiting internally,
and return typed result objects — no `Workflow` bookkeeping. Use them for quick,
one-call calculations wired into an existing RDKit pipeline; use the full workflow
API ([api_reference.md](api_reference.md)) when you need folders, method overrides,
or fine-grained control.

Each capability comes in a single-molecule `run_*` form and a parallel `batch_*`
form. Batch functions distribute across Rowan's cluster and return a list aligned to
the input, with `None` in slots that failed — **always guard for `None`**.

## pKa

```python
from rdkit import Chem
import rowan

res = rowan.run_pka(Chem.MolFromSmiles("c1ccccc1O"))
res.strongest_acid, res.strongest_base, res.microscopic_pkas, res.tautomer_populations

results = rowan.batch_pka([Chem.MolFromSmiles(s) for s in smiles_list])  # list[PKAResult | None]
```

## Tautomers

```python
res = rowan.run_tautomers(mol)
res.tautomers    # list[rdkit.Chem.Mol]
res.energies     # kcal/mol, relative
res.populations  # Boltzmann populations at 298 K

rowan.batch_tautomers(mols)  # list[TautomerResult | None]
```

## Conformers

```python
res = rowan.run_conformers(mol)
res.conformers               # list[Mol] with 3D coords
res.energies                 # Hartree
res.lowest_energy_conformer  # Mol
res.energy_range             # kcal/mol span
res.boltzmann_weights

rowan.batch_conformers(mols)  # list[ConformerResult | None]
```

## Single-point energy

Requires 3D coordinates on the input molecule:

```python
from rdkit.Chem import AllChem
mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))
AllChem.EmbedMolecule(mol); AllChem.MMFFOptimizeMolecule(mol)

res = rowan.run_energy(mol)
res.energy            # Hartree
res.dipole            # (x, y, z)
res.dipole_magnitude  # Debye
res.mulliken_charges

rowan.batch_energy(mols_with_3d)  # list[EnergyResult | None]
```

## Geometry optimization

```python
res = rowan.run_optimization(mol)   # 3D coords optional; embedded if absent
res.molecule   # optimized rdkit.Chem.Mol
res.energy     # Hartree
res.converged  # bool
res.n_steps

rowan.batch_optimization(mols)  # list[OptimizationResult | None]
```

## Patterns

### Guarded single-molecule call

```python
def safe_pka(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, "invalid SMILES"
    try:
        return rowan.run_pka(mol), None
    except rowan.RowanAPIError as e:
        return None, f"API error: {e}"
```

### Filter locally, compute in the cloud

Cut cloud cost by pruning with cheap local RDKit descriptors first, then batching
only survivors:

```python
from rdkit.Chem import Descriptors
keep = [m for m in mols if m and Descriptors.MolWt(m) < 500]
pka = rowan.batch_pka(keep)
```

### Screening table

```python
import pandas as pd
from rdkit.Chem import Descriptors

mols = [(s, Chem.MolFromSmiles(s)) for s in library]
valid = [(s, m) for s, m in mols if m]
pkas = rowan.batch_pka([m for _, m in valid])
df = pd.DataFrame({
    "smiles": [s for s, _ in valid],
    "mw":  [Descriptors.MolWt(m)   for _, m in valid],
    "logp":[Descriptors.MolLogP(m) for _, m in valid],
    "pka": [r.strongest_acid if r else None for r in pkas],
})
```

## Native vs full API

| | RDKit-native | Full workflow API |
|---|---|---|
| Input | RDKit `Mol` | `stjames.Molecule` |
| Output | typed result (RDKit Mol + fields) | `Workflow` object |
| Waiting | automatic (blocks) | manual `wait`/`fetch` |
| Folders / projects | no | yes |
| Method / parameter control | defaults only | full |

Notes: batch functions are cheaper than looping single calls; low-cost jobs may bill
fractional credits; previously computed molecules can return faster from cache.
