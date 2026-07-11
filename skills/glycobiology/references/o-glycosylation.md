# O-Glycosylation Hotspot Scoring

Mucin-type O-glycosylation attaches GalNAc to the hydroxyl of a serine (S) or
threonine (T). Unlike N-glycosylation there is **no strict consensus sequon** —
occupancy is governed by a family of GalNAc-transferases with overlapping,
context-dependent specificities. Sites cluster in Ser/Thr/Pro-rich "PTS" mucin
domains. Because there is no clean motif, the best a sequence-only method can do
is flag **hotspot regions** by S/T density; per-residue calls from this heuristic
are noisy and carry a high false-positive rate. For real probabilities use
NetOGlyc 4.0 (see `references/glycan-resources.md`).

> Scope: this heuristic targets secreted/membrane **mucin-type O-GalNAc**
> glycosylation. It does **not** model intracellular **O-GlcNAc** (a distinct
> single-sugar, nucleocytoplasmic, cycling modification on S/T) — different
> enzymes, different biology, different tooling.

## Core function

```python
import numpy as np

def predict_o_glyc_hotspots(sequence, window_size=11, threshold=0.3):
    """Flag O-glycosylation hotspots by sliding-window Ser/Thr density.

    Args:
        sequence: protein sequence string.
        window_size: sliding window length (odd values center cleanly).
        threshold: minimum S+T fraction in a window to mark its S/T residues.

    Returns: list of per-residue site dicts (1-based `position`, `residue`,
    `near_proline`). Merge them into regions with `merge_hotspot_regions`.
    """
    seq = str(sequence).upper()
    n = len(seq)
    if n < window_size:
        return []

    flagged = set()
    for i in range(n - window_size + 1):
        window = seq[i:i + window_size]
        density = (window.count("S") + window.count("T")) / window_size
        if density > threshold:
            for j in range(i, i + window_size):
                if seq[j] in ("S", "T"):
                    flagged.add(j)

    sites = []
    for pos in sorted(flagged):
        near_p = (
            (pos > 0 and seq[pos - 1] == "P")
            or (pos < n - 1 and seq[pos + 1] == "P")
        )
        sites.append({
            "position": pos + 1,
            "residue": seq[pos],
            "near_proline": near_p,     # proline neighbor: often lowers occupancy
        })
    return sites
```

## Merging residues into regions

Reviewers reason about **regions** (mucin domains), not scattered residues. Merge
adjacent flagged S/T (allowing a small gap) into contiguous hotspots:

```python
def merge_hotspot_regions(o_sites, max_gap=2):
    """Collapse nearby O-glyc residues into (start, end) regions (1-based)."""
    if not o_sites:
        return []
    positions = sorted(s["position"] for s in o_sites)
    regions, start, end = [], positions[0], positions[0]
    for pos in positions[1:]:
        if pos <= end + max_gap:
            end = pos
        else:
            regions.append((start, end))
            start = end = pos
    regions.append((start, end))
    return regions
```

## Tuning the knobs

| Parameter | Effect | When to change |
| --- | --- | --- |
| `threshold` (default 0.3) | Higher → fewer, denser hotspots | Raise to 0.4–0.5 if you get too many regions; lower to catch sparse mucin edges |
| `window_size` (default 11) | Smaller → sharper, noisier; larger → smoother, misses short motifs | Use 15–20 to find broad mucin domains, 7–11 for local S/T clusters |
| `near_proline` flag | Marks S/T with a Pro neighbor | Note that Pro flanking is common *within* real mucin domains — do not blanket-drop these; use as one signal among several |

Proline is doubled-edged for O-glycosylation: mucin PTS domains are proline-rich,
so a Pro neighbor is *not* a clean negative the way `N-X-S/T-P` is for
N-glycosylation. Report the flag; do not filter on it alone.

## Interpreting the output honestly

- A hotspot means "this region is S/T-dense, worth checking" — nothing more.
- The false-positive rate is high; never present per-residue O-sites as
  predictions without the NetOGlyc caveat.
- Extracellular/secreted topology matters: an S/T-rich intracellular loop is not a
  mucin-type O-glyc candidate. Confirm topology before trusting a hotspot.

## Edge cases

- **Sequence shorter than `window_size`** → returns `[]` (no window fits).
- **Uniformly S/T-poor protein** → no hotspots; that is the correct answer, not a
  bug. Lowering the threshold to force hits produces noise.
- **Very long, uniformly S/T-rich mucin** → one giant merged region; that is
  faithful, but consider a smaller `max_gap` or per-window reporting if you need
  sub-region resolution.
