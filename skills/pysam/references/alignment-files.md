# Alignment Files (SAM/BAM/CRAM)

`AlignmentFile` reads and writes aligned reads. BAM and CRAM are compressed and
support index-backed random access; SAM is plain text and is read sequentially.

## Opening

```python
import pysam

samfile = pysam.AlignmentFile("example.bam", "rb")          # read BAM
cram    = pysam.AlignmentFile("example.cram", "rc",
                              reference_filename="ref.fasta")  # CRAM needs the ref
outfile = pysam.AlignmentFile("out.bam", "wb", template=samfile)  # write, inherit header
```

Mode qualifiers: `"rb"`/`"wb"` BAM, `"rc"`/`"wc"` CRAM, `"r"`/`"w"` SAM. Writing
requires either `template=` (copy another file's header) or an explicit
`header=`. Use `with pysam.AlignmentFile(...) as f:` or call `.close()` — BAM
writers must be closed to flush and finalize the file.

### Streams

Pass `"-"` for stdin/stdout. Arbitrary Python file objects are **not** supported.

```python
infile  = pysam.AlignmentFile("-", "rb")
outfile = pysam.AlignmentFile("-", "w", template=infile)
```

## Header properties

- `references` — tuple of contig names.
- `lengths` — matching contig lengths.
- `header` — full header as a dict (`HD`, `SQ`, `RG`, `PG`, ...) or
  `AlignmentHeader` object.

## Reading reads

### `fetch()` — region retrieval

```python
for read in samfile.fetch("chr1", 1000, 2000):   # 0-based, half-open
    print(read.query_name, read.reference_start)

for read in samfile.fetch("chr1"):               # whole contig
    ...

for read in samfile.fetch(until_eof=True):       # sequential, no index needed
    ...
```

- Requires a `.bai`/`.crai` index unless `until_eof=True`.
- Returns every read **overlapping** the interval (may extend past edges).
- Returns mapped reads by default. For unmapped reads use `until_eof=True` (they
  sit after mapped records) or `fetch("*")`.
- Region strings (`fetch("chr1:1000-2000")`) are 1-based; numeric args 0-based.

### Multiple simultaneous iterators

A second `fetch()` on the same handle repositions the shared file pointer and
invalidates the first iterator. Open with `multiple_iterators=True` to get
independent iterators (at extra cost).

### `count()` and `count_coverage()`

```python
n = samfile.count("chr1", 1000, 2000)                     # reads overlapping region
n = samfile.count("chr1", 1000, 2000, read_callback="all")  # apply default QC filter

# per-base A/C/G/T coverage across the interval; four equal-length arrays
a, c, g, t = samfile.count_coverage("chr1", 1000, 2000)
```

Prefer `count()` over manually iterating and incrementing.

## AlignedSegment attributes

Each read is an `AlignedSegment`.

**Read data**
- `query_name` — read ID.
- `query_sequence` — bases (str).
- `query_qualities` — Phred scores as an array of ints (no ASCII offset).
- `query_length` / `query_alignment_length` — full vs aligned length.

**Mapping**
- `reference_name`, `reference_id` — contig name / index into header `SQ`.
- `reference_start` (0-based, inclusive), `reference_end` (0-based, exclusive).
- `mapping_quality` — MAPQ.
- `cigarstring` (e.g. `"100M"`) and `cigartuples` (list of `(op, length)`).
- `get_aligned_pairs(with_seq=True)` — `(query_pos, ref_pos, ref_base)` triples.

**CIGAR operation codes** (integers in `cigartuples`, *not* the SAM letters):

| Code | Op | Meaning | Code | Op | Meaning |
| --- | --- | --- | --- | --- | --- |
| 0 | M | match/mismatch | 5 | H | hard clip |
| 1 | I | insertion | 6 | P | padding |
| 2 | D | deletion | 7 | = | seq match |
| 3 | N | ref skip | 8 | X | seq mismatch |
| 4 | S | soft clip | | | |

**Flag accessors** (booleans over the SAM `flag` int): `is_paired`,
`is_proper_pair`, `is_unmapped`, `mate_is_unmapped`, `is_reverse`,
`mate_is_reverse`, `is_read1`, `is_read2`, `is_secondary`, `is_qcfail`,
`is_duplicate`, `is_supplementary`.

**Optional tags**: `has_tag(tag)`, `get_tag(tag)`, `set_tag(tag, value, value_type=None)`,
`get_tags()`.

```python
for read in samfile.fetch("chr1", 1000, 2000):
    if read.has_tag("NM"):
        print(read.query_name, "edit distance", read.get_tag("NM"))
```

## Writing

### From a header dict

```python
header = {
    "HD": {"VN": "1.0"},
    "SQ": [{"SN": "chr1", "LN": 1575}, {"SN": "chr2", "LN": 1584}],
}
outfile = pysam.AlignmentFile("out.bam", "wb", header=header)
```

### Building a read

```python
a = pysam.AlignedSegment()
a.query_name = "read001"
a.query_sequence = "AGCTTAGCTAGCTACCTATATCTTGGTCTTGGCCG"
a.flag = 0
a.reference_id = 0            # index into header["SQ"]
a.reference_start = 100
a.mapping_quality = 20
a.cigar = [(0, 35)]          # 35M
a.query_qualities = pysam.qualitystring_to_array("I" * 35)
outfile.write(a)
```

Set `query_sequence` **before** `query_qualities`; assigning the sequence
resets qualities. To edit qualities of an existing read, copy them out first:
`quals = read.query_qualities; read.query_sequence = new_seq; read.query_qualities = quals`.

### Format conversion

Open the input, open the output with `template=input` and the target mode, and
copy reads through the loop (`for read in infile: outfile.write(read)`).

## Pileup analysis

`pileup()` walks the region **column by column** (one reference position at a
time), exposing every read covering each position.

```python
for column in samfile.pileup("chr1", 1000, 2000):
    print(column.pos, "depth", column.nsegments)
    for pread in column.pileups:
        if not pread.is_del and not pread.is_refskip:
            base = pread.alignment.query_sequence[pread.query_position]
```

- `column.pos` — 0-based reference position.
- `column.nsegments` — reads covering the column.
- `pread.alignment` — the `AlignedSegment`.
- `pread.query_position` — index into the read (`None` for deletions/skips).
- `pread.is_del`, `pread.is_refskip` — deletion / N-in-CIGAR flags.

By default `pileup()` clips base qualities and applies filters; pass
`truncate=True` to restrict output strictly to the requested interval, and
`min_base_quality=0`/`stepper="all"` to change filtering. **Keep the iterator and
its current column referenced** — releasing them early raises
`PileupProxy accessed after iterator finished`.

## Indexing

```python
pysam.index("example.bam")          # writes example.bam.bai
pysam.samtools.index("example.bam") # equivalent via the CLI wrapper
```

Sort before indexing if needed: `pysam.samtools.sort("-o", "sorted.bam", "in.bam")`.

## Performance

- Index once, then use region `fetch()`; avoid full scans for point queries.
- Use `count()`/`count_coverage()` for depth rather than manual pileup counting.
- Use `pileup()` (not repeated `fetch()`) for per-position base analysis.
- Parallelize across independent regions with separate file handles.
- Watch memory on `pileup()` over ultra-high-coverage loci.
