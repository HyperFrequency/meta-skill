# ESMFold API Recipes

Copy-ready recipes for the four workflows in `SKILL.md`. All use the standard `fair-esm`
ESMFold API (`esm.pretrained.esmfold_v1()` → `model.infer_pdb(sequence)`) and read pLDDT
from the PDB B-factor column. Structure I/O uses Biopython.

## Device handling

Resolve the device once, up front, so failures are explicit rather than silent CPU fallback.

```python
import torch

def resolve_device(arg="auto"):          # "auto" | "cuda" | "cpu"
    if arg == "cpu":
        return torch.device("cpu")
    if arg == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but no GPU is available.")
    if arg in ("auto", "cuda") and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")           # auto with no GPU
```

Validate sequences against the 20-letter alphabet before folding; warn on unknown
characters, error on empty input, and warn past 800 residues (likely OOM):

```python
VALID = set("ACDEFGHIKLMNPQRSTVWY")
def check(seq):
    if not seq:
        raise SystemExit("Empty sequence.")
    bad = set(seq) - VALID
    if bad:
        print(f"WARNING: non-standard residues {bad} may hurt quality")
    if len(seq) > 800:
        print(f"WARNING: {len(seq)} residues — may OOM / degrade")
```

## 1. Single predict

```python
import torch, esm, numpy as np

model = esm.pretrained.esmfold_v1().eval().to(resolve_device("auto"))
model.set_chunk_size(128)                # lowers peak VRAM on long chains

with torch.no_grad():
    pdb = model.infer_pdb(sequence)      # PDB string, pLDDT in B-factor
open("predicted.pdb", "w").write(pdb)

plddt = np.array([float(l[60:66]) for l in pdb.splitlines()
                  if l.startswith("ATOM") and l[12:16].strip() == "CA"])
print(f"len={len(plddt)}  mean pLDDT={plddt.mean():.1f}  min={plddt.min():.1f}")
```

## 2. Batch predict

Load the model **once**, fold sequences one at a time to cap memory, and recover from OOM
per row instead of aborting the whole run. Accept multi-FASTA or a `name,sequence` CSV.

```python
import csv, os, torch, esm, numpy as np

def parse_fasta(path):
    recs, name, buf = [], None, []
    for line in open(path):
        line = line.strip()
        if not line: continue
        if line.startswith(">"):
            if name is not None: recs.append((name, "".join(buf).upper()))
            name, buf = line[1:].strip(), []
        else:
            buf.append(line)
    if name is not None: recs.append((name, "".join(buf).upper()))
    return recs

def parse_csv(path):                       # case-insensitive name/sequence columns
    rows = list(csv.DictReader(open(path, newline="")))
    cols = {c.lower().strip(): c for c in (rows[0].keys() if rows else [])}
    n, s = cols["name"], cols["sequence"]
    return [(r[n].strip(), r[s].strip().upper()) for r in rows if r[n] and r[s]]

model = esm.pretrained.esmfold_v1().eval().to(resolve_device("auto"))
model.set_chunk_size(128)

records = parse_csv(inp) if inp.lower().endswith(".csv") else parse_fasta(inp)
os.makedirs(out_dir, exist_ok=True)
summary = []
for name, seq in records:
    try:
        with torch.no_grad():
            pdb = model.infer_pdb(seq)
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            torch.cuda.empty_cache()       # recover, keep going
            summary.append({"name": name, "length": len(seq),
                            "mean_plddt": "OOM", "path": ""})
            continue
        raise
    plddt = [float(l[60:66]) for l in pdb.splitlines()
             if l.startswith("ATOM") and l[12:16].strip() == "CA"]
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:100]
    path = os.path.join(out_dir, f"{safe}.pdb")
    open(path, "w").write(pdb)
    summary.append({"name": name, "length": len(seq),
                    "mean_plddt": round(float(np.mean(plddt)), 2), "path": path})

with open(os.path.join(out_dir, "summary.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "length", "mean_plddt", "path"])
    w.writeheader(); w.writerows(summary)
```

## 3. Evaluate a model

