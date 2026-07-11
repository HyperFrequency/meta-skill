# Alignment — `Bio.Align`, `Bio.AlignIO`

`Bio.Align.PairwiseAligner` does pairwise alignment; `Bio.AlignIO` reads and
writes multiple-sequence alignment (MSA) files. To *compute* an MSA you shell
out to an external aligner (see the bottom of this file).

## `PairwiseAligner`

The aligner auto-selects the algorithm (Needleman–Wunsch global,
Smith–Waterman local, Gotoh, Waterman–Smith–Beyer) from your gap parameters.

```python
from Bio import Align
from Bio.Seq import Seq

aligner = Align.PairwiseAligner()
# Defaults (Biopython 1.85): match +1.0, mismatch 0.0, all gaps -1.0
aligner.mode = "global"          # or "local"

alignments = aligner.align(Seq("ACCGGT"), Seq("ACGGT"))
best = alignments[0]
print(best)            # prints the aligned block
print(best.score)      # alignment score
score_only = aligner.score("ACCGGT", "ACGGT")   # score without building alignment
```

`aligner.align(...)` returns a lazily-evaluated container of all
co-optimal alignments; index `[0]` for one, or iterate. For long, divergent
sequences the number of optimal alignments can explode — take the first rather
than materializing all.

### Scoring parameters

```python
aligner.match_score = 2.0
aligner.mismatch_score = -1.0
aligner.gap_score = -0.5                  # symmetric shortcut

# Separate open/extend (affine gaps):
aligner.open_gap_score = -10
aligner.extend_gap_score = -0.5

# Internal vs. end gaps (semi-global / "glocal"): set end gaps to 0 to stop
# penalizing overhangs.
aligner.left_open_gap_score = 0
aligner.left_extend_gap_score = 0
aligner.right_open_gap_score = 0
aligner.right_extend_gap_score = 0
```

### Substitution matrices (protein alignment)

```python
from Bio.Align import substitution_matrices

print(substitution_matrices.load())          # list available names
matrix = substitution_matrices.load("BLOSUM62")
aligner.substitution_matrix = matrix
aligner.open_gap_score = -10
aligner.extend_gap_score = -0.5
aligner.align(Seq("KEVLA"), Seq("KSVLA"))
```

Available: `BLOSUM45/50/62/80/90`, `PAM30/70/250`, and others. Do not set both a
`substitution_matrix` and `match_score`/`mismatch_score` — the matrix wins for
scoring residue pairs.

## `Bio.AlignIO` — reading/writing MSAs

Same shape as `SeqIO`, but each "record" is a whole alignment:

```python
from Bio import AlignIO

msa = AlignIO.read("aln.aln", "clustal")          # single alignment
for msa in AlignIO.parse("many.sto", "stockholm"): # multiple alignments
    ...
AlignIO.write(msa, "out.phy", "phylip")
AlignIO.convert("in.aln", "clustal", "out.sto", "stockholm")
```

Formats: `clustal`, `phylip`, `phylip-relaxed` (long names), `stockholm`,
`fasta` (aligned), `nexus`, `emboss`, `msf`, `maf`.

### Working with an alignment object

```python
len(msa)                       # number of sequences (rows)
msa.get_alignment_length()     # number of columns
for record in msa:             # each row is a SeqRecord
    print(record.id, record.seq)

msa[0]        # first sequence (SeqRecord)
msa[:, 0]     # first column (str)
msa[:, 10:20] # sub-alignment, columns 10–19
msa[2, 5]     # single residue
```

### Consensus / PSSM

```python
from Bio.Align import AlignInfo
summary = AlignInfo.SummaryInfo(msa)
consensus = summary.dumb_consensus(threshold=0.7)
pssm = summary.pos_specific_score_matrix(consensus)
```

### Build an MSA object in memory

```python
from Bio.Align import MultipleSeqAlignment
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq

msa = MultipleSeqAlignment([
    SeqRecord(Seq("ACTGCTAGCTAG"), id="seq1"),
    SeqRecord(Seq("ACT-CTAGCTAG"), id="seq2"),
])
msa.append(SeqRecord(Seq("ACTGCTA-CTAG"), id="seq3"))  # must match column count
```

All rows must be the same length — `MultipleSeqAlignment` represents an
*already aligned* set, not raw sequences.

## Running an external aligner (Clustal Omega, MUSCLE, MAFFT)

The old `Bio.Align.Applications.*Commandline` wrappers were **deprecated and
removed** (the whole `Bio.Application` framework is gone in current Biopython).
Call the tool yourself and read the result back with `AlignIO`:

```python
import subprocess
from Bio import AlignIO

subprocess.run(
    ["clustalo", "-i", "seqs.fasta", "-o", "aln.fasta", "--outfmt", "fasta",
     "--force"],
    check=True,
)
msa = AlignIO.read("aln.fasta", "fasta")

# MUSCLE v5:
subprocess.run(["muscle", "-align", "seqs.fasta", "-output", "aln.fasta"],
               check=True)
# MAFFT (writes to stdout):
with open("aln.fasta", "w") as out:
    subprocess.run(["mafft", "--auto", "seqs.fasta"], stdout=out, check=True)
```

## Common patterns

**Percent identity of two aligned rows** (ignoring gap columns):

```python
def pct_identity(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x != "-" and y != "-"]
    if not pairs:
        return 0.0
    return sum(x == y for x, y in pairs) / len(pairs)
```

**Conserved columns (> 80% agreement):**

```python
cons = []
for i in range(msa.get_alignment_length()):
    col = msa[:, i]
    top = max(set(col), key=col.count)
    if col.count(top) / len(col) > 0.8:
        cons.append(i)
```

## Gotchas

- `Bio.pairwise2` is deprecated — always prefer `PairwiseAligner`.
- Setting a gap-open score without a gap-extend score gives a linear (not
  affine) gap model; set both for realistic protein gaps.
- `msa[:, i]` returns a `str`; `.count()` works but the column includes gaps.
