---
name: deeptools
version: 0.1.0
description: >-
  deepTools command-line suite for high-throughput sequencing coverage analysis
  and signal visualization. Use to convert BAM alignments into normalized
  bigWig/bedGraph coverage tracks (RPGC, CPM, RPKM, BPM), run
  ChIP-seq/ATAC-seq/RNA-seq quality control (sample correlation, PCA, fingerprint
  enrichment, coverage depth, fragment-size distribution), build signal matrices
  around genomic features (TSS, gene bodies, peaks) with computeMatrix, and
  render publication heatmaps and meta-profiles (plotHeatmap, plotProfile,
  plotEnrichment). Reach for it whenever a request mentions BAM-to-bigWig
  conversion, coverage normalization, ChIP quality assessment, replicate
  correlation, or heatmaps/profiles around genomic regions. NOT for read
  alignment (bwa/bowtie2/STAR), peak calling (MACS2/Genrich), differential
  expression or binding statistics (DESeq2/edgeR/csaw), variant calling (GATK),
  or generic array plotting unrelated to genome coverage.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (deepTools; file cm.py is BSD-3-Clause)"
---

# deepTools: NGS Coverage, QC, and Signal Visualization

## Overview

deepTools is a suite of Python command-line utilities for processing aligned
high-throughput sequencing reads into normalized coverage tracks, assessing data
quality, and producing publication-grade signal plots around genomic features. It
is the standard toolkit for the "after alignment, before biology" stage of
ChIP-seq, ATAC-seq, RNA-seq, MNase-seq, and CUT&RUN analysis.

This SKILL.md is a **router**. It gives you the core pattern, input-validation
discipline, a capability map, and the sharp edges that bite in real use, then
delegates full parameter tables, complete pipelines, and lookup values to
`references/`. Every deepTools tool is a self-contained CLI command — there is no
Python object to hold; a workflow is a sequence of commands passing files
(`.bam` → `.bw` → `.gz` matrix → `.png`) between stages.

## When to Use This Skill

Use this skill when the request involves any of:

- **Coverage tracks**: "convert BAM to bigWig", "make a normalized coverage
  track", "generate a log2 ChIP-vs-input ratio track".
- **Quality control**: "check ChIP enrichment", "are my replicates
  correlated?", "run PCA on my samples", "is sequencing depth adequate?", "plot
  the fragment-size distribution".
- **Signal visualization**: "heatmap around the TSS", "meta-profile over gene
  bodies", "signal at peak centers", "FRiP / enrichment at peaks".
- **Assay pipelines**: end-to-end ChIP-seq, ATAC-seq (Tn5 shift), or
  strand-specific RNA-seq coverage.

## When NOT to Use This Skill

deepTools operates on *already-aligned* reads and does not do statistics. Route
elsewhere for:

- **Alignment** of raw FASTQ → use bwa, bowtie2, or STAR.
- **Peak calling** → use MACS2, Genrich, or SEACR (deepTools consumes the peaks
  they emit, it does not call them).
- **Differential binding / expression statistics** → use DESeq2, edgeR, csaw, or
  limma.
- **Variant calling** → use GATK or bcftools.
- **Custom re-plotting** of exported matrices/tables beyond deepTools' built-in
  plots → export with `--outFileNameMatrix` / `--outFileNameData` and hand the
  `.tab` file to `matplotlib`, `seaborn`, or `polars`.

## Installation

```bash
uv pip install deeptools    # or: pip install deeptools / conda install -c bioconda deeptools
```

Requires `samtools` on PATH for BAM indexing. Verify with `deeptools --version`.

## The Core Pattern

Nearly every deepTools analysis follows one arc:

```
QC  →  Normalize (BAM → bigWig)  →  Compare  →  Visualize
```

1. **QC first**, always: correlation + PCA + fingerprint + coverage. Never build
   figures on data you have not sanity-checked.
2. **Normalize** BAM to a coverage track with `bamCoverage` (pick a method — see
   below).
3. **Compare** two conditions with `bamCompare` (log2 ratio) when relevant.
4. **Visualize**: `computeMatrix` builds a per-region signal matrix, then
   `plotHeatmap` / `plotProfile` render it; `plotEnrichment` scores signal in
   peak sets.

## Validate Inputs Before Running

deepTools failures are overwhelmingly bad inputs, not bad flags. Check up front:

```bash
samtools quickcheck *.bam                 # truncation / corruption
ls *.bam.bai 2>/dev/null || samtools index sample.bam   # every BAM needs an index
head -1 regions.bed                        # BED must be tab-delimited, 0-based
```

Then confirm the **genome build matches** across every BAM and BED/GTF (an hg19
BED against hg38 BAMs silently produces empty or shifted signal), and that BAM
and region files share the same chromosome naming (`chr1` vs `1`).

## Capability Map

