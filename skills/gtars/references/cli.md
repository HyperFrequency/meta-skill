# CLI Reference

The `gtars` binary exposes one subcommand per compiled module. Which subcommands
exist depends on the Cargo features the binary was built with — always confirm
with `gtars --help` and `gtars <subcommand> --help`, since flags evolve pre-1.0.

## Install and global options

```bash
cargo install gtars --features "uniwig overlaprs igd bbcache scoring fragsplit"
# or a subset: cargo install gtars --features "uniwig overlaprs"

gtars --help
gtars --version
gtars --verbose <command>
gtars --quiet   <command>
```

## igd — indexed overlap

```bash
gtars igd build --input regions.bed --output regions.igd
gtars igd query --index regions.igd --region "chr1:1000-2000"
gtars igd query --index regions.igd --query-file queries.bed --output results.bed
gtars igd count --index regions.igd --query-file queries.bed
```

See [overlap.md](overlap.md) for when to prefer IGD over pairwise overlap.

## overlaprs — set-to-set overlap

```bash
gtars overlaprs overlap  --set-a a.bed --set-b b.bed --output overlaps.bed
gtars overlaprs count    --set-a a.bed --set-b b.bed
gtars overlaprs filter   --input regions.bed --filter mask.bed --output kept.bed
gtars overlaprs subtract --set-a a.bed --set-b b.bed --output diff.bed
```

## uniwig — coverage tracks

```bash
gtars uniwig generate --input fragments.bed --output coverage.wig
gtars uniwig generate --input fragments.bed --output coverage.wig --resolution 10
gtars uniwig generate --input fragments.bed --output coverage.bw --format bigwig
gtars uniwig generate --input fragments.bed --output forward.wig --strand +
```

See [coverage.md](coverage.md) for formats and per-assay recipes.

## fragsplit — single-cell fragment splitting

Split a 10x scATAC `fragments.tsv` by cell barcode or cluster assignment.

```bash
gtars fragsplit split         --input fragments.tsv --barcodes barcodes.txt --output-dir ./split/
gtars fragsplit cluster-split --input fragments.tsv --clusters clusters.txt --output-dir ./clustered/
gtars fragsplit filter        --input fragments.tsv --min-fragments 100 --output filtered.tsv
```

## scoring — score fragments/regions against a reference

```bash
gtars scoring score --fragments fragments.bed --reference reference.bed --output scores.txt
gtars scoring batch --fragments-dir ./fragments/ --reference reference.bed --output-dir ./scores/
gtars scoring score --fragments fragments.bed --reference reference.bed --weights weights.txt --output scores.txt
```

## bbcache — BEDbase cache client

Fetch and cache BED / BEDset files from BEDbase (bedbase.org).

```bash
gtars bbcache fetch --id <bedbase_id> --output cached.bed
gtars bbcache list
gtars bbcache update
gtars bbcache clear
```

## refget — sequence digests

```bash
gtars refget digest --input genome.fa --output digests.txt
gtars refget verify --sequence sequence.fa --digest <expected>
```

See [refget.md](refget.md) for the GA4GH digest details.

## End-to-end examples

```bash
# Overlap pipeline: index a reference, query experimental data, summarize
gtars igd build --input reference.bed --output reference.igd
gtars igd query --index reference.igd --query-file experimental.bed --output hits.bed
gtars overlaprs count --set-a experimental.bed --set-b reference.bed

# Single-cell pipeline: filter -> split by cluster -> score
gtars fragsplit filter        --input raw.tsv --min-fragments 100 --output filtered.tsv
gtars fragsplit cluster-split --input filtered.tsv --clusters clusters.txt --output-dir ./by_cluster/
gtars scoring   batch         --fragments-dir ./by_cluster/ --reference reference.bed --output-dir ./scores/
```

## Input formats

```text
# BED (0-based, half-open)      # Fragment TSV (scATAC)       # WIG (fixedStep)
chr1  1000  2000                chr1  1000  2000  BARCODE1    fixedStep chrom=chr1 start=1000 step=10
chr1  3000  4000                chr1  3000  4000  BARCODE2    12
chr2  5000  6000                chr2  5000  6000  BARCODE1    15
```

## Performance and robustness flags

Exact names vary by build — confirm with `--help`. Common controls include
thread count, memory limit, buffer size, and log routing:

```bash
gtars --threads 8 <command>
gtars --log-file run.log <command>
```

## Gotchas

- **Feature gating:** a subcommand missing from `gtars --help` means the binary
  was built without that feature — reinstall with the feature flag.
- **Chromosome naming** must be consistent across every input file (`chr1` vs
  `1`), or overlaps silently come back empty.
- **Rebuild indexes** after the underlying BED changes; a stale `.igd` answers
  against old data.
- **BigWig output** typically needs chromosome sizes / a reference for correct
  track lengths.