Read pLDDT from B-factors, bucket into tiers, estimate secondary structure from backbone
dihedrals, and flag contiguous low-confidence stretches.

```python
import numpy as np
from Bio.PDB import PDBParser, is_aa

st = PDBParser(QUIET=True).get_structure("m", "predicted.pdb")
model0 = next(iter(st))
res = [(ch.id, r.id[1], r.resname, r["CA"].get_bfactor())
       for ch in model0 for r in ch if is_aa(r, standard=True) and "CA" in r]
plddt = np.array([x[3] for x in res])

tiers = {"very_high(>90)":  (plddt > 90).mean(),
         "confident(70-90)": ((plddt > 70) & (plddt <= 90)).mean(),
         "low(50-70)":       ((plddt > 50) & (plddt <= 70)).mean(),
         "very_low(<50)":    (plddt <= 50).mean()}
print("mean", round(plddt.mean(), 1), tiers)
```

**Low-confidence regions** — merge residues with pLDDT < 50 into contiguous runs (allowing
gaps of up to ~2 residues) so you report disordered *segments*, not isolated dips. Report
chain, start, end, length, and mean pLDDT per run.

**Secondary structure** — a fast Ramachandran approximation from φ/ψ (helix: φ∈[-160,-20],
ψ∈[-80,0]; sheet: φ∈[-180,-40] with ψ∈[50,180] or ψ∈[-180,-120]; else coil) via
`Bio.PDB.vectors.calc_dihedral`. This is an estimate only — **use DSSP for any quantitative
secondary-structure assignment.**

Assessment rule of thumb: mean pLDDT > 80 → high quality; 60-80 → fold likely right but
local detail unreliable; < 60 → treat with caution / likely disordered.

## 4. Compare against a reference

Align two structures by Cα and report RMSD, TM-score, and GDT-TS. Prefer `TMalign` when the
binary is on PATH; otherwise use Biopython superimposition plus the analytic TM-score.

```python
import numpy as np
from Bio.PDB import PDBParser, Superimposer, is_aa

def ca_by_resnum(path):
    st = PDBParser(QUIET=True).get_structure("s", path)
    out = {}
    for ch in next(iter(st)):
        for r in ch:
            if is_aa(r, standard=True) and "CA" in r:
                out[r.id[1]] = r["CA"]      # keyed by residue number
    return out

pred, ref = ca_by_resnum("predicted.pdb"), ca_by_resnum("experimental.pdb")
keys = sorted(set(pred) & set(ref))         # matched residue numbers
if len(keys) < 3:
    raise SystemExit("Fewer than 3 aligned residues.")
pa, ra = [pred[k] for k in keys], [ref[k] for k in keys]

sup = Superimposer(); sup.set_atoms(ra, pa)  # optimal superposition, moving atoms = pred
print(f"Cα-RMSD = {sup.rms:.2f} Å over {len(keys)} pairs")

rot, tran = sup.rotran
pc = np.array([a.coord for a in pa]) @ rot + tran
rc = np.array([a.coord for a in ra])
d = np.linalg.norm(pc - rc, axis=1)          # per-residue Cα distance
```

**TM-score (analytic fallback)** — normalized by reference length `L`:

```python
L = len(ref)                                 # normalize by target length
d0 = max(1.24 * (L - 15) ** (1/3) - 1.8, 0.5)
tm = np.sum(1.0 / (1.0 + (d / d0) ** 2)) / L
```

Because this uses residue-number alignment rather than optimal structural superposition, it
is an approximation — install `TMalign` (https://zhanggroup.org/TM-align/) for exact scores.

**GDT-TS** — mean of the fraction of Cα within 1, 2, 4, and 8 Å:

```python
gdt_ts = np.mean([(d <= t).mean() * 100 for t in (1, 2, 4, 8)])
```

**Interpretation.** TM-score > 0.5 → same fold; 0.17-0.5 → possible partial similarity;
< 0.17 → essentially unrelated. RMSD < 2 Å → excellent; 2-4 Å → good core; 4-8 Å → moderate,
fold maybe right; > 8 Å → poor / different conformation or fold. Residues deviating > 5 Å
usually mark flexible loops, domain shifts, or modelling errors.
