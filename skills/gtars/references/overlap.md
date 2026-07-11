# Overlap Detection and IGD

`overlaprs` computes overlaps between genomic interval sets; `igd` builds an
**Integrated Genome Database** index for fast repeated queries against a large
reference. Use plain overlap for one-off comparisons; use IGD when the reference
set is large or queried many times (variant annotation, BEDbase-style search).

> Signatures are illustrative — verify with `help(gtars.overlap)` /
> `help(gtars.igd)` and `gtars overlaprs --help` / `gtars igd --help`.

## Background: what IGD is

IGD (Feng et al.) is a disk-friendly index that answers "which reference
intervals overlap this query" without scanning the whole reference. Building the
index is roughly `O(n log n)` in the number of reference intervals; a query is
roughly `O(k + log n)` where `k` is the number of hits. This is why IGD backs
large-scale interval search (e.g. BEDbase). Build once, query many times.

## IGD index (Python)

```python
import gtars

igd = gtars.igd.build_index("reference_regions.bed")
igd.save("reference.igd")                 # persist for reuse
igd = gtars.igd.load_index("reference.igd")

hits  = igd.query("chr1", 1000, 2000)     # overlapping reference intervals
count = igd.count_overlaps("chr1", 1000, 2000)
```

## Pairwise overlap between two sets (Python)

```python
a = gtars.RegionSet.from_bed("regions_a.bed")
b = gtars.RegionSet.from_bed("regions_b.bed")

a.overlap(b)                    # overlap relation between the sets
a.filter_overlapping(b)         # intervals of a that touch b  (membership)
a.filter_non_overlapping(b)     # intervals of a that do NOT touch b

a.count_overlaps(b)             # how many of a overlap b
a.overlap_fraction(b)           # fraction of a covered by b
```

**Membership vs geometry:** `filter_overlapping(b)` returns whole `a`-intervals
that touch `b`; `a.intersect(b)` (see [python-api.md](python-api.md)) returns the
clipped overlapping sub-intervals. Pick based on whether you want the original
features or just the shared bases.

## CLI

```bash
# IGD
gtars igd build --input reference.bed --output reference.igd
gtars igd query --index reference.igd --region "chr1:1000-2000"
gtars igd query --index reference.igd --query-file queries.bed --output hits.bed
gtars igd count --index reference.igd --query-file queries.bed

# overlaprs (set-to-set)
gtars overlaprs overlap  --set-a a.bed --set-b b.bed --output overlaps.bed
gtars overlaprs count    --set-a a.bed --set-b b.bed
gtars overlaprs filter   --input regions.bed --filter mask.bed --output kept.bed
gtars overlaprs subtract --set-a a.bed --set-b b.bed --output diff.bed
```

## Worked patterns

```python
# TF binding sites that fall in promoters
tfbs      = gtars.RegionSet.from_bed("chip_peaks.bed")
promoters = gtars.RegionSet.from_bed("promoters.bed")
in_prom   = tfbs.filter_overlapping(promoters)
print(len(in_prom), "peaks overlap a promoter")

# Variants overlapping coding sequence
variants = gtars.RegionSet.from_bed("variants.bed")
cds      = gtars.RegionSet.from_bed("cds.bed")
coding   = variants.filter_overlapping(cds)
```

## Gotchas

- **Chromosome-name mismatch** (`chr1` vs `1`) silently yields zero overlaps.
  Normalize naming before querying.
- **Coordinate base.** BED is 0-based half-open; a 1-based query shifts hits by
  one base and can drop boundary overlaps.
- **Rebuild the index** when the reference BED changes — a stale `.igd` answers
  against old data with no warning.
- **Half-open touching:** intervals `[0,10)` and `[10,20)` are adjacent, not
  overlapping. Decide whether book-ended features should count and adjust
  coordinates accordingly.
