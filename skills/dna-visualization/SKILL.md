---
name: dna-visualization
version: 0.1.0
description: >-
  Render publication-quality DNA/RNA figures from sequence and annotation files
  using Biopython, dna_features_viewer, logomaker, and Matplotlib: circular or
  linear annotated plasmid maps and linear gene/feature tracks from GenBank,
  sequence logos (information-content or probability) from multiple sequence
  alignments, restriction-enzyme cut-site maps, and sliding-window GC-content
  plots. Use when you need figures of DNA/RNA structure, annotation,
  conservation, or base composition for papers, plasmid/cloning design, and
  genomics. Do NOT use for small-molecule/chemical-structure graphics (use
  `molecule-visualization`), general non-sequence data plots (use
  `scientific-visualization`), conceptual pathway/mechanism schematics (use
  `scientific-schematics`), sequence analysis with no figure required (use
  `biopython`), or interactive genome-browser tracks over whole assemblies.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "Biopython: BSD-3-Clause; dna_features_viewer: MIT; logomaker: MIT; matplotlib: PSF-based (BSD-compatible)"
---

# DNA Visualization

## Overview

Produce clean, reproducible DNA/RNA figures for molecular biology, cloning, and
genomics. Each output family is backed by a stable open-source library API you
call directly — no vendor CLI required. Inputs are standard sequence files
(GenBank, FASTA) and alignments (aligned FASTA, Clustal).

| Output | Library | Reference |
|--------|---------|-----------|
| Circular / linear plasmid map | Biopython + `dna_features_viewer` | `references/plasmid-and-gene-maps.md` |
| Linear gene / feature track | Biopython + `dna_features_viewer` | `references/plasmid-and-gene-maps.md` |
| Sequence logo (bits or probability) | Biopython `AlignIO` + `logomaker` | `references/sequence-logos.md` |
| Restriction-enzyme cut-site map | Biopython `Bio.Restriction` + Matplotlib | `references/restriction-maps.md` |
| Sliding-window GC-content plot | Biopython `SeqIO` + Matplotlib | `references/gc-content.md` |

For DPI, SVG-vs-PNG, feature-color conventions, colorblind-safe palettes, fonts,
and figure dimensions, see `references/style-guide.md`. To assemble several of
these panels into one manuscript figure, hand off to `scientific-figure`.

## When to Use This Skill

- You have a **GenBank plasmid** and need an annotated circular or linear map
  (promoters, CDS, origins, terminators).
- You have a **multiple sequence alignment** and want a **sequence logo** showing
  per-position conservation (information content) or base frequency (probability).
- You want to plan a cloning step: a **restriction map** of which enzymes cut a
  sequence and where.
- You are inspecting **compositional bias**: a GC-content trace to find GC-rich
  islands or AT-rich regions.
- You are drawing a **linear gene/feature track** for a genomic region for a
  figure.

## When NOT to Use This Skill

- **Small-molecule or chemical-structure graphics** (SMILES/SDF/PDB depictions,
  SAR grids, 3D ligand viewers) — use `molecule-visualization`. Never pass a DNA
  sequence to a SMILES-based tool.
- **General, non-sequence data plots** (scatter, bar, ROC, distributions) — use
  `scientific-visualization`.
- **Conceptual schematics** (pathway diagrams, mechanism cartoons, block
  diagrams) drawn from a description rather than data — use
  `scientific-schematics`.
- **Sequence analysis with no figure as the deliverable** (parsing, translation,
  alignment, Tm, motif search, Entrez/BLAST) — use `biopython`; this skill
  *renders* results.
- **Interactive, zoomable genome-browser tracks over whole assemblies** — these
  are static publication figures. Use JBrowse/IGV for browser-style exploration.

## Setup

```bash
# Core: sequence I/O, restriction analysis, GC (required for everything)
pip install biopython matplotlib

# Plasmid maps and gene/feature tracks
pip install dna_features_viewer

# Sequence logos
pip install logomaker
```

All rendering uses the Matplotlib `Agg` backend, so scripts run headless. Set it
before importing `pyplot`:

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
```

Choose the output by file extension in `savefig` — `.png` (raster), `.svg` /
`.pdf` (vector; preferred for print). Use `dpi=300` and `bbox_inches="tight"`.

## 1. Plasmid Map (circular or linear)

Read a GenBank record, convert its features to `GraphicFeature` objects colored
by feature type, then plot with `CircularGraphicRecord` (circular) or
`GraphicRecord` (linear).

```python
from Bio import SeqIO
from dna_features_viewer import GraphicFeature, GraphicRecord, CircularGraphicRecord

