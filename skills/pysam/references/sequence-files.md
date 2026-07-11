# Sequence & Interval Files (FASTA / FASTQ / tabix)

Three classes: `FastaFile` (indexed reference lookup), `FastxFile` (sequential
FASTQ/FASTA streaming), and `TabixFile` (region queries over bgzipped
tab-delimited annotations).

## FASTA — `FastaFile`

Indexed, random-access reference sequences. Needs a `.fai` index.

```python
import pysam

pysam.faidx("reference.fasta")            # build reference.fasta.fai (once)
fasta = pysam.FastaFile("reference.fasta")  # auto-locates the .fai

fasta.references                          # contig names
fasta.lengths                             # matching lengths
fasta.get_reference_length("chr1")
```

### Fetching

```python
seq = fasta.fetch("chr1", 1000, 2000)     # 0-based half-open -> 1000 bases
seq = fasta.fetch("chr1")                 # whole contig
seq = fasta.fetch(region="chr1:1001-2000")  # region string is 1-based
```

Numeric args are 0-based; region strings are 1-based (samtools convention).
Returned sequence **preserves case** (soft-masking) — normalize with `.upper()`
before comparisons.

### Common helpers

```python
def variant_context(fasta, chrom, pos, window=10):
    """Reference bases around a 1-based variant position."""
    return fasta.fetch(chrom, max(0, pos - window - 1), pos + window)

def gene_sequence(fasta, chrom, start, end, strand):
    seq = fasta.fetch(chrom, start, end)
    if strand == "-":
        comp = str.maketrans("ATGCatgcNn", "TACGtacgNn")
        seq = seq.translate(comp)[::-1]      # reverse complement
    return seq

def check_ref_allele(fasta, chrom, pos, expected):   # pos is 1-based
    return fasta.fetch(chrom, pos - 1, pos).upper() == expected.upper()
```

### IUPAC ambiguity codes

Reference FASTA may contain more than A/C/G/T:

| Code | Bases | Code | Bases | Code | Bases |
| --- | --- | --- | --- | --- | --- |
| N | any | R | A/G | Y | C/T |
| S | G/C | W | A/T | K | G/T |
| M | A/C | B | C/G/T | D | A/G/T |
| H | A/C/T | V | A/C/G | | |

Count non-ACGT bases with `sum(1 for b in seq.upper() if b not in "ACGT")`.

## FASTQ — `FastxFile`

Sequential reader for raw reads (also reads FASTA). **No random access.**
Handles `.gz` transparently.

```python
with pysam.FastxFile("reads.fastq.gz") as fq:
    for r in fq:
        r.name         # ID, no leading '@'
        r.sequence
        r.quality      # ASCII-encoded quality string (or None for FASTA)
        r.comment      # trailing header comment, if any
        r.get_quality_array()   # numeric Phred scores
```

Quality is Phred-scaled, typically Phred+33 (`Q = -10*log10(P_error)`; `'!'`=Q0,
`'+'`=Q10, `'?'`=Q30). Use `get_quality_array()` rather than decoding ASCII by
hand.

### Streaming filters (write FASTQ manually)

pysam reads FASTQ but does not write it, so emit records with plain `open()`:

```python
def filter_fastq(inp, outp, min_len=50, min_mean_q=20):
    with pysam.FastxFile(inp) as fin, open(outp, "w") as fout:
        for r in fin:
            q = r.get_quality_array()
            if len(r.sequence) >= min_len and sum(q) / len(q) >= min_mean_q:
                fout.write(f"@{r.name}\n{r.sequence}\n+\n{r.quality}\n")
```

The same 4-line-per-record pattern covers length filtering, extract-by-name
(`if r.name in wanted_set`), subsampling (`if random.random() < frac`), and
FASTQ→FASTA (`f">{r.name}\n{r.sequence}\n"`, dropping quality).

## Tabix — `TabixFile`

Region queries over any bgzipped, tabix-indexed tab-delimited file (BED, GFF,
GTF, VCF, generic).

```python
pysam.tabix_index("annotations.bed", preset="bed", force=True)  # -> .bed.gz + .tbi
tbx = pysam.TabixFile("annotations.bed.gz")

for row in tbx.fetch("chr1", 1000000, 2000000):
    print(row)                               # raw tab-delimited string
```

Presets for `tabix_index`: `"bed"`, `"gff"`, `"vcf"`. Compression must be
**bgzip**, not gzip.

### Parsers for named-field access

Pass `parser=` to get typed rows instead of raw strings:

```python
for iv in tbx.fetch("chr1", 1_000_000, 2_000_000, parser=pysam.asBed()):
    iv.contig, iv.start, iv.end, iv.name, iv.score, iv.strand

for ft in tbx.fetch("chr1", 1_000_000, 2_000_000, parser=pysam.asGTF()):
    ft.feature, ft.gene_id, ft.transcript_id, ft.start, ft.end
```

Available parsers: `asBed()`, `asGTF()`, `asVCF()`, `asTuple()`.

## Pitfalls

- FASTA `fetch()` numeric args are 0-based; region strings are 1-based.
- FASTA random access requires the `.fai`; FASTQ has no random access at all.
- Assume Phred+33 unless the data explicitly says otherwise.
- Tabix needs bgzip compression and an explicit `parser=` for named fields.
- FASTA case is meaningful (soft-masking) — `.upper()` before comparing alleles.
