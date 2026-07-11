---
name: pocket-detection
version: 0.1.0
description: >-
  Detect small-molecule binding pockets on a protein structure and rank them by
  druggability before docking or de novo design. Runs three complementary
  detectors — a BioPython/SciPy grid cavity scan, fpocket (alpha spheres), and
  P2Rank (ML) — reconciles them into consensus sites, scores each pocket on a
  6-axis druggability model (volume, hydrophobicity, enclosure, depth, H-bond
  capacity, aromaticity), and compares pockets across apo/holo or WT/mutant
  structures. Use when you need to find or validate a binding site, prioritize
  pockets by drug-likeness, or locate allosteric sites. Do NOT use to dock a
  ligand into a pocket (use `diffdock`), to score the binding strength of a pose
  (use `binding-affinity`), to predict the 3D structure itself (do that first),
  or to map protein-protein interfaces (use a docking server such as ClusPro).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "wraps fpocket and P2Rank (external tools) and Biopython — each under its own license"
---

# Pocket Detection & Druggability Assessment

## Overview

Finding **where** a small molecule can bind is the first committed step of any
structure-based drug design campaign. This skill locates candidate cavities on a
prepared protein, ranks them by how drug-like they are, and cross-checks the
result with multiple detectors so you do not build a whole docking pipeline on a
crystal-packing artifact.

The workflow has four capabilities:

- **Multi-method detection** — a geometric grid scan, `fpocket` (alpha spheres),
  and `P2Rank` (machine learning). Agreement across methods is your confidence
  signal.
- **Druggability scoring** — a transparent 6-axis weighted model that turns raw
  pocket geometry into a single 0-1 score and a druggable / difficult /
  undruggable class.
- **Cross-structure comparison** — match pockets across apo vs holo, wild-type
  vs mutant, or predicted vs experimental structures.
- **A normalized pocket record** — every pocket carries a `center` `[x, y, z]`
  and a bounding box, which is exactly the search box the downstream docking
  step needs.

## When to Use This Skill

Reach for `pocket-detection` when you need to:

- Find binding sites on a protein **before** docking a ligand.
- Decide whether a cavity is worth pursuing (**druggability**: can a drug-like
  molecule bind here at all?).
- Compare the same protein's pockets across structures (apo/holo, WT/mutant,
  before/after a conformational change).
- Locate **allosteric** sites beyond the obvious orthosteric one.
- Reach **consensus** by validating a site with more than one detector.

Trigger phrases: "find the binding pocket", "detect the active site",
"druggability assessment", "where does the ligand bind", "compare binding sites
across structures", "is this pocket druggable".

## When NOT to Use This Skill

- **Docking a ligand into a pocket** — feed this skill's pocket `center` and box
  into `diffdock` (or another docking engine); this skill only finds the box.
- **Predicting how tightly a pose binds** — use `binding-affinity` after docking.
- **You have no 3D structure yet** — predict or fetch a structure first; this
  skill needs atomic coordinates, not a sequence.
- **Protein-protein interface mapping** — flat, very large surfaces (> ~1500 Å³)
  are not small-molecule pockets; use a PPI docking server (ClusPro, HDOCK).

## Prerequisites

Provide a **prepared** PDB/mmCIF: solvent and irrelevant heteroatoms removed,
the biologically relevant chain(s) kept, hydrogens added consistently (fpocket
in particular is sensitive to hydrogen treatment). Before detecting, confirm the
structure's organism in the PDB `SOURCE`/`HEADER` records matches the target you
were asked about — a human request served by a murine crystal is a silent,
expensive error. Flag any mismatch instead of proceeding.

Core Python stack: `biopython`, `numpy`, `scipy` (grid method, geometry,
druggability). Optional external detectors: `fpocket` (a binary) and `P2Rank`
(a Java tool; set `P2RANK_HOME` or put `prank` on `PATH`). See
[references/detection-methods.md](references/detection-methods.md) for install
commands and exact invocations.

## Detection Methods (choose per situation)

| Method   | Engine                         | Strength                                  | Cost / limitation                          |
| -------- | ------------------------------ | ----------------------------------------- | ------------------------------------------ |
| grid     | BioPython + SciPy (no binary)  | zero setup, deterministic, deep cavities  | slow on > ~3000 residues; can merge cavities |
| fpocket  | alpha-sphere Voronoi binary    | fast, well-validated, flexible pockets    | needs the binary; can over-segment         |
| P2Rank   | random-forest ML binary (Java) | best benchmark accuracy, odd geometries   | needs Java + a larger install              |

