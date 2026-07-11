---
name: molecular-cloning
version: 0.1.0
description: >-
  In-silico molecular cloning design and simulation with Biopython and
  primer3-py.
  Predict PCR amplicons from primer/template binding with mismatch tolerance;
  simulate single and double restriction digests and fragment sizes on linear
  or circular DNA; design and verify Golden Gate (Type IIS, 4 bp overhangs) and
  Gibson (overlap-primer) assemblies; design PCR primers under Tm/GC/self-
  complementarity constraints; enumerate and heuristically score CRISPR sgRNAs
  by PAM on both strands; and annotate plasmid features, ORFs, and unique
  restriction sites into GenBank. Use when planning or virtually validating a
  cloning strategy before the bench — checking a diagnostic digest, choosing
  compatible overhangs, ordering primers, or picking guide RNAs. NOT for
  protein-level sequence analysis or 3D structure (use `biopython` or `esm`),
  gene/transcript database lookups (use `gget`, `bioservices`, or
  `database-lookup`), or wet-lab inventory/LIMS tracking (use
  `benchling-integration`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Biopython License Agreement (MIT-style) / BSD-3-Clause; primer3-py: GPL-2.0; NumPy: BSD-3-Clause"
---

# Molecular Cloning: In-Silico Cloning Design & Simulation

## Overview

This skill simulates and designs the DNA-manipulation steps of a molecular
cloning project so you can catch problems on the screen before spending
reagents and days at the bench. It is a **router**: below is the setup path, a
capability map with one-line entry points, and the non-obvious boundaries; the
full functions, parameter tables, and worked examples live in `references/`.

The primitives are deliberately simple and inspectable: a template or plasmid
is a `Bio.Seq` object, cut sites and enzymes come from `Bio.Restriction`,
melting temperatures from `Bio.SeqUtils.MeltingTemp`, and primer design from
`primer3-py`. Nothing here calls a network service or a proprietary design
tool — every result is a deterministic computation you can re-derive by hand.

## When to Use This Skill

Trigger when the user wants to:

- Predict the PCR amplicon(s) a primer pair produces on a template, including
  off-target priming from partial (mismatched) binding.
- Simulate a restriction digest — single or double, linear or circular — and
  get the expected fragment sizes for a diagnostic gel.
- Design a **Golden Gate** assembly: check that 4 bp Type IIS overhangs are
  unique and non-palindromic, and lay out parts in order.
- Design a **Gibson** assembly: generate overlap primers for a set of fragments
  in a chosen order.
- Design PCR primers to Tm / GC / specificity constraints with `primer3`.
- Enumerate candidate **CRISPR sgRNAs** for SpCas9 (or another PAM) and rank
  them by a heuristic design score.
- Annotate a plasmid: find common features, ORFs, and unique restriction sites,
  and write a GenBank map.

## When NOT to Use This Skill

- **Protein-level sequence analysis, alignment, or 3D structure** — use
  `biopython` (`Bio.PDB`, `PairwiseAligner`) or `esm`.
- **Gene / transcript / accession lookups** against public databases — use
  `gget`, `bioservices`, or `database-lookup`.
- **Wet-lab inventory, sample tracking, or registry/LIMS** — use
  `benchling-integration`.
- **Experimentally validated off-target prediction** for CRISPR guides — the
  scoring here is a fast heuristic filter, not a substitute for a genome-wide
  aligner (Cas-OFFinder, CRISPOR, or an on-target model like Rule Set 2). Treat
  scores as a first pass; see `references/crispr-annotation.md`.
- **Codon optimization or gene synthesis ordering** — out of scope.

## Setup

```bash
uv pip install biopython primer3-py numpy
```

`primer3-py` (Section 5 / primer design) is the only heavyweight dependency; the
PCR, restriction, assembly, CRISPR, and annotation capabilities need only
Biopython + NumPy. Import surface:

```python
from Bio.Seq import Seq
from Bio.Restriction import EcoRI, BamHI, RestrictionBatch, Analysis, CommOnly
from Bio.SeqUtils import MeltingTemp as mt
import primer3  # only for primer design
```

Quick smoke test — cut sites and a primer Tm:

```python
seq = Seq("ATCGATCGGGATCCATCGATCGAATTCATCGATCG")
print("BamHI:", BamHI.search(seq))   # 1-based cut positions
print("EcoRI:", EcoRI.search(seq))
print("Tm:", round(mt.Tm_NN(Seq("ATCGATCGGATCCATCGATCG")), 1), "C")
```

## Capability Map

Each capability has a self-contained function in the linked reference. Read the
reference before using it — the signatures, return shapes, and gotchas matter.

| # | Capability | Entry point | Reference |
|---|-----------|-------------|-----------|
| 1 | PCR amplicon prediction | `simulate_pcr(template, fwd, rev, max_mismatches)` | [pcr-primers.md](references/pcr-primers.md) |
| 2 | PCR primer design (primer3) | `design_primers(template, start, length, ...)` | [pcr-primers.md](references/pcr-primers.md) |
| 3 | Restriction digest | `restriction_digest(seq, enzymes, is_linear)` | [restriction-assembly.md](references/restriction-assembly.md) |
| 4 | Golden Gate assembly | `design_golden_gate(parts, enzyme)` | [restriction-assembly.md](references/restriction-assembly.md) |
| 5 | Gibson assembly | `design_gibson_assembly(fragments, overlap_length)` | [restriction-assembly.md](references/restriction-assembly.md) |
| 6 | CRISPR sgRNA design | `design_crispr_guides(target, pam, guide_length)` | [crispr-annotation.md](references/crispr-annotation.md) |
| 7 | Plasmid annotation | `annotate_plasmid(sequence, name)` → GenBank | [crispr-annotation.md](references/crispr-annotation.md) |

## Boundaries & Gotchas To Keep In Mind

These bite in real use; the reference files expand each one.

- **Coordinate conventions.** `Bio.Restriction` `.search()` and `Analysis`
  return **1-based** cut positions; Python slicing on a `Seq` is 0-based. Don't
  mix them when computing fragment boundaries.
- **Circular vs linear.** Pass `linear=False` (or `is_linear=False`) for
  plasmids. A circular molecule with *n* cuts yields *n* fragments; a linear one
  yields *n + 1*. Getting this wrong changes every predicted band.
- **Primer orientation.** The reverse primer is supplied as ordered (5'→3'); the
  PCR simulator must reverse-complement it before searching the template.
- **Type IIS choice matters.** BsaI, BsmBI/Esp3I, and BbsI/BpiI have different
  recognition sites and cut offsets — the overhang you get depends on which
  enzyme and where its site sits. Verify overhangs are unique *and*
  non-palindromic or the assembly mis-ligates.
- **PolIII terminators kill guides.** A run of ≥4 T (`TTTT`) in an sgRNA
  terminates U6/H1 transcription; the scorer penalizes it, but confirm.
- **Methylation blocks cutting.** Dam/Dcm methylation can silently protect a
  restriction site in DNA from a standard *E. coli* host — a real digest may not
  match the simulation.

Cross-cutting design rules, coordinate conventions, and the primary literature
are consolidated in [best-practices.md](references/best-practices.md).

## Related Skills

- `biopython` — the general `Bio.*` toolkit this skill builds on (sequence I/O,
  alignment, structure, Entrez).
- `esm` — protein language models for protein-level analysis.
- `gget`, `bioservices`, `database-lookup` — gene/accession/database lookups.
- `benchling-integration` — cloud LIMS, registry, and sequence management.
