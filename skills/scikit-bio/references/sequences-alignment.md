# Sequences & Alignment

Deep reference for `skbio` grammared sequences and pairwise/multiple alignment.
Return to `SKILL.md` for the capability map.

## Sequence classes

Use `DNA`, `RNA`, `Protein` for validated (grammared) sequences and the generic
`Sequence` when you need no alphabet restrictions.

```python
from skbio import DNA, RNA, Protein, Sequence

dna = DNA("ATGCGATCG", metadata={"id": "seq1", "description": "example"})
rna = RNA("AUCGAUCG")
prot = Protein("ACDEFGHIKLMNPQRSTVWY")
generic = Sequence("XYZ123")            # no alphabet validation
```

### Transforms

```python
rc      = dna.reverse_complement()
mrna    = dna.transcribe()              # DNA → RNA
protein = mrna.translate()              # RNA → Protein (standard code)
protein = mrna.translate(genetic_code=11)   # e.g. bacterial code table
```

`translate()` accepts an NCBI genetic-code table number. `DNA.translate()` also
exists as a convenience (transcribes internally).

### Searching, motifs, k-mers

```python
positions = dna.find_with_regex("ATG.{3}")   # generator of slice objects
kmers     = dna.kmer_frequencies(k=3)         # dict {kmer: count}
degens    = dna.has_degenerates()             # bool: any ambiguous bases?
clean     = dna.degap()                       # strip gap characters
```

### Metadata (three levels)

- **Sequence-level** — `seq.metadata` (dict: `id`, `description`, arbitrary keys).
- **Positional** — `seq.positional_metadata` (a pandas DataFrame, one row per
  position). FASTQ quality scores load here under the `quality` column.
- **Interval** — `seq.interval_metadata` for features/regions.

```python
reads = DNA.read("reads.fastq", format="fastq", variant="illumina1.8")
q = reads.positional_metadata["quality"]      # per-base Phred scores

dna.interval_metadata.add([(5, 15)], metadata={"type": "gene", "name": "geneA"})
```

### Sequence distances

```python
d = seq1.distance(seq2)                        # Hamming by default (equal length)
from skbio.sequence.distance import kmer_distance
d = seq1.distance(seq2, metric=kmer_distance, k=3)
```

Hamming distance requires equal-length sequences (align or `degap` first if they
differ).

## Pairwise alignment

scikit-bio 0.6+ ships a unified `pair_align` alongside the older
function family. Know which one you are calling — **their return types differ.**

### Modern interface — `pair_align`

```python
from skbio.alignment import pair_align

aln = pair_align(seq1, seq2, mode="local")     # "local" | "global" | "semiglobal"
aln.score                                       # alignment score
aln.paths                                       # list of PairAlignPath objects
```

Returns a `PairAlignResult` (has `.score`, `.paths`). Use this for new code.

### Classic functions (3-tuple return)

```python
from skbio.alignment import (
    local_pairwise_align, global_pairwise_align,
    local_pairwise_align_nucleotide, global_pairwise_align_nucleotide,
    local_pairwise_align_protein, global_pairwise_align_protein,
)

# Full control: supply penalties + substitution matrix
msa, score, start_end = local_pairwise_align(
    seq1, seq2,
    gap_open_penalty=5, gap_extend_penalty=2,
    substitution_matrix=sub_matrix,            # 2D dict of scores
)
```

These return a **3-tuple** `(TabularMSA, score, start_end_positions)` — *not* an
object with a `.score` attribute. The `_nucleotide` / `_protein` convenience
variants fill in default penalties and matrices (e.g. BLOSUM50 for protein), so
you can omit those arguments.

### SSW (Striped Smith-Waterman) — fast local alignment

```python
from skbio.alignment import StripedSmithWaterman, local_pairwise_align_ssw

query = StripedSmithWaterman("ACGTACGTACGT")
result = query("ACGTAAAAACGT")
result.optimal_alignment_score
result.aligned_query_sequence
result.aligned_target_sequence
result.target_begin, result.target_end_optimal

# Convenience wrapper over SSW returning the classic 3-tuple:
msa, score, start_end = local_pairwise_align_ssw(seq1, seq2)
```

`StripedSmithWaterman` is the fastest local aligner here; pass
`protein=True` and `substitution_matrix="blosum62"` for protein queries.

## Multiple sequence alignment — `TabularMSA`

`TabularMSA` stores an aligned set of same-length grammared sequences.

```python
from skbio.alignment import TabularMSA
from skbio import DNA

msa = TabularMSA.read("alignment.fasta", constructor=DNA)   # or build manually
msa = TabularMSA([DNA("ATCG--"), DNA("ATGG--"), DNA("ATCGAT")])

cons = msa.consensus()               # consensus sequence
entropies = msa.conservation()       # per-column conservation
first = msa[0]                       # a sequence (row)
col2  = msa[:, 2]                    # a column across all sequences
```

`TabularMSA` requires all sequences to be the same length (they are aligned).
It integrates with the diversity/tree code once you derive a distance matrix.

## CIGAR / alignment paths

```python
from skbio.alignment import AlignPath
path = AlignPath.from_cigar("10M2I5M3D10M")   # parse a CIGAR string
```

`AlignPath` (and `PairAlignPath` from `pair_align`) encode gap structure
compactly and convert to/from CIGAR for interoperability with SAM-style tools.

## Interop

- Convert to/from Biopython or Biotite via shared formats (FASTA, etc.) — write
  with `skbio.io.write` and re-parse in the other library.
- For NCBI fetch, BLAST, or 3D structures, hand off to `biopython`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `AttributeError: 'tuple' object has no attribute 'score'` | You used a classic `*_pairwise_align*` return as an object — unpack `(msa, score, start_end)` or switch to `pair_align`. |
| Hamming `distance` raises on unequal lengths | Sequences differ in length — align, or use a length-tolerant metric like `kmer_distance`. |
| Alignment "fails" on equal-length inputs | They are already aligned — `degap()` both before re-aligning. |
| Empty/garbled `translate()` output | Wrong reading frame or genetic code — slice to the ORF and pass the right `genetic_code`. |
