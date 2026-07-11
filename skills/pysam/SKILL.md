---
name: pysam
version: 0.1.0
description: >-
  Read, query, and write genomic file formats from Python through pysam's
  binding to htslib/samtools/bcftools: SAM/BAM/CRAM alignments, VCF/BCF
  variants, FASTA/FASTQ sequences, and tabix-indexed BED/GTF/GFF. Use when
  building NGS or bioinformatics pipelines that fetch reads or variants by
  genomic region, compute per-base coverage and pileups, extract reference
  sequences, filter reads or variants by quality/flags/genotype, or drive
  samtools/bcftools subcommands programmatically. Not for de-novo alignment
  or variant CALLING (run bwa/minimap2/GATK/`bcftools call` and read their
  output here instead), not for single-cell expression matrices (use
  `scanpy`), and not for tabular genomic annotations that carry no
  coordinate index (use `polars`/pandas).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT"
---

# Pysam

## Overview

`pysam` is a thin, Pythonic binding over htslib and the samtools/bcftools
command-line suites. It gives you random-access, index-backed reads and writes
of the core sequencing file formats without shelling out or parsing text by
hand. Reach for it whenever a task involves the raw artifacts of a sequencing
run — aligned reads, called variants, reference sequences, or interval
annotations — and you need to slice them by genomic coordinate.

Four object families cover almost everything:

| Class | Formats | Use for |
| --- | --- | --- |
| `AlignmentFile` | SAM / BAM / CRAM | reads, coverage, pileup, filtering |
| `VariantFile` | VCF / BCF | variants, genotypes, INFO/FORMAT |
| `FastaFile` / `FastxFile` | FASTA / FASTQ | reference lookup, raw-read streaming |
| `TabixFile` | bgzipped BED/GTF/GFF/VCF | interval annotations by region |

Install with `uv pip install pysam` (Linux/macOS wheels bundle htslib; Windows
is unsupported).

## When to Use This Skill

- Fetching reads or variants that overlap a genomic region (`fetch()`).
- Computing read depth, per-base coverage, or column-wise pileups.
- Filtering alignments by MAPQ, SAM flags, or duplicate status.
- Reading/writing genotypes and INFO/FORMAT fields from multi-sample VCFs.
- Extracting reference subsequences by coordinate (variant context, gene span).
- Streaming and QC-filtering raw FASTQ reads by length or Phred quality.
- Querying tabix-indexed BED/GTF/GFF annotations.
- Invoking `samtools`/`bcftools` subcommands from Python (sort, index, view).

## When NOT to Use This Skill

- **Producing** alignments or variant calls — pysam reads outputs, it does not
  align or call. Run `bwa`/`minimap2`/GATK/`bcftools call`, then load results here.
- **Single-cell / expression matrices** — use `scanpy` (AnnData), not pysam.
- **General sequence records without a genomic index** (parsing a multi-FASTA
  of proteins, translating ORFs, phylogenetics) — `biopython` fits better.
- **Coverage track generation and bigwig/deeptools-style visualization at
  scale** — `deeptools` is purpose-built; pysam is fine for ad-hoc coverage.
- **Tabular annotation joins with no coordinate query** — load into `polars`/pandas.

## Coordinate Systems (read this first)

The single most common source of off-by-one bugs. Two conventions coexist:

- **Numeric `fetch()`/`pileup()` args and object attributes are 0-based,
  half-open** (Python style): `reference_start` is inclusive, `reference_end`
  is exclusive. `fetch("chr1", 1000, 2000)` yields bases 1000–1999.
- **Region strings are 1-based, closed** (samtools style):
  `fetch("chr1:1000-2000")` yields bases 1000–2000.
- **VCF POS is 1-based** as displayed (`variant.pos`), but `variant.start` /
  `variant.stop` are 0-based, half-open. `VariantFile.fetch()` numeric args are
  **0-based, half-open too** — the same rule as everything else here; only the
  region-string form (`fetch("chr1:1000-2000")`) is 1-based. Don't let the
  1-based `pos` mislead you.

