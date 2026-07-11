# Restriction Maps (Bio.Restriction + Matplotlib)

Find restriction-enzyme recognition/cut sites with Biopython's `Bio.Restriction`
module, then draw them as tick marks along a sequence backbone with Matplotlib.

## Read the sequence

```python
from Bio import SeqIO
def read_sequence(path):
    if path.lower().endswith((".gb", ".gbk", ".genbank")):
        return SeqIO.read(path, "genbank")
    return SeqIO.read(path, "fasta")
record = read_sequence("sequence.gb")
```

## Find cut sites

```python
from Bio.Restriction import RestrictionBatch, CommOnly

def find_cut_sites(seq, enzyme_names=None):
    batch = RestrictionBatch(enzyme_names) if enzyme_names else CommOnly
    results = batch.search(seq)                 # {EnzymeObject: [positions]}
    return {str(e): sorted(pos) for e, pos in results.items() if pos}
```

- **`CommOnly`** is the built-in batch of all commercially available common
  enzymes. Other prebuilt batches: `AllEnzymes`, `NonComm`.
- **`RestrictionBatch([...])`** takes enzyme names as strings. Names are
  **case-sensitive**: `EcoRI`, `BamHI`, `HindIII`, `NotI` — not lowercase.
- **`.search(seq)`** returns a dict mapping each enzyme to a list of cut
  positions. Positions are **1-based** (Biopython restriction convention) and
  empty lists mean "does not cut" — filter them out.
- Passing a raw string works, but wrap in `Bio.Seq.Seq` if you built the sequence
  by hand: `batch.search(Seq("ACGT..."))`.

## Draw

Sort enzymes by cut count (fewest first — usually the most useful for cloning)
and cap the number displayed so labels stay legible:

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sites = find_cut_sites(record.seq, ["EcoRI", "BamHI", "HindIII"])
seq_len = len(record.seq)
enzymes = sorted(sites, key=lambda e: len(sites[e]))[:15]   # max 15 rows

fig_h = max(3, 1 + len(enzymes) * 0.4)
fig, ax = plt.subplots(figsize=(14, fig_h))
ax.plot([0, seq_len], [0, 0], color="black", linewidth=2)   # backbone

PALETTE = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
           "#1abc9c", "#e67e22", "#34495e", "#d35400", "#8e44ad"]
for i, enz in enumerate(enzymes):
    color = PALETTE[i % len(PALETTE)]
    y = -(i + 1) * 0.35
    for pos in sites[enz]:
        ax.plot([pos, pos], [0, y], color=color, linewidth=1, alpha=0.7)
        ax.plot(pos, y, "v", color=color, markersize=5)
    ax.text(seq_len * 1.02, y, f"{enz} ({len(sites[enz])})",
            fontsize=9, va="center", color=color, fontweight="bold")

ax.set_xlim(-seq_len * 0.02, seq_len * 1.15)
ax.set_ylim(-(len(enzymes) + 1) * 0.35, 0.5)
ax.set_xlabel("Position (bp)")
ax.set_yticks([])
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
plt.tight_layout()
plt.savefig("restriction_map.svg", dpi=300, bbox_inches="tight")
```

## Circular sequences

`Bio.Restriction` search is linear by default. For a circular plasmid, cut sites
that span the origin are missed. Search a doubled sequence (`seq + seq`) and keep
positions `< seq_len`, or use `batch.search(seq, linear=False)` where the enzyme
API supports it, to catch origin-spanning sites.

## Selecting enzymes for cloning

- **Unique cutters** (exactly one site) are the useful ones for linearizing or
  inserting: `[e for e, p in sites.items() if len(p) == 1]`.
- **Non-cutters** in a region of interest matter too — an enzyme absent from an
  insert but present in the backbone MCS is a good directional-cloning choice.
- Restrict the batch to your available enzyme kit rather than `CommOnly` to keep
  the map readable and actionable.

## Gotchas

- **No sites found**: either the enzymes genuinely do not cut, or the names are
  misspelled. Fall back to `CommOnly` to confirm the sequence cuts at all.
- **Too many enzymes**: `CommOnly` on a long sequence produces a dense,
  unreadable plot; the fewest-cuts sort + 15-row cap above keeps it legible. Raise
  the cap only for short sequences.
- **Ambiguity codes** (`N`, `R`, `Y`) in the sequence can create spurious or
  missed matches depending on the enzyme's site definition — clean the sequence
  first if it contains many.
