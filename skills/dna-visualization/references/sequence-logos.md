# Sequence Logos (logomaker)

A sequence logo shows, per alignment column, which residues occur and how
conserved the position is. Height in **information mode** is measured in bits
(`log2` of the alphabet size at full conservation); **probability mode** shows
raw frequencies summing to 1.

## Read the alignment

`AlignIO.read` requires an *aligned* file — every row the same length.

```python
from Bio import AlignIO
alignment = AlignIO.read("alignment.fasta", "fasta")   # or "clustal"
```

Simple format detection from the first line:

- starts with `>` → `"fasta"`
- starts with `CLUSTAL` or `MUSCLE` → `"clustal"`
- otherwise default to `"fasta"`

If rows differ in length, align first with MUSCLE/MAFFT/Clustal Omega, then read.

## Build the counts matrix

```python
import pandas as pd

seqs = [str(rec.seq) for rec in alignment]
length = len(seqs[0])

# Alphabet auto-detection: >4 distinct non-gap letters ⇒ treat as protein
all_chars = set("".join(seqs)) - {"-", "."}
alphabet = sorted(all_chars) if len(all_chars) > 4 else ["A", "C", "G", "T"]

counts = pd.DataFrame(0.0, index=range(length), columns=alphabet)
for seq in seqs:
    for i, ch in enumerate(seq):
        if ch in alphabet:
            counts.at[i, ch] += 1        # gaps and out-of-alphabet chars ignored
```

The matrix is **positions (rows) × alphabet (columns)** — the layout
`logomaker.Logo` expects.

## Information vs probability

```python
import logomaker

# Information content (bits) — conservation
matrix = logomaker.transform_matrix(counts, from_type="counts", to_type="information")

# Probability — per-column frequencies (rows sum to 1)
matrix = counts.div(counts.sum(axis=1), axis=0).fillna(0)
```

`transform_matrix` handles the small-sample correction and the counts→bits math;
prefer it over hand-rolling the entropy calculation.

## Slice to a sub-region

Positions are 0-indexed; `end` is exclusive. Reset the index so the x-axis starts
at 0 after slicing:

```python
matrix = matrix.iloc[start:end].reset_index(drop=True)
```

## Draw

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(10, 3))
logo = logomaker.Logo(matrix, ax=ax, shade_below=0.5, fade_below=0.5)

if information_mode:
    max_bits = np.log2(len(matrix.columns))   # 2.0 for DNA, ~4.32 for protein
    ax.set_ylabel("Information (bits)")
    ax.set_ylim(0, max_bits * 1.1)
else:
    ax.set_ylabel("Probability")
    ax.set_ylim(0, 1.05)

ax.set_xlabel("Position")
logo.style_spines(visible=False)
logo.style_spines(spines=["left", "bottom"], visible=True)
plt.tight_layout()
plt.savefig("logo.svg", dpi=300, bbox_inches="tight")
```

`logomaker.Logo` accepts an existing `ax`, so a logo can be embedded as one panel
of a larger figure.

## Choosing the mode

- **Information (bits)** — use for conservation analysis and motif discovery;
  tall stacks = conserved positions, short = variable. This is the classic
  Schneider–Stephens logo.
- **Probability** — use to communicate raw base/residue frequency at each
  position when you do not want the information-content weighting.

## Gotchas

- **Alphabet misdetection**: ambiguity codes (`N`, `R`, `Y`) or stray characters
  can push a DNA alignment over the 4-letter threshold and it renders as
  "protein". Force `alphabet = ["A","C","G","T"]` explicitly for nucleotide data.
- **All-gap or empty columns** in probability mode divide by zero; `.fillna(0)`
  keeps them blank rather than raising.
- **Color scheme**: `logomaker.Logo(..., color_scheme="classic")` for the
  standard nucleotide colors (`A` green, `C` blue, `G` orange/gold, `T` red);
  `"chemistry"` or `"skylign_protein"` for amino acids.
- **RNA input**: `U` is not in the default DNA alphabet. Either add it
  (`["A","C","G","U"]`) or transcribe `U→T` before counting.