When bridging a variant's 1-based `pos` into any numeric call — a `VariantFile`,
`AlignmentFile`, or `FastaFile` `fetch`/`count`/`pileup` — subtract 1:
`samfile.count(v.chrom, v.pos - 1, v.pos)` counts reads over the single variant
base (equivalently `v.start`/`v.stop`).

## Indexing Requirements

Random access by region needs a companion index; without one, iterate
sequentially (`fetch(until_eof=True)`).

| File | Index | Create with |
| --- | --- | --- |
| BAM | `.bai` | `pysam.index(bam)` |
| CRAM | `.crai` | `pysam.index(cram)` |
| FASTA | `.fai` | `pysam.faidx(fa)` |
| VCF.gz | `.tbi` | `pysam.tabix_index(vcf, preset="vcf")` |
| BCF | `.csi` | `pysam.bcftools.index(bcf)` |
| BED/GFF/GTF.gz | `.tbi` | `pysam.tabix_index(f, preset="bed"/"gff")` |

Tabix indexing requires **bgzip** compression, not plain gzip.

## Capabilities

Each area has a dedicated reference with the full API surface, attribute tables,
and worked examples. Load the one you need.

### Alignment files (SAM/BAM/CRAM)

Open with mode qualifiers (`"rb"` BAM, `"rc"` CRAM, `"r"` SAM; `w*` to write).
`fetch()` for region reads, `count()`/`count_coverage()` for depth, `pileup()`
for column-wise base analysis, and the `AlignedSegment` object for per-read
sequence, CIGAR, flags, and tags. See
[references/alignment-files.md](references/alignment-files.md).

### Variant files (VCF/BCF)

Iterate or `fetch()` `VariantRecord`s; read `ref`/`alts`/`qual`/`filter`,
`info[...]` fields, and per-sample `samples[name]["GT"]` genotypes. Build new
files with `VariantHeader` and `new_record()`. See
[references/variant-files.md](references/variant-files.md).

### Sequence & interval files (FASTA/FASTQ/tabix)

`FastaFile.fetch()` for indexed reference lookup, `FastxFile` for sequential
FASTQ streaming with Phred quality, `TabixFile` with `asBed()`/`asGTF()`/
`asVCF()` parsers for annotation records. IUPAC ambiguity codes and quality
encoding covered here. See
[references/sequence-files.md](references/sequence-files.md).

### Integrated workflows & command-line tools

Multi-format recipes (BAM QC stats, coverage profiling, variant validation
against reads, variant-context extraction, BAM/VCF subsetting) plus the
`pysam.samtools.*` / `pysam.bcftools.*` subcommand wrappers and `SamtoolsError`
handling. See [references/workflows.md](references/workflows.md).

## Common Pitfalls

1. **Coordinate confusion** — see the section above; it is the #1 bug source.
2. **Missing index** — region `fetch()` raises without an index; build one or
   pass `until_eof=True` for a sequential scan.
3. **Overlap, not containment** — `fetch()` returns every read *overlapping*
   the region, including reads that extend past its edges. Filter explicitly if
   you need containment.
4. **Pileup iterator lifetime** — keep the `pileup()` iterator (and its column)
   referenced; letting it fall out of scope triggers
   `PileupProxy accessed after iterator finished`.
5. **Quality-vs-sequence edit order** — you cannot edit `query_qualities` in
   place after reassigning `query_sequence`; copy the qualities out, then
   reassign both.
6. **Streams** — only `"-"` (stdin/stdout) is a supported stream target; pysam
   cannot read/write arbitrary Python file objects.
7. **Thread safety** — the GIL is released during I/O, but full thread safety is
   not guaranteed; prefer per-region parallelism with independent file handles.

Official upstream docs: https://pysam.readthedocs.io/
