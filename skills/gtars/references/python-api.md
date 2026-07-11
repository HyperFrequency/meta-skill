# Python API: Region Sets and Algebra

Reference for the core region-set surface of the `gtars` Python bindings.

> **Signatures are illustrative.** gtars is pre-1.0; verify with
> `help(gtars)` and `help(gtars.<submodule>)` on your installed version. Where a
> method below is absent, treat it as describing intent and adapt to what
> `help()` reports. Authoritative sources: databio/gtars (GitHub), PyPI `gtars`.

## The region-set model

A region set is an ordered collection of genomic intervals `(chromosome, start,
end)` with optional score/name/strand fields (extended BED). The two conceptual
types are a single **region** and a **region set**.

```python
import gtars

# From a BED file
regions = gtars.RegionSet.from_bed("regions.bed")

# From explicit coordinates
regions = gtars.RegionSet([
    ("chr1", 1000, 2000),
    ("chr1", 3000, 4000),
    ("chr2", 5000, 6000),
])

# Iterate
for region in regions:
    print(region.chromosome, region.start, region.end)

len(regions)                 # number of intervals
regions.total_coverage()     # summed interval length in base pairs
```

## Single-set operations

```python
regions.sort()                          # coordinate sort
regions.merge()                         # collapse overlapping/adjacent intervals
regions.filter_by_size(min_size=1000)   # keep intervals >= min_size
regions.filter_by_chromosome("chr1")    # keep one chromosome
```

`merge()` is the standard normalization before overlap or coverage work: it
removes double-counting from overlapping intervals. Sort first if the input is
not already coordinate-ordered.

## Set operations between two region sets

```python
a = gtars.RegionSet.from_bed("set_a.bed")
b = gtars.RegionSet.from_bed("set_b.bed")

a.union(b)                   # all intervals, merged
a.intersect(b)               # overlapping portions
a.subtract(b)                # a minus any overlap with b
a.symmetric_difference(b)    # in a or b but not both
```

For overlap **membership** (which intervals of `a` touch `b`) versus overlap
**geometry** (the intersected sub-intervals), see
[overlap.md](overlap.md) — `filter_overlapping` vs `intersect`.

## Export

```python
regions.to_bed("output.bed")
regions.to_bed("output.bed", scores=score_array)   # write a score column
regions.to_bed("output.bed", names=name_list)      # write a name column

regions.to_json("output.json")
gtars.RegionSet.from_json("input.json")
```

## NumPy interop

Coordinates round-trip through NumPy arrays for vectorized numerical work.

```python
import numpy as np

starts = regions.starts_array()   # np.ndarray of start positions
ends   = regions.ends_array()     # np.ndarray of end positions
sizes  = regions.sizes_array()    # np.ndarray of interval lengths

chroms = ["chr1"] * len(starts)
rebuilt = gtars.RegionSet.from_arrays(chroms, starts, ends)
```

## Large files: streaming and memory mapping

Do not load a multi-gigabyte BED fully into memory. Prefer chunked streaming or
memory-mapped reads, and enable parallel parsing when available.

```python
# Chunked streaming
for chunk in gtars.RegionSet.stream_bed("large.bed", chunk_size=10000):
    process(chunk)

# Memory-mapped
regions = gtars.RegionSet.from_bed("large.bed", mmap=True)

# Parallel parse
regions = gtars.RegionSet.from_bed("large.bed", parallel=True)
```

## Errors and configuration

```python
try:
    regions = gtars.RegionSet.from_bed("file.bed")
except FileNotFoundError:
    ...
except Exception as e:          # gtars raises typed parse/format errors;
    ...                         # check the module for exact exception names

gtars.set_log_level("DEBUG")    # verbose logging for troubleshooting
```

## Edge cases and gotchas

- **BED is 0-based, half-open** `[start, end)`. Mixing in 1-based coordinates
  (e.g. from a VCF or genome-browser paste) shifts every interval by one — a
  silent off-by-one that corrupts overlap and coverage results.
- **Merge before counting.** Overlap counts and `total_coverage()` double-count
  unless the set is merged first.
- **Chromosome naming must match** across sets (`chr1` vs `1`). Mismatched
  naming yields zero overlaps with no error. Normalize naming up front.
- **Sort assumptions.** Some operations assume coordinate-sorted input; sort
  explicitly if the source order is unknown.
- **Empty inputs** are valid: an empty BED yields an empty region set, and
  overlaps against it are empty — guard downstream code that assumes results.
