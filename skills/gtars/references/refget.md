# Reference Sequences with refget

`gtars.refget` retrieves reference-genome sequences and computes content-based
digests following the **GA4GH refget** standard. Use it to identify a sequence
by its content (rather than a filename or accession), verify reference
integrity, and extract subsequences.

> Signatures are illustrative — verify with `help(gtars.refget)` and
> `gtars refget --help`.

## Why content digests

A refget digest is a hash of the sequence bytes, so the *same* sequence always
gets the *same* id regardless of file name or source. This lets you detect that
two "hg38" files actually differ, or confirm a pipeline used the reference it
claims to. The GA4GH standard digest is **sha512t24u**: SHA-512 of the
normalized sequence, truncated to 24 bytes and base64url-encoded, surfaced with
the `SQ.` prefix. (Do not assume a different truncation length — confirm the
exact form your version emits.)

## RefgetStore

```python
import gtars

store = gtars.RefgetStore()
store.add_sequence("chr1", sequence_bytes)
store.get_sequence("chr1")
store.get_digest("chr1")

# From a FASTA
store = gtars.RefgetStore.from_fasta("hg38.fa")
store.get_sequence("chr1")
store.get_subsequence("chr1", 1000, 2000)   # extract a region
```

## Digests

```python
from gtars.refget import compute_digest

digest = compute_digest(sequence_bytes)      # e.g. "SQ.<base64url>"
store.verify_digest("chr1", expected_digest) # integrity check
store.get_sequence_by_digest("SQ.<...>")     # content-addressed lookup
```

CLI:

```bash
gtars refget digest --input genome.fa --output digests.txt
gtars refget verify --sequence sequence.fa --digest <expected>
```

## Worked patterns

```python
# Validate a reference against expected digests
store  = gtars.RefgetStore.from_fasta("reference.fa")
actual = {c: store.get_digest(c) for c in store.chromosomes}
for chrom, expected in expected_digests.items():
    if actual.get(chrom) != expected:
        print(f"MISMATCH {chrom}: {actual.get(chrom)} != {expected}")

# Compare two reference builds by digest
hg19 = gtars.RefgetStore.from_fasta("hg19.fa")
hg38 = gtars.RefgetStore.from_fasta("hg38.fa")
for chrom in hg19.chromosomes:
    if hg19.get_digest(chrom) != hg38.get_digest(chrom):
        print(f"{chrom} differs between hg19 and hg38")
```

## Gotchas

- **Normalization matters.** The digest is defined over normalized sequence
  (case and, per spec, allowed characters). A soft-masked (lowercase) vs
  upper-case FASTA can produce a *different* digest if not normalized — confirm
  how your version normalizes before comparing across sources.
- **Coordinates.** `get_subsequence` follows BED-style 0-based half-open
  `[start, end)`; a 1-based request is off by one.
- **Large genomes.** Load on demand and rely on memory-mapped access rather than
  reading whole chromosomes into memory.
- **Digest form.** Verify whether your version returns the bare base64url string
  or the `SQ.`-prefixed form, and match the format your downstream tooling
  expects.
