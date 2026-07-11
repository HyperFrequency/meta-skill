# Datamol Core API

Functions in the top-level `dm.` namespace. All molecule objects are native
`rdkit.Chem.Mol`, so anything here interoperates with RDKit and the `rdkit` skill.

## Parse and Convert

| Function | Purpose |
|---|---|
| `dm.to_mol(smiles_or_repr)` | SMILES (or other representation) → `Mol`; returns `None` on failure |
| `dm.from_inchi(inchi)` | InChI → `Mol` |
| `dm.from_smarts(smarts)` | SMARTS pattern → query `Mol` |
| `dm.from_selfies(selfies)` | SELFIES → `Mol` |
| `dm.copy_mol(mol)` | Deep copy so in-place edits don't mutate the original |

Export the other direction:

| Function | Notes |
|---|---|
| `dm.to_smiles(mol, canonical=True, isomeric=True, kekulize=False)` | Canonical SMILES; `isomeric=True` keeps stereochemistry |
| `dm.to_inchi(mol)` / `dm.to_inchikey(mol)` | InChI string / fixed-length hash key |
| `dm.to_smarts(mol)` | SMARTS pattern string |
| `dm.to_selfies(mol)` | SELFIES (robust to invalid mutations, useful for generative models) |

```python
mol = dm.to_mol("CC(=O)O")            # acetic acid
if mol is None:
    raise ValueError("bad SMILES")
key = dm.to_inchikey(mol)             # stable dedup key for a library
```

## Standardize and Repair

Always standardize structures from external sources before comparing or featurizing.

- `dm.sanitize_mol(mol)` — a more forgiving sanitize than raw RDKit; does a
  mol→SMILES→mol round-trip and fixes aromatic-nitrogen issues. Returns `None` if
  it cannot recover the structure.
- `dm.standardize_mol(mol, disconnect_metals=False, normalize=True, reionize=True, uncharge=False, stereo=True)`
  — full cleanup: metal disconnection, functional-group normalization,
  reionization, largest-fragment selection.
- `dm.standardize_smiles(smiles)` — same, straight from a string.
- `dm.fix_mol(mol)` / `dm.fix_valence(mol)` — attempt automatic structure/valence repair.

Utility structure ops: `dm.reorder_atoms(mol)` (canonical atom order for
reproducible features), `dm.add_hs(mol)`, `dm.remove_hs(mol)`.

## Fingerprints and Similarity

`dm.to_fp(mol, fp_type="ecfp", radius=2, ...)` builds a fingerprint (NumPy array by
default). Supported `fp_type` values:

| `fp_type` | Description |
|---|---|
| `"ecfp"` | Extended-connectivity (Morgan) — general-purpose structural similarity |
| `"fcfp"` | Feature-based connectivity fingerprint |
| `"maccs"` | 166-key MACCS — fast, small, coarse |
| `"topological"` | RDKit topological (path-based) |
| `"atompair"` | Atom pairs with topological distance |

Extra keyword arguments (`radius`, bit size, etc.) pass through to the underlying
RDKit generator; if you need exact control of the generator, use `rdkit` directly.

Similarity is expressed as **Tanimoto distance** (`0` identical, `1` most different):

- `dm.pdist(mols, n_jobs=-1)` — condensed pairwise distance matrix within one set.
- `dm.cdist(mols_a, mols_b, n_jobs=-1)` — distances between two sets.

```python
from scipy.spatial.distance import squareform
full = squareform(dm.pdist(mols))          # N×N; convert to similarity with 1 - full
```

## Clustering and Diversity

- `dm.cluster_mols(mols, cutoff=0.2, n_jobs=1)` — Butina clustering. Returns a
  **tuple** `(cluster_indices, cluster_mols)`: the first is a list of clusters of
  molecule **indices**, the second the same clusters as `Mol` objects. `cutoff` is a
  distance threshold (smaller = tighter clusters). Builds a full distance matrix, so
  keep the input to a few thousand molecules.
- `dm.pick_diverse(mols, npick)` — MaxMin diversity pick of `npick` molecules.
  Returns `(indices, picked_mols)`; scales better than clustering for large sets.
- `dm.pick_centroids(mols, npick, threshold=0.5, method="sphere")` —
  representative/centroid molecules. Also returns `(indices, picked_mols)`.

```python
cluster_indices, cluster_mols = dm.cluster_mols(mols, cutoff=0.3, n_jobs=-1)
for i, idxs in enumerate(cluster_indices):
    members = [mols[j] for j in idxs]
```

## DataFrame Bridges and Graphs

- `dm.to_df(mols, smiles_column="smiles", mol_column="mol")` — molecules → DataFrame.
- `dm.from_df(df, smiles_column="smiles", mol_column="mol")` — DataFrame → molecules.
- `dm.to_graph(mol)` — molecular graph for graph-based analysis.
- `dm.get_all_path_between(mol, start, end)` — all atom paths between two atoms.

## Generic Parallel Map

`dm.parallelized(fn, inputs, n_jobs=-1, progress=True, batch_size="auto")` maps any
callable over an iterable with the same parallel/progress conventions as the batch
functions — the escape hatch when a specific op lacks a built-in `n_jobs`.

```python
scaffolds = dm.parallelized(dm.to_scaffold_murcko, mols, n_jobs=-1, progress=True)
```