Default to **auto**: try P2Rank, then fpocket, then fall back to the grid scan.
For a high-confidence call, run all available methods and treat pockets whose
centers agree within ~5 Å as consensus sites. The grid algorithm, the exact
`fpocket -f` / `prank predict -f` commands and their output layouts, tuning
parameters (`grid spacing`, `min volume`, `max pockets`), and the method-selection
table live in [references/detection-methods.md](references/detection-methods.md).

Normalize every detector's output to one record per pocket so the rest of the
pipeline is method-agnostic:

```json
{
  "rank": 1,
  "source": "fpocket",
  "center": [10.5, 22.3, 15.0],
  "volume_A3": 542.8,
  "residues": ["ASP189", "SER195", "HIS57"],
  "n_residues": 15,
  "bbox_min": [5.2, 17.1, 10.8],
  "bbox_max": [16.1, 27.9, 19.3]
}
```

The `center` is a 3-float `[x, y, z]` — the docking search-box center. Keep the
bounding box so the box size can be derived rather than guessed.

## Druggability Assessment

Score each detected pocket on six physically motivated axes, combine them with
fixed weights, and classify:

| Axis          | Weight | What it rewards                                  |
| ------------- | ------ | ------------------------------------------------ |
| volume        | 0.25   | drug-like size (Gaussian peaked ~500 Å³)         |
| enclosure     | 0.25   | buried, wall-surrounded cavities over open grooves |
| hydrophobicity| 0.20   | desolvation-driven binding (peak ~0.5)           |
| depth         | 0.15   | deeper pockets (logistic through the 5-10 Å band) |
| H-bond capacity | 0.10 | anchoring polar contacts, ~4-5 optimal           |
| aromaticity   | 0.05   | π-stacking partners, a few aromatics optimal     |

Composite = weighted sum → **druggable** (> 0.7), **difficult** (0.4-0.7),
**undruggable** (< 0.4). These are literature-derived heuristics (Halgren 2009;
Volkamer 2012), **not** a validated predictive model — use them to prioritize,
never as a verdict. The exact scoring curves, the volume-vs-molecule-class table,
and the caveats are in
[references/druggability-scoring.md](references/druggability-scoring.md).

## Cross-Structure Comparison

To compare pockets across two or more structures of the same protein,
superimpose the structures first (align on shared, well-ordered backbone), detect
pockets with the **same** method on each (use `grid` for consistency), then match
pockets whose centers fall within a matching radius (~5 Å). This surfaces pockets
that open only in the holo state, close on mutation, or shift between conformers.
Details in [references/detection-methods.md](references/detection-methods.md).

## Interpreting & Reporting

- **Volume bands**: < 150 Å³ fragment/ion only · 150-300 Å³ fragment-based ·
  300-800 Å³ ideal drug-like · 800-1500 Å³ large (extended ligands, PROTACs) ·
  > 1500 Å³ likely a surface/PPI, not a pocket.
- **Consensus first**: prefer sites found by multiple methods; note where methods
  disagree rather than silently picking one.
- **Every reported number should trace to a pocket record** — do not hand-type
  coordinates into the docking step; read them from the pocket JSON.

Common failure modes — a single giant merged pocket, no pockets found, or all
druggability scores identical — and their fixes are in
[references/troubleshooting.md](references/troubleshooting.md). The rule of thumb:
**adjust method and parameters, do not reinvent the detection logic in ad-hoc
code.**

## Related Skills

- `diffdock` — dock a ligand once you have the pocket center/box. Run after this.
- `binding-affinity` — score docked poses for binding strength. Run after docking.
- `admet-prediction` / `admet-reasoning` — assess the ligand side once a series
  is chosen.

## References

- Le Guilloux, V. et al. Fpocket: an open source platform for ligand pocket
  detection. *BMC Bioinformatics* 10, 168 (2009).
- Krivák, R. & Hoksza, D. P2Rank: machine learning based tool for rapid and
  accurate prediction of ligand binding sites. *J. Cheminform.* 10, 39 (2018).
- Halgren, T.A. Identifying and characterizing binding sites and assessing
  druggability. *J. Chem. Inf. Model.* 49, 377-389 (2009).
- Volkamer, A. et al. DoGSiteScorer: a web server for automatic binding site
  prediction, analysis and druggability assessment. *Bioinformatics* 28,
  2074-2075 (2012).
