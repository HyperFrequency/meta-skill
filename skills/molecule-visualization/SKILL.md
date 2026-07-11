---
name: molecule-visualization
version: 0.1.0
description: >-
  Render publication-quality molecular graphics with RDKit and py3Dmol: 2D
  structure depictions (PNG/SVG) with atom/bond highlighting and indices,
  multi-molecule grids annotated with descriptors (QED, MW, LogP, TPSA),
  Murcko-scaffold and R-group SAR views, distance-based protein-ligand contact
  diagrams, and self-contained interactive 3D viewers for proteins, ligands,
  complexes, binding pockets, and ranked docking poses. Use when you need
  figures for papers, patents, slide decks, or SAR/binding-mode analysis in
  medicinal or computational chemistry. Do NOT use for 2D→3D conformer
  generation or geometry optimization, ML property/activity prediction, MD
  trajectory rendering, general non-molecular data plots (use
  `scientific-visualization`), conceptual schematics (use
  `scientific-schematics`), or rigorous interaction fingerprinting (reach for
  PLIP or ProLIF instead).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "RDKit: BSD-3-Clause; py3Dmol: BSD-3-Clause; Biopython: BSD-3-Clause"
---

# Molecule Visualization

## Overview

Produce clean, reproducible molecular figures from SMILES, SDF, and PDB inputs.
This skill covers five families of output, each backed by a stable open-source
library API you call directly (no vendor CLI required):

| Output | Library | Reference |
|--------|---------|-----------|
| 2D structure depiction (PNG/SVG) | RDKit `rdMolDraw2D` | `references/rdkit-2d-recipes.md` |
| Annotated molecule grid | RDKit `Draw.MolsToGridImage` | `references/rdkit-2d-recipes.md` |
| Scaffold + R-group SAR views | RDKit `MurckoScaffold`, `rdRGroupDecomposition` | `references/scaffold-and-rgroup.md` |
| Protein-ligand contact diagram | Biopython `NeighborSearch` + Matplotlib | `references/interaction-diagrams.md` |
| Interactive 3D viewer (HTML) | py3Dmol | `references/py3dmol-3d.md` |

For color schemes, DPI, dimensions, fonts, and the 2D-vs-3D decision, see
`references/style-guide.md`. Prefer `scientific-figure` for assembling
multi-panel manuscript figures once the individual molecular panels exist.

## When to Use This Skill

- You have a **SMILES / SDF / PDB** and need a figure of the actual chemical
  structure or 3D geometry.
- You are building **SAR tables** or virtual-screening hit lists and want a grid
  with per-compound descriptors.
- You want to communicate a **binding mode**: a 2D interaction summary or an
  interactive 3D complex a reader can rotate.
- You need **scaffold decomposition** (core + R-groups) to reason about a
  congeneric series.
- You are visualizing downstream artifacts: **detected pockets** (JSON of
  centers/scores) or **ranked docking poses** (multi-model SDF).

## When NOT to Use This Skill

- **Generating 3D conformers or optimizing geometry** — this skill only *renders*
  coordinates it is given. Use RDKit `AllChem.EmbedMolecule`/`MMFFOptimizeMolecule`
  or a dedicated conformer tool first, then render here.
- **Predicting properties or activity** with ML models — this skill only *displays*
  descriptor values (QED, MW, LogP, TPSA) it computes or reads from a table.
- **Plotting non-molecular data** (scatter, bar, ROC, dose-response) — use
  `scientific-visualization`.
- **Conceptual/mechanism schematics** (pathways, reaction arrows, block diagrams)
  drawn from a description — use `scientific-schematics`.
- **Rigorous interaction profiling** (validated H-bond geometry, pi-stacking
  angles, interaction fingerprints) — the diagram here is a distance-based
  heuristic; use PLIP or ProLIF for quantitative work.
- **MD trajectory or ensemble rendering** — use a molecular-viewer purpose-built
  for trajectories (VMD, PyMOL, nglview with a trajectory backend).

## Setup

```bash
# Core: 2D drawing and grids
pip install rdkit          # modern wheels; older docs may say rdkit-pypi
pip install pillow matplotlib

# Interaction diagrams (protein parsing + geometry)
pip install biopython numpy

# Interactive 3D viewers
pip install py3Dmol
```

RDKit `MolDraw2DCairo` (PNG) needs the Cairo-backed build; the standard `rdkit`
wheel includes it. `MolDraw2DSVG` (vector) has no extra dependency and is the
preferred format for print — see the style guide.

## 1. 2D Structure Depiction

Parse SMILES, compute 2D coordinates, then draw with a Cairo (PNG) or SVG
drawer. Highlighting, atom indices, and legends are set on the drawer options
and the `DrawMolecule` call.

