# Datamol Descriptors and Visualization

## `dm.descriptors` — molecular properties

### Single molecule

`dm.descriptors.compute_many_descriptors(mol, properties_fn=None, add_properties=True)`
returns a `dict` of the standard descriptor set:

```python
d = dm.descriptors.compute_many_descriptors(dm.to_mol("CCO"))
# {'mw': 46.07, 'clogp': -0.0014, 'n_lipinski_hba': 1, 'n_lipinski_hbd': 1,
#  'tpsa': 20.23, 'n_rotatable_bonds': 0, 'n_rings': 0, 'qed': 0.41, 'fsp3': 1.0, ...}
```

Default keys (exact spelling matters — these become the DataFrame columns):
`mw`, `fsp3`, `n_lipinski_hba`, `n_lipinski_hbd`, `n_rings`, `n_hetero_atoms`,
`n_heavy_atoms`, `n_rotatable_bonds`, `n_radical_electrons`, `tpsa`, `qed`, `clogp`,
`sas`, and the aromatic/aliphatic/saturated ring-count breakdowns. **Note:** LogP is
`clogp`, H-bond acceptors/donors are `n_lipinski_hba` / `n_lipinski_hbd` — there is no
`logp`, `hba`, `hbd`, or `n_aromatic_atoms` column (aromatic-atom count is the
separate function below).

### Batch (parallel) → DataFrame

`dm.descriptors.batch_compute_many_descriptors(mols, n_jobs=1, batch_size=None, progress=False)`
returns a DataFrame, one row per molecule — the workhorse for filtering libraries:

```python
df = dm.descriptors.batch_compute_many_descriptors(mols, n_jobs=-1, progress=True)
druglike = df[(df.mw <= 500) & (df.clogp <= 5) & (df.n_lipinski_hbd <= 5) & (df.n_lipinski_hba <= 10)]
```

### Specialized counts

| Function | Returns |
|---|---|
| `dm.descriptors.n_aromatic_atoms(mol)` | Count of aromatic atoms |
| `dm.descriptors.n_aromatic_atoms_proportion(mol)` | Aromatic atoms / heavy atoms (0–1) |
| `dm.descriptors.n_charged_atoms(mol)` | Atoms with nonzero formal charge |
| `dm.descriptors.n_rigid_bonds(mol)` | Non-rotatable, non-ring bonds |
| `dm.descriptors.n_stereo_centers(mol)` | Stereogenic (chiral) centers |
| `dm.descriptors.n_stereo_centers_unspecified(mol)` | Stereocenters lacking assignment |

### Reaching any RDKit descriptor

`dm.descriptors.any_rdkit_descriptor(name)` fetches a descriptor function by name
from `rdkit.Chem.Descriptors` / `rdMolDescriptors`:

```python
tpsa = dm.descriptors.any_rdkit_descriptor("TPSA")(mol)
```

### Filtering recipes

```python
# Lipinski Rule of Five (single molecule)
d = dm.descriptors.compute_many_descriptors(mol)
is_druglike = (d["mw"] <= 500 and d["clogp"] <= 5
               and d["n_lipinski_hbd"] <= 5 and d["n_lipinski_hba"] <= 10)

# ADME-style filter over a library (TPSA proxy for BBB penetration)
df = dm.descriptors.batch_compute_many_descriptors(library, n_jobs=-1)
bbb = df[df.tpsa < 90]
```

---

## `dm.viz` — rendering molecules

### Grid images

`dm.viz.to_image(mols, legends=None, n_cols=4, mol_size=(300,300), use_svg=True, highlight_atom=None, highlight_bond=None, align=False, outfile=None, max_mols=32, indices=False)`
renders one molecule or a list into an image grid. **`max_mols` defaults to `32`** —
larger lists are silently truncated, so raise it (or slice) to render more.

```python
# Labeled grid, saved to PNG (use_svg=False for raster output)
dm.viz.to_image(mols[:20], legends=[dm.to_smiles(m) for m in mols[:20]],
                n_cols=5, use_svg=False, outfile="grid.png")

# SVG for publications
dm.viz.to_image(mols, use_svg=True, outfile="grid.svg")

# Aligned by maximum common substructure — the right choice for SAR series
dm.viz.to_image(series, align=True, legends=[f"{a:.2f}" for a in activities])

# Highlight specific atoms/bonds
dm.viz.to_image(mol, highlight_atom=[0, 1, 2], highlight_bond=[0, 1])
```

Returns an image object (renders inline in Jupyter) or writes to `outfile`
(local or remote via `fsspec`). Prefer `outfile` for large grids to avoid holding
the whole image in memory.

### Conformer grid

`dm.viz.conformers(mol, n_confs=None, align_conf=True, n_cols=3, sync_views=True, remove_hs=True)`
displays multiple 3D conformers side by side — pass a `Mol` that already has
embedded conformers (see `references/conformers.md`).

### Circle grid

`dm.viz.circle_grid(center_mol, ring_mols, act_mapper=None, margin=50, align=None, use_svg=True, outfile=None)`
draws a central molecule ringed by neighbors — handy for similarity neighborhoods
and SAR. `ring_mols` is a **list of lists** (one inner list per concentric ring);
`act_mapper` color-codes by activity.

### Tips

- Always pass `legends` (SMILES, IDs, or activity values) so figures are readable.
- Use `align=True` whenever you compare structurally related molecules.
- `use_svg=True` for scalable, publication-quality output.
