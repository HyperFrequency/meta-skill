# Molecule Handling (`stjames.Molecule`)

Rowan's full workflow API takes `stjames.Molecule` objects. This is the canonical
input for `submit_*_workflow(initial_molecule=…)`.

## Constructing molecules

```python
import stjames

stjames.Molecule.from_smiles("CCO")                 # 3D coords generated automatically
stjames.Molecule.from_smiles("C[C@H](O)[C@@H](O)C") # stereochemistry preserved
stjames.Molecule.from_xyz(xyz_string)               # from an XYZ block
stjames.Molecule.from_file("structure.xyz")         # from a file path
stjames.Molecule.from_extxyz(extxyz_string)         # extended XYZ (forces, lattice)
stjames.Molecule.from_rdkit(rdkit_mol)              # from an embedded RDKit Mol
```

For extended XYZ, periodic systems expose `mol.cell.lattice_vectors`.

### Charge and multiplicity

Defaults are neutral singlet. Set both explicitly for ions and radicals:

```python
stjames.Molecule.from_smiles("CC(=O)[O-]", charge=-1, multiplicity=1)  # acetate
stjames.Molecule.from_smiles("[O][O]",       charge=0,  multiplicity=3)  # triplet O2
```

`stjames.Molecule` validates that `electrons = Σ(atomic_number) − charge` is
consistent with the multiplicity (odd/even) and raises `ValueError` otherwise — e.g.
requesting singlet O₂ fails. This catches many silent errors before you spend
credits, so let it: do not swallow the exception, fix the charge/spin.

## Reading properties

```python
mol.charge, mol.multiplicity, len(mol.atoms)
```

After a calculation populates them:

```python
mol.energy                     # Hartree
mol.dipole                     # (x, y, z), Debye
mol.mulliken_charges, mol.mulliken_spin_densities
```

After a frequency calculation:

```python
mol.zero_point_energy
mol.thermal_correction_enthalpy, mol.thermal_correction_gibbs
mol.gibbs_free_energy
for mode in mol.vibrational_modes:
    mode.frequency, mode.reduced_mass, mode.ir_intensity, mode.displacements
```

## Geometry queries

```python
mol.distance(0, 1)                              # Å
mol.angle(0, 1, 2, degrees=True)                # degrees (or radians)
mol.dihedral(0, 1, 2, 3, degrees=True, positive_domain=True)  # 0–360 domain
mol.translated([1.0, 0.0, 0.0])                 # returns a shifted copy
```

## Atoms

Each entry of `mol.atoms` is an `Atom` with `element`, `atomic_number`, and
Cartesian `x`, `y`, `z` (Å):

```python
import numpy as np
positions = np.array([[a.x, a.y, a.z] for a in mol.atoms])  # (N, 3)
```

## File output

```python
mol.to_xyz(comment="optimized")                 # returns an XYZ string
mol.to_xyz(comment="…", out_file="mol.xyz")     # writes to disk
```

## Convenience conversions (from the `rowan` client)

```python
import rowan
rowan.smiles_to_stjames("CCO")                  # SMILES → stjames.Molecule
rowan.molecule_lookup("aspirin")                # common name → SMILES string
```

Chain them to submit by name:

```python
mol = stjames.Molecule.from_smiles(rowan.molecule_lookup("ibuprofen"))
rowan.submit_pka_workflow(mol, name="ibuprofen pKa")
```

## Batch construction, defensively

`from_smiles` can raise on malformed input — build in a guarded loop so one bad
string doesn't abort the batch:

```python
molecules = []
for smi in smiles_list:
    try:
        molecules.append(stjames.Molecule.from_smiles(smi))
    except Exception as e:
        print(f"skip {smi}: {e}")
```