```python
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.Draw import rdMolDraw2D

mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")   # returns None on bad SMILES
AllChem.Compute2DCoords(mol)

drawer = rdMolDraw2D.MolDraw2DCairo(400, 300)        # or MolDraw2DSVG(...)
drawer.drawOptions().addStereoAnnotation = True
drawer.DrawMolecule(mol, legend="Aspirin",
                    highlightAtoms=[8, 9, 10],
                    highlightAtomColors={8: (0.29, 0.56, 0.85)})
drawer.FinishDrawing()
open("aspirin.png", "wb").write(drawer.GetDrawingText())
```

Always **check `MolFromSmiles` for `None`** before drawing. Full option table
(bond width, atom indices, kekulization, dative bonds, transparent background)
and the grid recipe are in `references/rdkit-2d-recipes.md`.

## 2. Annotated Molecule Grid

Use `Draw.MolsToGridImage` with `legends` carrying computed descriptors — this is
the canonical, reproducible grid rather than hand-laid PIL panels.

```python
from rdkit.Chem import Draw, Descriptors, QED
legends = [f"{name}\nQED {QED.qed(m):.2f}  MW {Descriptors.MolWt(m):.0f}"
           for name, m in series]
img = Draw.MolsToGridImage([m for _, m in series], molsPerRow=4,
                           subImgSize=(300, 250), legends=legends,
                           useSVG=True)
```

Descriptor cheat sheet (QED, MW, LogP, TPSA, HBD/HBA, formula) and CSV-driven
grids are in `references/rdkit-2d-recipes.md`.

## 3. Scaffold and R-Group Views

Detect the Bemis-Murcko scaffold automatically or supply a core, highlight the
core substructure, and decompose a congeneric series into R-groups.

```python
from rdkit.Chem.Scaffolds import MurckoScaffold
core = MurckoScaffold.GetScaffoldForMol(mol)          # or a supplied core mol
match = mol.GetSubstructMatch(core)                    # atoms to highlight
```

`rdRGroupDecomposition.RGroupDecompose` and rendering the R-group table are
covered in `references/scaffold-and-rgroup.md`.

## 4. Protein-Ligand Contact Diagram

Parse the complex with Biopython, find residues whose atoms fall within a
distance cutoff of the ligand, classify contacts heuristically, and lay them out
radially around the ligand with Matplotlib.

```python
from Bio.PDB import PDBParser, NeighborSearch
protein = PDBParser(QUIET=True).get_structure("rec", "receptor.pdb")
search = NeighborSearch(list(protein.get_atoms()))
contacts = search.search(ligand_centroid, 4.0)         # atoms within 4.0 Å
```

Contact typing is a **heuristic** (distance + atom identity), not validated
interaction geometry. Layout, color coding, and the PLIP/ProLIF upgrade path are
in `references/interaction-diagrams.md`.

## 5. Interactive 3D Viewer

Build a self-contained HTML file with py3Dmol — protein cartoon, ligand sticks,
optional pocket spheres from a scoring JSON, or ranked docking poses colored by
rank.

```python
import py3Dmol
view = py3Dmol.view(width=800, height=600)
view.addModel(open("protein.pdb").read(), "pdb")
view.setStyle({"cartoon": {"color": "spectrum"}})
view.addModel(open("ligand.sdf").read(), "sdf")
view.setStyle({"model": -1}, {"stick": {}})
view.zoomTo()
view.write_html("complex.html")     # older py3Dmol: use _make_html()
```

Pocket-sphere coloring by druggability, docking-pose overlays, surfaces, and the
`--mode` equivalents (protein / complex / pockets / docking-results) are in
`references/py3dmol-3d.md`.

## Common Failure Modes

- **`MolFromSmiles` returns `None`** — invalid or non-Kekulizable SMILES. Guard
  every parse; log the offending string instead of crashing on a `None` mol.
- **Blank or overlapping 2D layout** — you skipped `Compute2DCoords`, or reused a
  mol that already had 3D coords. Recompute 2D before drawing.
- **PNG output fails / empty file** — Cairo backend missing; fall back to
  `MolDraw2DSVG` or reinstall the full `rdkit` wheel.
- **Grid legends truncated** — `subImgSize` too small for the annotation text;
  enlarge the cell or shorten legends.
- **3D HTML renders empty in a strict CSP context** — py3Dmol embeds 3Dmol.js;
  ensure the viewing environment allows the inlined script, or open the file
  directly in a browser.
- **Wrong atoms highlighted from a substructure match** — `GetSubstructMatch`
  returns the *first* match; use `GetSubstructMatches` and pick deliberately for
  symmetric cores.

See `references/style-guide.md` for CPK colors, resolution/DPI targets, figure
dimensions, colorblind-safe palettes, and when to choose 2D over 3D.
