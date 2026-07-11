# deepTools Normalization Methods

Normalization makes coverage comparable across samples with different sequencing
depths, library sizes, and (for RPKM) region lengths. Without it, a 100M-read
sample looks like it has twice the signal of an identical 50M-read sample.
`bamCoverage` sets the method with `--normalizeUsing`; `bamCompare` sets it with
`--scaleFactorsMethod`.

## Methods

### RPKM — Reads Per Kilobase per Million

`reads / (region_length_kb x total_mapped_reads_millions)`. Corrects for **both**
depth and region length. Best for RNA-seq gene-level analysis and comparing
different-length regions within a sample. Available in `bamCoverage`. Do not use
on fixed-size bins — the length term is constant and does nothing.

### CPM — Counts Per Million (a.k.a. RPM)

`reads / total_mapped_reads_millions`. Corrects for depth only. Best for
comparing the same fixed-width regions across samples (ChIP-seq, ATAC-seq,
DNase-seq). Available in `bamCoverage`, `bamCompare`. Sensitive to very abundant
regions (e.g. rRNA in RNA-seq).

### BPM — Bins Per Million

`reads_in_bin / (sum_of_reads_in_all_bins_millions)`. Like CPM, but the
denominator counts only reads inside analyzed bins, not all mapped reads. Use to
normalize against analyzed regions while ignoring background. Available in
`bamCoverage`, `bamCompare`. Less common, so harder to line up with published
values.

### RPGC — Reads Per Genomic Content (1x normalization)

`reads x scale_factor / effective_genome_size`, where the scale factor targets 1x
genome-wide coverage. The output value approximates coverage depth (a value of 2
≈ 2x). Best when you want interpretable, cross-sample-comparable coverage.
**Requires** `--effectiveGenomeSize` (see `genome-sizes.md`). Assumes roughly
uniform coverage, which is not literally true for peaky ChIP-seq but still works
well in practice. Available in `bamCoverage`, `bamCompare`.

### None

Raw counts. Only for preliminary looks, debugging, or when a downstream tool does
its own normalization. Not valid for cross-sample comparison or publication.

### SES — Signal Extraction Scaling (`bamCompare` only)

A more sophisticated background-correction scaling for comparing ChIP to control;
often better than plain `readCount` on noisy data. `--scaleFactorsMethod SES`.

### readCount (`bamCompare` default)

Scales the two BAMs by their total-read ratio before comparing (100M vs 50M → the
50M sample is scaled 2x). Good default when total read counts reflect library
size. `--scaleFactorsMethod readCount`.

## Selection Guide

| Situation | Recommended |
|-----------|-------------|
| ChIP-seq coverage track | `RPGC` (interpretable) or `CPM` |
| ChIP-seq treatment vs control | `bamCompare --operation log2 --scaleFactorsMethod readCount` (or `SES`) |
| RNA-seq fixed bins | `CPM` |
| RNA-seq gene-level | `RPKM` (length-aware) |
| ATAC-seq | `RPGC` or `CPM` (after Tn5 shift) |
| Sample correlation | `CPM`/`RPGC` bigWigs → `multiBigwigSummary` |

`multiBamSummary` itself does not normalize, but correlation is robust to
scaling. For very unequal library sizes, correlate CPM/RPGC bigWigs via
`multiBigwigSummary` instead.

## Advanced Scaling

**Spike-in**: compute a scaling factor from spike-in reads (e.g. a *Drosophila*
chromatin spike-in) and apply it manually:

```bash
bamCoverage --bam chip.bam -o chip_spikenorm.bw --scaleFactor 0.8 --extendReads 200
```

**Manual factor**: `--scaleFactor 2.0` applies a 2x multiplier.

**Chromosome exclusion**: keep sex/mito chromosomes out of the normalization
scale factor:

```bash
bamCoverage --bam input.bam -o output.bw --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398 --ignoreForNormalization chrX chrY chrM
```

## Pitfalls

1. **RPKM on fixed bins** — length term is inert; use CPM or RPGC.
2. **Comparing unnormalized samples** — depth differences masquerade as signal.
3. **Wrong effective genome size** — an hg19 size on hg38 data skews RPGC.
4. **`--ignoreDuplicates` after GC correction** — introduces bias; never combine.
5. **RPGC without `--effectiveGenomeSize`** — the command fails.

## Quick Reference

| Method | Depth | Length | Best for | Flag |
|--------|-------|--------|----------|------|
| RPKM | yes | yes | RNA-seq genes | `--normalizeUsing RPKM` |
| CPM | yes | no | fixed bins | `--normalizeUsing CPM` |
| BPM | yes | no | analyzed regions | `--normalizeUsing BPM` |
| RPGC | yes | no | interpretable coverage | `--normalizeUsing RPGC --effectiveGenomeSize X` |
| None | no | no | raw data | `--normalizeUsing None` |
| SES | yes | no | ChIP comparisons | `bamCompare --scaleFactorsMethod SES` |
| readCount | yes | no | ChIP comparisons | `bamCompare --scaleFactorsMethod readCount` |

Further reading: deepTools docs (https://deeptools.readthedocs.io/), ENCODE
ChIP-seq guidelines, and DESeq2/edgeR TMM normalization literature for
statistical-model normalization beyond track scaling.
