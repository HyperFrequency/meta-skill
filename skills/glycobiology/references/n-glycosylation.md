# N-Glycosylation Sequon Finding

N-linked glycosylation attaches an oligosaccharide to the amide nitrogen of an
asparagine (N) that sits in a **sequon**: `N-X-S/T` where `X` is any residue
except proline. The rule is a strong necessary condition — the
oligosaccharyltransferase complex essentially requires it — but it is **not
sufficient**: occupancy depends on local structure, folding kinetics, and access
in the ER lumen. Expect a meaningful fraction of sequons to be unoccupied.

## Core function

```python
def find_n_glycosylation_sites(sequence, exclude_proline=True):
    """Find N-linked glycosylation sequons (N-X-S/T, X != P).

    Args:
        sequence: protein sequence (str or Bio.Seq).
        exclude_proline: apply the standard X != P rule (default True).

    Returns: list of dicts, each with 1-based `position`, `motif`, `x_residue`,
    `acceptor` (S or T), and a `context` window for readability.
    """
    seq = str(sequence).upper()
    sites = []
    for i in range(len(seq) - 2):
        if seq[i] != "N":
            continue
        x_residue, acceptor = seq[i + 1], seq[i + 2]
        if exclude_proline and x_residue == "P":
            continue
        if acceptor not in ("S", "T"):
            continue
        sites.append({
            "position": i + 1,              # 1-based Asn position
            "residue": seq[i],
            "motif": seq[i:i + 3],
            "x_residue": x_residue,
            "acceptor": acceptor,
            "context": seq[max(0, i - 5):i + 8],
        })
    return sites
```

## Efficiency modifiers (worth annotating, not filtering on)

The bare sequon hides real efficiency differences. Annotate rather than silently
drop these:

- **Proline immediately after the S/T** (`N-X-S/T-P`) sharply reduces glycan
  occupancy — one of the strongest negative signals.
- **`X = W`, `D`, `E`** tend to lower efficiency; `X = C` or `M` tends to be
  favorable. Treat as priors, not hard rules.
- **`T` acceptor** is glycosylated somewhat more efficiently than `S` on average.
- **Sequon near the N- or C-terminus** or inside a tight turn may be sterically
  blocked despite a perfect motif.

A pragmatic annotation pass:

```python
def annotate_efficiency(seq, i):
    """Flag known efficiency modifiers around an N at index i (0-based)."""
    notes = []
    if i + 3 < len(seq) and seq[i + 3] == "P":
        notes.append("reduced: proline after sequon (N-X-S/T-P)")
    if i > 0 and seq[i - 1] == "P":
        notes.append("reduced: proline before Asn")
    if seq[i + 1] in ("W", "D", "E"):
        notes.append(f"reduced: unfavorable X={seq[i+1]}")
    return notes or ["canonical sequon"]
```

## Non-canonical N-X-C sequons

A small number of sites are glycosylated at `N-X-C` (cysteine acceptor). These
are rare and often condition-dependent; scan for them **separately** and label
them clearly rather than merging into the canonical set, because their base
occupancy is much lower:

```python
def find_nxc_sequons(sequence):
    seq = str(sequence).upper()
    return [
        {"position": i + 1, "motif": seq[i:i + 3]}
        for i in range(len(seq) - 2)
        if seq[i] == "N" and seq[i + 1] != "P" and seq[i + 2] == "C"
    ]
```

## Batch scanning a FASTA

```python
from Bio import SeqIO
import pandas as pd

def scan_fasta_for_n_glyc(fasta_path):
    """Scan every record in a FASTA for N-glyc sequons; return per-record rows."""
    records = []
    for record in SeqIO.parse(fasta_path, "fasta"):
        sites = find_n_glycosylation_sites(str(record.seq))
        records.append({
            "id": record.id,
            "length": len(record.seq),
            "n_sites": len(sites),
            "density_per_1k": len(sites) / len(record.seq) * 1000,
            "sites": sites,
        })
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "sites"}
                       for r in records])
    print(f"{len(df)} sequences | total sites {df['n_sites'].sum()} | "
          f"mean density {df['density_per_1k'].mean():.1f} /1000 aa")
    return records
```

`density_per_1k` (sequons per 1000 residues) is a useful cross-protein
comparator — heavily glycosylated secreted proteins run high, cytoplasmic ones
near zero (and any hits there are almost certainly biological false positives).

## Edge cases

- **Sequence shorter than 3 residues** → no sites; the loop simply does not run.
- **Overlapping sequons** (`N-X-S/T` where the S/T is itself an `N` starting a new
  sequon) are reported independently; that is correct.
- **Lowercase / whitespace / gap characters** — upper-case and strip non-alpha
  before scanning, or coordinates drift. Biopython records are already clean;
  hand-pasted sequences often are not.
- **Selenocysteine (U), ambiguity codes (X, B, Z)** — leave them in place so
  positions stay faithful; they will simply never match the motif.
