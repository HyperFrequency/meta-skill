# Sequences and File I/O — `Bio.Seq`, `Bio.SeqRecord`, `Bio.SeqIO`

`Bio.Seq` gives you the `Seq` object (a string-like biological sequence with
biology-aware methods); `Bio.SeqRecord` wraps a `Seq` with identifiers and
annotations; `Bio.SeqIO` is the one unified reader/writer for every sequence
file format.

## The `Seq` object

```python
from Bio.Seq import Seq

s = Seq("AGTACACTGGT")
len(s)            # 11
s[0:5]            # Seq('AGTAC') — slicing returns a Seq
str(s)            # 'AGTACACTGGT'
```

Biology-aware methods (all return a new `Seq`):

| Method | Meaning |
| --- | --- |
| `s.complement()` | Complementary strand |
| `s.reverse_complement()` | Reverse complement |
| `s.transcribe()` | DNA → RNA (T → U) |
| `s.back_transcribe()` | RNA → DNA (U → T) |
| `s.translate()` | Nucleotide → protein |
| `s.translate(table=2)` | Translate with a specific codon table (see `seq-analysis.md`) |
| `s.translate(to_stop=True)` | Stop translating at the first stop codon |

`translate` uses the standard genetic code (table 1) unless you pass `table=`.
Use `cds=True` to validate a proper start/stop and translate alternative start
codons to `M`.

## `SeqRecord`

A `SeqRecord` is the object `SeqIO` hands you per record:

```python
record.id                 # primary identifier (e.g. accession)
record.name               # short name
record.description        # free-text description line
record.seq                # the Seq object
record.annotations        # dict: organism, taxonomy, references, ...
record.features           # list of SeqFeature (see seq-analysis.md)
record.letter_annotations # per-position data, e.g. {'phred_quality': [...]}
```

Slicing a record preserves per-letter annotations and features that fall inside
the slice:

```python
sub = record[10:30]                      # SeqRecord for positions 10–30
record.seq = record.seq.reverse_complement()
```

Build one from scratch:

```python
from Bio.SeqRecord import SeqRecord
rec = SeqRecord(Seq("ATGCGATCG"), id="seq001", name="mine",
                description="test sequence")
```

## `Bio.SeqIO` — the four core functions

```python
from Bio import SeqIO

# parse: iterator over ALL records (the workhorse)
for record in SeqIO.parse("seqs.fasta", "fasta"):
    ...

# read: exactly ONE record, else raises (use for single-record files)
record = SeqIO.read("single.gb", "genbank")

# write: SeqRecord(s) -> file, returns count written
n = SeqIO.write(records, "out.fasta", "fasta")

# convert: shortcut for parse+write between formats
n = SeqIO.convert("in.gbk", "genbank", "out.fasta", "fasta")
```

Format strings are **lowercase**. Common ones: `fasta`, `fasta-2line`, `fastq`,
`genbank`/`gb`, `embl`, `swiss` (SwissProt), `tab`, `qual`, `abi`, `sff`.

## Random access to large files

Three strategies, cheapest first:

```python
# 1. to_dict — loads everything into RAM (small/medium files only)
d = SeqIO.to_dict(SeqIO.parse("seqs.fasta", "fasta"))
d["seq_id"]

# 2. index — lazy dict, records read on demand (memory efficient)
idx = SeqIO.index("seqs.fasta", "fasta")
idx["seq_id"]; idx.close()

# 3. index_db — SQLite-backed index, spans multiple files / millions of records
idx = SeqIO.index_db("seqs.idx", "seqs.fasta", "fasta")
idx["seq_id"]; idx.close()
```

`to_dict`/`index` require unique record IDs; pass a `key_function` to derive keys
otherwise.

## Low-level parsers (speed-critical, high-throughput)

Return plain tuples instead of `SeqRecord` objects — far less overhead:

```python
from Bio.SeqIO.FastaIO import SimpleFastaParser
with open("seqs.fasta") as h:
    for title, sequence in SimpleFastaParser(h):
        ...

from Bio.SeqIO.QualityIO import FastqGeneralIterator
with open("reads.fastq") as h:
    for title, sequence, quality in FastqGeneralIterator(h):
        ...
```

## Compressed input

```python
import gzip
with gzip.open("seqs.fasta.gz", "rt") as h:      # note text mode "rt"
    for record in SeqIO.parse(h, "fasta"):
        ...

from Bio import bgzf                              # BGZF allows random access
with bgzf.open("seqs.fasta.bgz", "rt") as h:
    records = SeqIO.parse(h, "fasta")
```

## Common patterns

**Filter and stream to a new file** (generator keeps memory flat):

```python
long_seqs = (r for r in SeqIO.parse("in.fasta", "fasta") if len(r) > 500)
SeqIO.write(long_seqs, "filtered.fasta", "fasta")
```

**FASTQ quality filtering:**

```python
good = (r for r in SeqIO.parse("reads.fastq", "fastq")
        if min(r.letter_annotations["phred_quality"]) >= 20)
SeqIO.write(good, "clean.fastq", "fastq")
```

**Pull annotations from GenBank:**

```python
for r in SeqIO.parse("in.gbk", "genbank"):
    print(r.id, r.annotations.get("organism", "Unknown"))
```

## Edge cases

- `SeqIO.read` raises if the file has zero or more than one record — use `parse`
  when unsure of count.
- Not every record carries every field; use `.annotations.get(key, default)`.
- Writing FASTQ requires `phred_quality` letter annotations; converting FASTA →
  FASTQ fails without them.
- Translating a sequence whose length is not a multiple of 3 warns and drops the
  trailing partial codon.
