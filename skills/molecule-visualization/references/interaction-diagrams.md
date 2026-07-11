# Protein-Ligand Interaction Diagrams

Deep reference for the 2D contact diagram: parse a complex, find residues near the
ligand, classify contacts heuristically, and lay them out around the ligand. APIs
are from Biopython (`Bio.PDB`), NumPy, RDKit (for the ligand depiction), and
Matplotlib (for the schematic).

> **Scope caveat.** This produces a *distance-based heuristic* summary suitable for
> a figure or a quick binding-mode sketch. It is **not** validated interaction
> geometry. For quantitative work — correct H-bond angles, pi-stacking geometry,
> salt-bridge charge state, interaction fingerprints — use **PLIP**
> (Protein-Ligand Interaction Profiler) or **ProLIF**, which encode the proper
> geometric criteria. Cite those, not this diagram, in a methods section.

## Inputs

- **Protein**: a PDB file (receptor). Parse standard amino-acid residues only.
- **Ligand**: an SDF (or a ligand extracted from the complex PDB). RDKit reads it
  for the 2D depiction; Biopython/NumPy handle the 3D geometry.

## Finding contacting residues

```python
from Bio.PDB import PDBParser, NeighborSearch
from Bio.PDB.Polypeptide import is_aa
import numpy as np

structure = PDBParser(QUIET=True).get_structure("rec", "receptor.pdb")
protein_atoms = [a for a in structure.get_atoms()
                 if is_aa(a.get_parent(), standard=True)]
search = NeighborSearch(protein_atoms)

# ligand_coords: (N, 3) array of ligand heavy-atom positions
cutoff = 4.0                      # Å; typical contact shell 4.0–4.5
near = set()
for xyz in ligand_coords:
    for atom in search.search(np.array(xyz), cutoff):
        near.add(atom.get_parent())   # the residue
```

`NeighborSearch.search(center, radius)` uses a KD-tree, so scanning every ligand
atom against the whole protein is cheap even for large receptors.

## Heuristic contact classification

Classify each near residue by the closest protein-atom / ligand-atom pair and the
residue identity. Reasonable, transparent heuristics:

| Class | Heuristic |
|-------|-----------|
| Hydrogen bond | polar donor/acceptor pair (N/O) within ~3.5 Å |
| Salt bridge | charged residue (Asp/Glu/Lys/Arg/His) N/O near opposite-charge ligand atom ≤ 4.0 Å |
| Pi-stacking | aromatic residue (Phe/Tyr/Trp/His) ring near a ligand aromatic ring |
| Hydrophobic | carbon-carbon contact within ~4.5 Å, no polar pair |

Document these thresholds in any figure caption; they are conventions, not
physics. Do not report angles or energies from this method.

## Radial layout with Matplotlib

Place the ligand 2D depiction (RDKit, see `rdkit-2d-recipes.md`) at the center,
then arrange residue nodes on a circle:

```python
import math, matplotlib.pyplot as plt

n = len(contacts)
for i, res in enumerate(contacts):
    angle = i * (2 * math.pi / n) - math.pi / 2      # start at top
    x, y = math.cos(angle), math.sin(angle)
    # draw a rounded box (FancyBboxPatch) at (x, y) with the residue label,
    # background-colored by interaction class, and a dashed line back to center
```

Style conventions (line color per class, residue box background, dashed vs dotted)
are tabulated in `style-guide.md`. Label residues as `TYR189` (three-letter + seq
id + chain when ambiguous). Show the contact distance on the connector for the
closest atom pair.

## Rendering the central ligand

- Draw the ligand once with RDKit to PNG/SVG, then embed it as the central image
  (`imshow` a rasterized panel, or composite the SVG).
- Or draw a simplified ligand glyph if the true 2D structure is too dense to read
  at figure scale.

## Failure modes

- **No contacts found** — ligand and protein are in different coordinate frames, or
  the ligand was parsed without coordinates. Confirm both come from the same
  complex and the SDF carries 3D coords.
- **Every residue flagged hydrophobic** — polar-pair detection missed because
  hydrogens are absent; add explicit Hs to protein and ligand before classifying,
  or relax to heavy-atom N/O distance criteria.
- **Overcrowded ring** — too many contacts at a small cutoff. Reduce the cutoff,
  or group residues by class into arcs.
- **Non-standard residues / cofactors ignored** — `is_aa(..., standard=True)` drops
  modified residues, metals, and waters; handle metal coordination and structural
  waters separately if they matter to the binding story.