| Task | Primary tool(s) | Deep reference |
|------|-----------------|----------------|
| BAM → normalized coverage | `bamCoverage` | `references/tools-reference.md` |
| Two-sample ratio track | `bamCompare` | `references/tools-reference.md` |
| Coverage matrix for QC/PCA | `multiBamSummary`, `multiBigwigSummary` | `references/tools-reference.md` |
| Sample correlation / PCA | `plotCorrelation`, `plotPCA` | `references/tools-reference.md` |
| ChIP enrichment strength | `plotFingerprint` | `references/tools-reference.md` |
| Depth / fragment size | `plotCoverage`, `bamPEFragmentSize` | `references/tools-reference.md` |
| Signal matrix over features | `computeMatrix` | `references/tools-reference.md` |
| Heatmaps & meta-profiles | `plotHeatmap`, `plotProfile` | `references/tools-reference.md` |
| Enrichment / FRiP at peaks | `plotEnrichment` | `references/tools-reference.md` |
| Filter / shift reads | `alignmentSieve` (`--ATACshift`) | `references/tools-reference.md` |
| GC-bias detect / correct | `computeGCBias`, `correctGCBias` | `references/tools-reference.md` |
| Matrix subset / combine | `computeMatrixOperations` | `references/tools-reference.md` |

Copy-paste starting commands:

```bash
# BAM -> RPGC-normalized bigWig (ChIP-seq)
bamCoverage --bam chip.bam -o chip.bw --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398 --binSize 10 --extendReads 200 \
    --ignoreDuplicates -p 8

# Two-step heatmap around the TSS
computeMatrix reference-point -S chip.bw -R genes.bed \
    --referencePoint TSS -b 3000 -a 3000 -o matrix.gz -p 8
plotHeatmap -m matrix.gz -o heatmap.png --colorMap RdBu --kmeans 3
```

End-to-end pipelines (ChIP-seq QC, full ChIP-seq analysis, RNA-seq strand
coverage, ATAC-seq Tn5, multi-sample comparison, peak-region analysis) live in
`references/workflows.md`.

## Normalization: Choosing a Method

Getting normalization wrong invalidates every comparison. Quick guide:

| Experiment | Use | Note |
|------------|-----|------|
| ChIP-seq coverage | `RPGC` or `CPM` | RPGC gives interpretable 1x coverage |
| ChIP-seq treatment vs control | `bamCompare --operation log2 --scaleFactorsMethod readCount` (or `SES`) | positive = enriched |
| RNA-seq fixed bins | `CPM` | never `--extendReads` |
| RNA-seq gene-level | `RPKM` | accounts for gene length |
| ATAC-seq | `RPGC` or `CPM` | after Tn5 shift |

`RPGC` **requires** `--effectiveGenomeSize`. Do not use `RPKM` on fixed-size bins
(bins are all one length, so the length term does nothing). Full formulas,
per-method tradeoffs, spike-in and manual scaling, and pitfalls are in
`references/normalization.md`.

## Effective Genome Sizes

RPGC normalization and GC-bias tools need the mappable genome size:

| Organism | Assembly | `--effectiveGenomeSize` |
|----------|----------|-------------------------|
| Human | GRCh38/hg38 | `2913022398` |
| Mouse | GRCm38/mm10 | `2652783500` |
| Zebrafish | GRCz11 | `1368780147` |
| *Drosophila* | dm6 | `142573017` |
| *C. elegans* | ce11 | `100286401` |

Read-length-specific values, hg19/mm39 assemblies, shorthand codes, and custom
genome calculation are in `references/genome-sizes.md`.

## Assay-Specific Rules

- **ChIP-seq**: `--extendReads 200` (extend to fragment length), `--ignoreDuplicates`,
  and always run `plotFingerprint` before detailed work — a steep cumulative
  curve means good enrichment, a near-diagonal curve means the ChIP failed.
- **RNA-seq**: **NEVER** `--extendReads` (it would span splice junctions). Use
  `--filterRNAstrand forward/reverse` for stranded libraries.
- **ATAC-seq**: shift for the Tn5 offset first with
  `alignmentSieve --ATACshift`, then `bamCoverage`. A correct library shows a
  nucleosome ladder in `bamPEFragmentSize` (~50 / ~200 / ~400 bp).
- **GC correction**: only apply `correctGCBias` if `computeGCBias` shows real
  bias, and **never** combine `--ignoreDuplicates` with a GC-corrected BAM.

## Common Failure Modes

- **`Missing index`** → `samtools index sample.bam`.
- **Empty / all-zero matrix** → mismatched genome build or chromosome naming
  between BAM and BED; check with `samtools idxstats` vs the BED.
- **Out of memory** → process per chromosome with `--region chr1`, and raise
  `--binSize`.
- **Slow runs** → raise `-p/--numberOfProcessors` to the core count; test
  parameters on `--region chr1:1-10000000` first.
- **Huge bigWig files** → increase `--binSize` (e.g. `50`); prefer bigWig over
  bedGraph (compressed, faster).

## References

- `references/tools-reference.md` — every command by category (processing, QC,
  visualization, misc) with key parameters, modes, and interpretation.
- `references/workflows.md` — complete copy-paste pipelines per assay, plus
  performance and troubleshooting notes.
- `references/normalization.md` — each method's formula, when to use it,
  spike-in / manual scaling, and pitfalls.
- `references/genome-sizes.md` — effective genome size lookup and custom
  calculation.
