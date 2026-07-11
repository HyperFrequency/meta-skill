# GC-Content Plots (sliding window)

Plot the local GC fraction along a sequence to spot GC-rich islands, AT-rich
regions, and compositional bias (e.g. isochores, promoter/CpG regions, horizontal
transfer signatures).

## Compute the sliding window

```python
from Bio import SeqIO
import numpy as np

def read_sequence(path):
    if path.lower().endswith((".gb", ".gbk", ".genbank")):
        return SeqIO.read(path, "genbank")
    return SeqIO.read(path, "fasta")

def gc_content_sliding(seq, window, step):
    seq = str(seq).upper()
    positions, gc_values = [], []
    for i in range(0, len(seq) - window + 1, step):
        sub = seq[i:i + window]
        gc = (sub.count("G") + sub.count("C")) / len(sub)
        positions.append(i + window // 2)      # plot at window midpoint
        gc_values.append(gc)
    return np.array(positions), np.array(gc_values)
```

- **`window`** default 100 bp. Larger windows smooth the trace; smaller windows
  reveal fine structure but are noisier.
- **`step`** default `window // 4` (75% overlap). Set `step = window` for
  non-overlapping bins.
- The x-coordinate is the **window midpoint**, so the trace is centered.
- **Guard**: if `len(seq) < window` the loop yields nothing — check up front and
  either shrink the window or reject the input.

## Plot

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

seq = record.seq
seq_len = len(seq)
xs, gc = gc_content_sliding(seq, window=100, step=25)
overall = (str(seq).upper().count("G") + str(seq).upper().count("C")) / seq_len

fig, ax = plt.subplots(figsize=(12, 4))
ax.fill_between(xs, gc, alpha=0.3, color="#3498db")
ax.plot(xs, gc, color="#2980b9", linewidth=1)
ax.axhline(overall, color="#e74c3c", ls="--", lw=1, alpha=0.7,
           label=f"Overall GC: {overall:.1%}")
# optional fixed threshold line:
# ax.axhline(0.5, color="#f39c12", ls=":", lw=1, label="Threshold: 50%")

ax.set_xlabel("Position (bp)")
ax.set_ylabel("GC Content")
ax.set_ylim(0, 1)
ax.set_xlim(0, seq_len)
ax.legend(fontsize=9, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
plt.tight_layout()
plt.savefig("gc_plot.svg", dpi=300, bbox_inches="tight")
```

## GC skew (optional extension)

GC content ignores strand asymmetry. **GC skew** `(G − C) / (G + C)` per window
locates replication origins/termini in bacterial genomes (skew flips sign at the
origin). Same sliding loop, different per-window statistic:

```python
g, c = sub.count("G"), sub.count("C")
skew = (g - c) / (g + c) if (g + c) else 0.0
```

Plot the **cumulative** skew for the clearest origin/terminus V-shape.

## Gotchas

- **Lowercase / soft-masked bases**: uppercase the sequence first
  (`str(seq).upper()`), or masked regions read as 0% GC.
- **`N` runs**: ambiguous bases count as neither G nor C, dragging windows toward
  0. For assemblies with long `N` gaps, either skip windows above an N-fraction
  threshold or note the artifact.
- **Window vs step tradeoff**: a window far larger than the features you care
  about washes them out; match the window to the expected feature scale (e.g.
  ~200 bp for CpG islands, several kb for isochores).
- **Multi-record FASTA**: `SeqIO.read` errors on more than one record — loop with
  `SeqIO.parse` and plot per record, or concatenate deliberately.
