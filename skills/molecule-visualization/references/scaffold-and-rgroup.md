# Scaffold Highlighting and R-Group Decomposition

Deep reference for SAR-oriented views: detecting a core scaffold, highlighting it
inside each analog, and decomposing a congeneric series into R-groups. APIs are
from `rdkit.Chem.Scaffolds.MurckoScaffold` and
`rdkit.Chem.rdRGroupDecomposition`.

## Bemis-Murcko scaffolds

The Murcko scaffold is the ring systems of a molecule plus the linkers between
them, with terminal side chains removed.

```python
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
core = MurckoScaffold.GetScaffoldForMol(mol)          # returns a Mol
core_smiles = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)   # returns SMILES

# "Generic" framework: all atoms → C, all bonds → single (topology only)
generic = MurckoScaffold.MakeScaffoldGeneric(core)
```

Use the generic framework when you want to group molecules by shape/topology
rather than exact atom identity.

## Highlighting the core inside a molecule

Given a core (auto-detected or user-supplied), find the matching atoms and pass
them to the 2D drawer (see `rdkit-2d-recipes.md` for the draw call):

```python
core = Chem.MolFromSmiles(core_smiles)           # or the Murcko core Mol
match = mol.GetSubstructMatch(core)              # tuple of atom indices, () if none
if not match:
    # core is not a substructure of mol — check aromaticity / kekulization
    ...
```

- A supplied core given as SMARTS (via `MolFromSmarts`) matches more flexibly
  (query features, wildcard atoms) than one given as SMILES.
- For symmetric cores, `GetSubstructMatches(core)` returns every mapping; pick the
  one you intend rather than defaulting to the first.
- Color the core one hue and (optionally) the complement (R-group atoms) another;
  `style-guide.md` recommends blue core / orange R-groups for colorblind safety.

## R-group decomposition across a series

`RGroupDecompose` aligns each molecule to one or more cores and returns the
substituents at each attachment point, keyed `R1`, `R2`, ….

```python
from rdkit.Chem import rdRGroupDecomposition as rdRGD

core = Chem.MolFromSmiles("c1ccc(NC(=O)c2ccccc2)cc1")
mols = [Chem.MolFromSmiles(s) for s in analog_smiles]
mols = [m for m in mols if m is not None]

groups, unmatched = rdRGD.RGroupDecompose(
    [core], mols, asSmiles=True, asRows=True
)
# groups: list of dicts, e.g. {"Core": "...", "R1": "...", "R2": "..."}
# unmatched: indices of mols that did not fit the core
```

Key parameters:

- `asRows=True` → one dict per molecule (row-oriented, easy to tabulate);
  `asRows=False` → one dict of columns (`{"R1": [...], "R2": [...]}`).
- `asSmiles=True` → values are SMILES strings; `False` → RDKit Mols (needed if you
  want to draw each R-group).
- Pass **multiple cores** in the list to decompose a mixed series; RGD assigns each
  molecule to the best-matching core.
- Always inspect `unmatched` — molecules that lack the core are silently dropped
  from `groups`, which will otherwise skew an SAR table.

Fine control lives in `rdRGD.RGroupDecompositionParameters()` (e.g.
`onlyMatchAtRGroups`, `removeHydrogensPostMatch`, labeling strategy). Construct it,
set fields, and pass it to `RGroupDecompose`.

## Rendering the R-group table

With `asSmiles=False`, each `R1`/`R2` value is a Mol you can draw. Two common
layouts:

1. **Column of decorated analogs** — draw each full molecule with its core
   highlighted (grid from `rdkit-2d-recipes.md`, `highlightAtomLists` set to each
   core match).
2. **Core + R-group matrix** — draw the shared core once, then a grid of the
   distinct R-group fragments per position, labeled `R1`, `R2`, ….

Attachment points appear as dummy atoms (`*`, atomic num 0). Keep them visible so
the reader can see where each substituent connects.

## Failure modes

- **Empty match / everything unmatched** — the core's aromaticity perception
  differs from the analogs. Sanitize consistently, or express the core as SMARTS.
- **R-groups landing on the wrong label** — attachment-point numbering depends on
  core atom order; fix the core atom map numbers (`[*:1]`, `[*:2]`) to pin labels.
- **A single molecule dominates the scaffold** — Murcko strips side chains but
  keeps all rings; a fused polycyclic core may be larger than intended. Supply an
  explicit core when the auto-detected one is too permissive.
