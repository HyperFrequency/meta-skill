# Datamol Conformers

`dm.conformers` generates and analyzes 3D structures. Coordinates live on the
`Mol` as RDKit `Conformer` objects, so you can hand results to any RDKit routine.

## Generate

`dm.conformers.generate(mol, n_confs=None, rms_cutoff=None, minimize_energy=False, method=None, forcefield="UFF", add_hs=True, random_seed=19)`

| Parameter | Meaning |
|---|---|
| `n_confs` | Number to embed; if `None`, chosen from the count of rotatable bonds |
| `rms_cutoff` | RMS threshold (Å) to prune near-duplicate conformers |
| `minimize_energy` | Force-field minimization after embedding — **default `False`**; set `True` to clean up geometries |
| `forcefield` | Field used when `minimize_energy=True`: `"UFF"` (default) or `"MMFF94"` |
| `method` | Embedding: `ETDG`, `ETKDG`, `ETKDGv2`, `ETKDGv3`; `None` (default) resolves to `ETKDGv3` (recommended) |
| `add_hs` | Add hydrogens before embedding (default `True`) — critical for geometry quality |
| `random_seed` | Embedding seed; **defaults to `19`**, so runs reproduce unless you change it |

```python
mol = dm.to_mol("CC(C)CCO")
mol_3d = dm.conformers.generate(mol, n_confs=50, rms_cutoff=0.5, random_seed=42)
print(mol_3d.GetNumConformers())
```

**Do not disable `add_hs` unless the molecule already carries explicit hydrogens**
— embedding on an implicit-H graph produces poor or failed geometries.

## Cluster and reduce

- `dm.conformers.cluster(mol, rms_cutoff=1.0, already_aligned=False, centroids=True)`
  — group conformers by RMSD into conformational families. Lower `rms_cutoff` =
  more, tighter clusters. With `centroids=True` (default) it returns the
  representative conformers directly; pass `centroids=False` to get the index
  clusters to feed `return_centroids` (as below).
- `dm.conformers.return_centroids(mol, conf_clusters, centroids=True)` — extract
  the representative conformer(s) from cluster output.

```python
clusters  = dm.conformers.cluster(mol_3d, rms_cutoff=1.0, centroids=False)
centroids = dm.conformers.return_centroids(mol_3d, clusters)
```

## Analyze

- `dm.conformers.rmsd(mol)` — N×N pairwise RMSD matrix (needs ≥2 conformers);
  quantifies conformational diversity.
- `dm.conformers.sasa(mol, n_jobs=1)` — Solvent Accessible Surface Area per
  conformer (FreeSASA). Values are also stored on each conformer as the property
  `rdkit_free_sasa`.

```python
sasa = dm.conformers.sasa(mol_3d, n_jobs=-1)
per_conf = mol_3d.GetConformer(0).GetDoubleProp("rdkit_free_sasa")
```

## Coordinate access and transforms

- `dm.conformers.get_coords(mol, conf_id=-1)` — `(n_atoms, 3)` NumPy array of positions.
- `dm.conformers.center_of_mass(mol, conf_id=-1, use_atoms=True)` — mass-weighted
  (or geometric, `use_atoms=False`) center.
- `dm.conformers.translate(mol, conf_id=-1, transform_matrix=...)` — reposition a
  conformer in place.

## End-to-end

```python
mol_3d   = dm.conformers.generate(dm.to_mol("CC(C)CCO"), n_confs=50, rms_cutoff=0.5)
clusters = dm.conformers.cluster(mol_3d, rms_cutoff=1.0, centroids=False)
reps     = dm.conformers.return_centroids(mol_3d, clusters)
coords   = dm.conformers.get_coords(mol_3d, conf_id=0)
```

## Concepts

- **Distance geometry** builds 3D structure from connectivity; **ETKDG** adds
  experimental torsion preferences and chemical knowledge (v3 is the current best).
- **RMS cutoff** trades count for distinctness — higher cutoff yields fewer, more
  distinct conformers.
- Force-field minimization (UFF/MMFF) is geometry cleanup, **not** QM energetics.
