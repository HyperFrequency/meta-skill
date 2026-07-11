---
name: glycobiology
version: 0.1.0
description: >-
  Predict and analyze protein glycosylation sites from sequence with lightweight,
  dependency-free Python. Finds canonical N-glycosylation sequons (N-X-S/T, X≠P)
  with proline-efficiency flags and non-canonical N-X-C handling, scores
  O-glycosylation hotspots by sliding-window Ser/Thr density, runs combined
  glycoprotein analysis with UniProt cross-validation, and points to external
  structure servers (NetNGlyc, NetOGlyc, GLYCAM-Web). Use when you have a protein
  sequence and need candidate glyco sites for mutagenesis design, biotherapeutic
  annotation, or triage before wet-lab glycoproteomics. Do NOT treat output as
  ground truth (a sequon is necessary, not sufficient — use the NetNGlyc/NetOGlyc
  neural nets for occupancy probabilities), and do NOT use it for glycan
  STRUCTURE/composition or MS spectra assignment, for intracellular O-GlcNAc, or
  for surface-accessibility calls — cross-check annotated sites in UniProt and
  exposure in AlphaFold.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Glycobiology: Glycosylation Site Prediction

## Overview

Turn a protein sequence into a ranked list of candidate glycosylation sites.
This skill implements the two sequence-level workhorse predictions — N-linked
sequon scanning and O-linked hotspot scoring — as small, auditable pure-Python
functions (only Biopython for FASTA I/O, NumPy for the sliding window), then
cross-validates them against experimentally annotated sites and hands off glycan
*structure* questions to the right external servers.

The predictions are **rule-based, not learned**: a sequon or an S/T-rich window
marks a *candidate*, not an occupied site. Treat this skill as fast triage and
experiment planning, then confirm with the neural-net servers and UniProt.

This file is a **router**. Each capability links to a `references/` file with the
exact functions, parameters, and failure modes. Read the map, jump to the
reference you need, then return here for boundaries.

## When to Use This Skill

- Enumerate N-glycosylation sequons (N-X-S/T) in a sequence or a FASTA file.
- Flag S/T-rich regions that are candidate mucin-type O-glycosylation hotspots.
- Plan glycosylation-site mutagenesis (knock a site in or out) and reason about
  proline-mediated efficiency effects.
- Annotate glycosylation for biotherapeutic/antibody engineering (e.g. the
  conserved IgG Fc N297 site).
- Reconcile predicted sites with UniProt annotations (true/false positives,
  missed sites) before committing to an assay.
- Look up which external tool answers a glycan *structure* or MS question.

## When NOT to Use This Skill

- **As ground truth for occupancy.** A sequon is necessary but not sufficient;
  many are never glycosylated. For probabilities use NetNGlyc / NetOGlyc.
- **Glycan structure, composition, or MS spectra assignment.** This skill locates
  *sites on the protein*, not the sugar tree attached to them — see
  `references/glycan-resources.md`.
- **Intracellular O-GlcNAc.** The O-hotspot heuristic targets secreted/mucin-type
  O-GalNAc; nucleocytoplasmic O-GlcNAcylation is a distinct single-sugar mark and
  is not modeled here.
- **Surface-accessibility / 3D context.** Sequence tells you nothing about whether
  a site is solvent-exposed — check a structure (AlphaFold DB, PDB).
- **Cytoplasmic/nuclear proteins.** N-glycosylation happens in the ER lumen;
  sequons in non-secretory proteins are biological false positives — filter by
  localization first.

## Setup

```bash
uv pip install biopython numpy pandas
```

Everything runs on the standard library plus these three packages — no compiled
callers, no network access required for the core predictions.

## Capability Map

### N-glycosylation sequon finding
Scan for N-X-S/T (X≠P), report 1-based positions with flanking context, annotate
proline-mediated efficiency reductions, handle the rare non-canonical N-X-C
sequon, and batch-scan a multi-record FASTA with per-sequence site density.
→ `references/n-glycosylation.md`

### O-glycosylation hotspot scoring
Sliding-window Ser/Thr density with a tunable window and threshold, hotspot
region merging, per-residue proline-neighbor down-weighting, and guidance on why
this heuristic has a high false-positive rate.
→ `references/o-glycosylation.md`

### Combined glycoprotein analysis, CLI, and UniProt validation
The `analyze_glycoprotein` roll-up, the `predict_glycosylation.py` command-line
script (CSV + annotated-sequence output), TP/FP/FN comparison against UniProt
annotations, best practices, and the troubleshooting table.
→ `references/glycoprotein-analysis.md`

### Glycan structure & database resources
When to leave sequence-level prediction for structure: NetNGlyc/NetOGlyc neural
nets, GLYCAM-Web (3D + MD), glycan-shield modeling, and the GlyConnect/GlyGen and
UniProt carbohydrate databases.
→ `references/glycan-resources.md`

## Quick Start

Find every N-glycosylation sequon in a sequence:

```python
def find_n_glycosylation_sites(sequence, exclude_proline=True):
    """N-X-S/T sequons; X != P by the standard rule. Positions are 1-based."""
    seq = str(sequence).upper()
    sites = []
    for i in range(len(seq) - 2):
        if seq[i] != "N":
            continue
        x_residue, acceptor = seq[i + 1], seq[i + 2]
        if exclude_proline and x_residue == "P":
            continue
        if acceptor not in ("S", "T"):
            continue
        sites.append({
            "position": i + 1,
            "motif": seq[i:i + 3],
            "x_residue": x_residue,
            "acceptor": acceptor,
            "context": seq[max(0, i - 5):i + 8],
        })
    return sites

# Human erythropoietin (EPO): known N-sites at N24, N38, N83 (mature numbering)
epo = ("MGVHECPAWLWLLLSLLSLPLGLPVLGAPPRLICDSRVLERYLLEAKEAENITTGCAEHCSLNENITVPDT"
       "KVNFYAWKRMEVGQQAVEVWQGLALLSEAVLRGQALLVNSSQPWEPLQLHVDKAVSGLRSLTTLLRALGAQ"
       "KEAISPPDAASAAPLRTITADTFRKLFRVYSNFLRGKLKLYTGEACRTGDR")
for s in find_n_glycosylation_sites(epo):
    print(f"N{s['position']}: {s['motif']}  ...{s['context']}...")
```

Positions here are relative to the sequence you pass. Database annotations are
usually numbered on the **mature** chain (after signal-peptide cleavage) — see
`references/glycoprotein-analysis.md` for reconciling the offset.

## Related Skills

- `biopython` — FASTA/record parsing and sequence manipulation feeding these scans.
- `bioservices` — query UniProt programmatically for annotated glycosylation sites
  to validate predictions against.
- `esm` — protein language-model embeddings / ESMFold structures when you need
  learned context or 3D exposure beyond sequence rules.
- `statistical-analysis` — enrichment and precision/recall testing when comparing
  predicted vs annotated site sets across many proteins.
- External databases (not skills): **UniProt** (carbohydrate annotations),
  **GlyConnect/GlyGen** (site-specific glycoproteomics), **AlphaFold DB** (exposure).
