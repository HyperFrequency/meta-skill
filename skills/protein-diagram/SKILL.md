---
name: protein-diagram
version: 0.1.0
description: >-
  Generate publication-quality 2D protein analysis diagrams with matplotlib and
  BioPython: domain-architecture maps, DSSP secondary-structure tracks,
  Ramachandran plots, C-alpha contact/distance maps, colored multiple-sequence-
  alignment panels, and annotated feature tracks (PTMs, active/binding sites,
  mutations). Use when you have a PDB structure, an aligned FASTA/Clustal file, a
  UniProt accession, or JSON domain/feature definitions and need a static figure
  (PNG/SVG/PDF) for a paper, poster, or slide. NOT for interactive 3D structure
  views or small-molecule/SMILES rendering (use molecule-visualization), 3D
  structure prediction (use structure-prediction), fetching AlphaFold models
  (use alphafold-database), plain data charts (use scientific-visualization), or
  DNA/RNA sequence graphics.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: BioPython (BSD-3-Clause), matplotlib (PSF-based/BSD-compatible), NumPy (BSD-3-Clause), pyMSAviz (MIT)
---

# Protein Diagram

## Overview

This skill renders six kinds of **static 2D protein figures** for structural
biology, bioinformatics, and drug-discovery write-ups. Each figure type is a
self-contained Python script under `scripts/` that takes a structure, sequence,
accession, or JSON spec and writes a PNG/SVG/PDF. The scripts wrap BioPython
(structure parsing, DSSP, dihedrals), NumPy (distance matrices), matplotlib
(rendering), and pyMSAviz (alignment panels).

| Figure | Script | Primary input |
|--------|--------|---------------|
| Domain architecture map | `scripts/draw_domain_map.py` | length + domain JSON, or UniProt ID |
| Secondary-structure track | `scripts/draw_secondary_structure.py` | PDB + chain (needs DSSP binary) |
| Ramachandran plot | `scripts/draw_ramachandran.py` | PDB (+ optional chain) |
| Residue contact / distance map | `scripts/draw_contact_map.py` | PDB + chain |
| MSA visualization | `scripts/draw_alignment.py` | aligned FASTA/Clustal |
| Feature tracks (PTMs, sites) | `scripts/draw_features.py` | length + feature JSON, or UniProt ID |

Full flag tables, JSON schemas, color schemes, and input-format details live in
`references/tools.md`. Dependency setup, publication conventions, known
limitations, and failure modes live in `references/conventions.md`.

## When to Use This Skill

- You have a **PDB structure** and need a Ramachandran plot, C-alpha contact map,
  or helix/sheet/coil track for validation or a methods figure.
- You have an **aligned FASTA/Clustal** file and want a colored, conservation-
  annotated MSA panel.
- You have a **UniProt accession** or hand-written JSON and want a Pfam/InterPro-
  style domain map or a feature track (phospho-sites, active sites, mutations).
- You need a **file-based deliverable** (PNG for slides, SVG/PDF for print) rather
  than an interactive viewer.

## When NOT to Use This Skill

- **Interactive or 3D structure views**, cartoon/surface renders, or
  small-molecule (SMILES) 2D/3D depiction → use `molecule-visualization`.
- **Predicting a 3D structure from sequence** → use `structure-prediction`;
  **retrieving a precomputed model** → use `alphafold-database`.
- **Generic data plots** (scatter, bar, line, heatmaps of arbitrary matrices) →
  use `scientific-visualization`; **AI-generated conceptual schematics** from a
  text prompt → use `scientific-schematics`.
- **DNA/RNA sequence graphics** (plasmid maps, gene tracks) → not covered here.
- **mmCIF-only inputs**: the bundled scripts parse **PDB** (BioPython `PDBParser`).
  Convert mmCIF to PDB first (see `references/conventions.md`).

## Setup

```bash
pip install biopython matplotlib numpy pymsaviz
```

The secondary-structure script additionally needs an external **DSSP** binary
(`mkdssp`/`dssp`); the MSA script needs `pymsaviz`. See
`references/conventions.md` for DSSP install and version notes.

## Capabilities

Each script is invoked with `python scripts/<name>.py ...`. One canonical
invocation is shown per figure; every flag is documented in
`references/tools.md`.

### Domain architecture map

Linear backbone with colored domain boxes and a legend, from inline/file JSON or
a live UniProt/InterPro lookup.

```bash
python scripts/draw_domain_map.py \
  --length 450 \
  --domains '[{"name":"SH2","start":10,"end":100},{"name":"Kinase","start":150,"end":400}]' \
  --output domain_map.png --title "ABL1 Kinase"
# or fetch InterPro domains + length:  --uniprot P00519 --output abl1_domains.svg
```

Colors auto-fill from a colorblind-safe palette when a domain omits `color`.

### Secondary-structure track

Helix (rounded), sheet (arrow), and coil (thin bar) segments derived from DSSP.

```bash
python scripts/draw_secondary_structure.py --input structure.pdb --chain A --output ss.png
```

Prints helix/sheet/coil percentages. Requires the DSSP binary on `PATH`.

### Ramachandran plot

Phi/psi scatter for backbone validation, with optional Gly/Pro highlighting and
approximate favored/allowed region overlays.

```bash
python scripts/draw_ramachandran.py --input structure.pdb --output rama.png \
  --highlight-glycine --highlight-proline --show-regions
```

### Contact / distance map

Symmetric C-alpha distance matrix, or a binary contact map at a distance cutoff.

```bash
python scripts/draw_contact_map.py --input structure.pdb --chain A \
  --output contacts.png --cutoff 8.0 --binary        # omit --binary for a distance heatmap
```

### MSA visualization

Colored alignment panel via pyMSAviz, with wrapping, a consensus/conservation
bar, region slicing, and selectable color schemes.

```bash
python scripts/draw_alignment.py --input alignment.fasta --output msa.svg \
  --wrap 80 --show-conservation --color-scheme Clustal
```

### Feature tracks

Point features (PTMs, sites, mutations) as annotated markers plus region
features as boxes, from JSON or a live UniProt lookup.

```bash
python scripts/draw_features.py --length 450 \
  --features '[{"name":"Active site","position":271,"type":"active_site"},{"name":"pY412","position":412,"type":"phosphorylation"}]' \
  --output features.png
# or:  --uniprot P00519 --output abl1_features.png
```

## References

- `references/tools.md` — per-script flag reference, domain/feature JSON schemas,
  feature-type vocabulary, MSA color schemes, and the input-format table.
- `references/conventions.md` — dependency + DSSP setup, publication style
  conventions (DPI, figure sizes, colors), known limitations, and failure modes.

## Related Skills

- `molecule-visualization` — interactive/3D protein views and small-molecule rendering.
- `structure-prediction` — fold a sequence into a 3D structure before diagramming.
- `alphafold-database` — pull a precomputed AlphaFold model to visualize.
- `scientific-visualization` — general-purpose data charts and heatmaps.
- `scientific-figure` / `scientific-schematics` — composed figure panels and prompt-driven conceptual diagrams.
