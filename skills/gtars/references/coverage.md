# Coverage Tracks with uniwig

`uniwig` ("unified wiggle") converts genomic intervals — aligned fragments,
reads, or peaks — into coverage profiles and writes them as WIG, BigWig, or
bedGraph. Use it to build browser tracks and to derive per-position signal for
downstream analysis.

> Signatures are illustrative — verify with `help(gtars.uniwig)` and
> `gtars uniwig --help`.

## Generate coverage

Python:

```python
import gtars

cov = gtars.uniwig.coverage_from_bed("fragments.bed")
cov = gtars.uniwig.coverage_from_bed("fragments.bed", resolution=10)  # bin size (bp)

fwd = gtars.uniwig.coverage_from_bed("fragments.bed", strand="+")
rev = gtars.uniwig.coverage_from_bed("fragments.bed", strand="-")
```

CLI:

```bash
gtars uniwig generate --input fragments.bed --output coverage.wig
gtars uniwig generate --input fragments.bed --output coverage.wig --resolution 10
gtars uniwig generate --input fragments.bed --output coverage.bw --format bigwig
gtars uniwig generate --input fragments.bed --output forward.wig --strand +
```

**Resolution** is the trade-off knob: `resolution=1` gives base-pair precision
and the largest output; larger bins shrink output and smooth signal. Match it to
the assay and to what the browser or model needs.

## Query coverage values

```python
cov.get_coverage("chr1", 1000)               # value at a position
cov.get_coverage_range("chr1", 1000, 2000)   # array over a range
cov.mean_coverage("chr1", 1000, 2000)
cov.max_coverage("chr1", 1000, 2000)
```

## Transform and combine

```python
cov.normalize()                 # e.g. depth normalization
cov.smooth(window_size=10)      # sliding-window smoothing
cov1.add(cov2)                  # sum two tracks
cov1.subtract(cov2)             # difference
```

Verify the exact normalization definition (per-million? per-bp?) in your
version before using it in a quantitative comparison — the label alone is not
enough for reproducibility.

## Output formats

- **WIG** — text `fixedStep`/`variableStep`; human-readable, largest.
- **BigWig** — indexed binary; the right choice for genome browsers and large
  genomes. `--format bigwig`.
- **bedGraph** — `chrom start end value` per interval; flexible and easy to
  post-process with shell tools.

For large datasets prefer BigWig, and process chromosomes in parallel where the
build supports it.

## Per-assay recipes

```python
# ATAC-seq accessibility (base-pair resolution)
atac = gtars.uniwig.coverage_from_bed("atac_fragments.bed", resolution=1)

# ChIP-seq browser track
# gtars uniwig generate --input chip.bed --output chip.bw --format bigwig

# Strand-specific RNA-seq
fwd = gtars.uniwig.coverage_from_bed("rnaseq.bed", strand="+")
rev = gtars.uniwig.coverage_from_bed("rnaseq.bed", strand="-")
```

## Gotchas

- **A chromosome-sizes / reference is usually required to write BigWig** so the
  track has correct chromosome lengths. Supply the genome the intervals were
  called against.
- **Fragments vs cut-sites vs reads** produce different coverage. Be explicit
  about what each interval represents (e.g. ATAC fragment span vs Tn5 insertion
  point) before interpreting peaks.
- **Strand filtering** silently returns empty coverage if the input BED lacks a
  strand column — check the input has strand before splitting by `+`/`-`.
- **Comparing samples** requires the same normalization and resolution on both
  tracks, or the difference reflects processing, not biology.