record = SeqIO.read("plasmid.gb", "genbank")
features = [
    GraphicFeature(start=int(f.location.start), end=int(f.location.end),
                   strand=f.location.strand or 1, color="#3498db",
                   label=f.qualifiers.get("label", [f.type])[0])
    for f in record.features if f.type not in ("source", "gene")
]
rec = CircularGraphicRecord(sequence_length=len(record.seq), features=features)
ax, _ = rec.plot(figure_width=8)          # GraphicRecord(...) for a linear map
plt.savefig("plasmid_map.svg", dpi=300, bbox_inches="tight")
```

Feature-type → color map, label-qualifier fallback order, and the circular-vs-
linear decision are in `references/plasmid-and-gene-maps.md`.

## 2. Gene / Feature Track (linear, region-sliced)

Same `dna_features_viewer` path, but on a linear record you can clip to a
`start`/`end` window and shift feature coordinates to the region origin. See
`references/plasmid-and-gene-maps.md` for the region-clipping logic and the
richer feature-color map (CDS, mRNA, tRNA/rRNA, exon/intron, mobile_element).

> **GFF input is not read directly.** `SeqIO.read(..., "genbank")` only parses
> GenBank. To draw from GFF, first convert to a `SeqRecord` (e.g. with the
> `bcbio-gff` package's `GFF.parse`) and pass that record's `.features`.

## 3. Sequence Logo (from an alignment)

Read an alignment with `AlignIO`, build a per-position counts matrix, convert to
information (bits) or probability, then draw with `logomaker.Logo`.

```python
from Bio import AlignIO
import logomaker

alignment = AlignIO.read("alignment.fasta", "fasta")   # or "clustal"
# ... build a counts DataFrame (positions x {A,C,G,T} or protein alphabet) ...
matrix = logomaker.transform_matrix(counts, from_type="counts", to_type="information")
logo = logomaker.Logo(matrix, shade_below=0.5, fade_below=0.5)
```

Alphabet auto-detection (DNA vs protein), the counts-matrix build, probability
mode, position slicing, and bit-scale y-axis are in `references/sequence-logos.md`.
Inputs **must be aligned** (all rows equal length) — `AlignIO.read` errors
otherwise.

## 4. Restriction Map

Search a sequence with `Bio.Restriction`. Use `CommOnly` (all common commercial
enzymes) or a named `RestrictionBatch`; `.search()` returns enzyme → cut
positions.

```python
from Bio.Restriction import RestrictionBatch, CommOnly
batch = RestrictionBatch(["EcoRI", "BamHI", "HindIII"])   # or use CommOnly
sites = {str(e): pos for e, pos in batch.search(record.seq).items() if pos}
```

Positions are 1-based. The Matplotlib backbone-plus-tick layout, sorting by cut
count, and the `--max-enzymes` display cap live in `references/restriction-maps.md`.

## 5. GC-Content Plot

Slide a fixed window along the sequence, compute GC fraction per window, and plot
with an overall-GC reference line.

```python
seq = str(record.seq).upper()
window, step = 100, 25
xs, gc = [], []
for i in range(0, len(seq) - window + 1, step):
    sub = seq[i:i + window]
    xs.append(i + window // 2)
    gc.append((sub.count("G") + sub.count("C")) / window)
```

Default `step` is `window // 4`; the window must not exceed the sequence length.
Threshold lines, GC-skew, and styling are in `references/gc-content.md`.

## Common Failure Modes

- **`SeqIO.read` raises on multi-record files** — `read` expects exactly one
  record. Use `SeqIO.parse` and loop, or select one record, for multi-FASTA.
- **Empty plasmid/gene map** — all features were filtered (e.g. only `source`
  present) or coordinates fall outside the `start`/`end` window. Check
  `record.features` and the region bounds.
- **Sequence logo errors on unequal-length rows** — the FASTA is unaligned. Align
  first (MUSCLE/MAFFT/Clustal), then read with `AlignIO`.
- **Logo alphabet looks wrong** — auto-detection treats >4 distinct letters as
  protein; ambiguity codes (N, R, Y) or gaps can flip DNA to "protein". Pass an
  explicit alphabet — see the reference.
- **No restriction sites found** — the chosen enzymes do not cut this sequence,
  or names are misspelled (case-sensitive: `EcoRI`, not `ecori`). Fall back to
  `CommOnly` to confirm the sequence cuts at all.
- **GC plot fails: window larger than sequence** — reduce `--window` or supply a
  longer sequence; the loop yields no windows when `len(seq) < window`.

See `references/style-guide.md` for DPI targets, vector-vs-raster choice, the
standard feature-color conventions, colorblind-safe palettes, font sizes, and
default figure dimensions.
