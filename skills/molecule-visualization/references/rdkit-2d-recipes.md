# RDKit 2D Drawing and Grid Recipes

Deep reference for single-molecule depictions and annotated grids. All APIs are
from RDKit (`rdkit.Chem`, `rdkit.Chem.Draw`, `rdkit.Chem.Draw.rdMolDraw2D`).

## Drawer selection

| Drawer | Output | When |
|--------|--------|------|
| `rdMolDraw2D.MolDraw2DCairo(w, h)` | PNG bytes | Screen, slides, quick previews |
| `rdMolDraw2D.MolDraw2DSVG(w, h)` | SVG text | Print / publications (scales losslessly) |

Both share the same drawing calls; only how you retrieve the result differs
(`GetDrawingText()` returns `bytes` for Cairo, `str` for SVG).

## Minimal, robust single-molecule pipeline

```python
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import rdMolDraw2D

def draw(smiles, path, size=(400, 300), legend="",
         highlight_atoms=None, highlight_color=(1.0, 0.5, 0.5),
         show_indices=False, kekulize=True):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"unparseable SMILES: {smiles!r}")
    AllChem.Compute2DCoords(mol)
    if kekulize:
        try:
            Chem.Kekulize(mol, clearAromaticFlags=False)
        except Chem.KekulizeException:
            pass  # keep aromatic form if a ring will not kekulize

    is_svg = path.lower().endswith(".svg")
    drawer = (rdMolDraw2D.MolDraw2DSVG if is_svg else rdMolDraw2D.MolDraw2DCairo)(*size)

    opts = drawer.drawOptions()
    opts.bondLineWidth = 2
    opts.clearBackground = True          # set False for transparent PNG
    opts.addStereoAnnotation = True
    if show_indices:
        opts.addAtomIndices = True

    atom_colors = {}
    bonds, bond_colors = [], {}
    atoms = highlight_atoms or []
    for i in atoms:
        atom_colors[i] = highlight_color
    for b in mol.GetBonds():
        a1, a2 = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if a1 in atoms and a2 in atoms:
            bonds.append(b.GetIdx())
            bond_colors[b.GetIdx()] = highlight_color

    drawer.DrawMolecule(mol, legend=legend,
                        highlightAtoms=list(atoms), highlightAtomColors=atom_colors,
                        highlightBonds=bonds, highlightBondColors=bond_colors)
    drawer.FinishDrawing()
    data = drawer.GetDrawingText()
    mode = "w" if is_svg else "wb"
    with open(path, mode) as f:
        f.write(data)
```

## Commonly used `drawOptions()` fields

| Field | Effect |
|-------|--------|
| `bondLineWidth` | Bond stroke width (px); 2 is a good default |
| `addAtomIndices` | Label every atom with its 0-based index |
| `addStereoAnnotation` | Show R/S and E/Z labels |
| `clearBackground` | `False` → transparent background (PNG) |
| `additionalAtomLabelPadding` | Extra space around heteroatom labels |
| `fixedBondLength` | Force a constant bond length across figures |
| `annotationFontScale` | Scale index / note font relative to atom labels |

Per-atom notes (arbitrary text, not just indices):

```python
for atom in mol.GetAtoms():
    atom.SetProp("atomNote", str(atom.GetIdx()))   # or any label
```

## Per-atom / per-substructure highlighting

- `highlightAtoms` + `highlightAtomColors` (dict of `idx → (r,g,b)` floats 0-1).
- To highlight a substructure, get its atoms from a match and pass them:

```python
patt = Chem.MolFromSmarts("c1ccccc1")
atoms = mol.GetSubstructMatch(patt)          # tuple of atom indices
```

- `GetSubstructMatch` returns the **first** match only; use
  `GetSubstructMatches` for all matches (important for symmetric molecules).

## Grids with `MolsToGridImage`

Prefer the built-in grid over manual PIL composition — it handles layout,
legends, and SVG/PNG switching for you.

```python
from rdkit.Chem import Draw
img = Draw.MolsToGridImage(
    mols, molsPerRow=4, subImgSize=(300, 250),
    legends=legends,          # one string per mol; "\n" allowed
    useSVG=True,              # SVG string; False → PIL Image (PNG-able)
    highlightAtomLists=None,  # optional: list-of-lists, per-mol highlights
)
```

- `useSVG=True` returns an SVG string you write to `.svg`.
- `useSVG=False` returns a PIL `Image`; call `img.save("grid.png")`.
- Keep `subImgSize` large enough that multi-line legends are not clipped.

## Descriptor cheat sheet (for grid legends / annotations)

| Value | Call |
|-------|------|
| Molecular formula | `from rdkit.Chem import rdMolDescriptors; rdMolDescriptors.CalcMolFormula(mol)` |
| Molecular weight | `Descriptors.MolWt(mol)` |
| cLogP (Crippen) | `Descriptors.MolLogP(mol)` |
| TPSA | `rdMolDescriptors.CalcTPSA(mol)` |
| H-bond donors / acceptors | `rdMolDescriptors.CalcNumHBD(mol)` / `CalcNumHBA(mol)` |
| QED (drug-likeness 0-1) | `from rdkit.Chem import QED; QED.qed(mol)` |
| Canonical SMILES | `Chem.MolToSmiles(mol)` |

Note: the legacy `Descriptors.MolecularFormula` name does **not** exist — use
`rdMolDescriptors.CalcMolFormula`.

## CSV-driven grids

Read `name,smiles` (plus optional precomputed property columns), parse each
SMILES, skip rows where `MolFromSmiles` is `None`, cap the count for readability
(e.g. 20-30 mols), and build `legends` from the columns you want to show. Reading
properties from the CSV avoids recomputing and lets you display externally-sourced
values (assay data, model scores) that RDKit cannot derive.

## Format and resolution guidance

- **SVG** for anything going to print — it is resolution-independent and editable
  in Illustrator/Inkscape.
- **PNG** at the right pixel dimensions for screen; there is no DPI metadata knob
  on the Cairo drawer, so size the canvas in pixels to hit your target print size
  (e.g. 400 px ≈ 1.3 in at 300 DPI). See `style-guide.md` for the size tables.
