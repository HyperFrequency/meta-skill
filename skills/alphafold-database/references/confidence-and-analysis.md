# AlphaFold DB — Confidence Interpretation and Structure Analysis

How to read AlphaFold's two confidence signals correctly, and how to parse and
analyze the downloaded structures. For file formats and JSON schemas see
`api-reference.md`; for the parser itself see the `biopython` skill.

## pLDDT — per-residue local confidence

pLDDT (predicted Local Distance Difference Test) scores each residue 0–100. It rates
whether the **local** structure around that residue is right — it says nothing about
global domain arrangement.

| pLDDT | Category   | Interpretation                                            |
| ----- | ---------- | --------------------------------------------------------- |
| > 90  | very_high  | Backbone and side chains reliable; safe for detailed work |
| 70–90 | high       | Backbone reliable; side-chain detail weaker               |
| 50–70 | low        | Treat with caution; often genuinely flexible              |
| < 50  | very_low   | Frequently intrinsically disordered; do not over-interpret |

Load per-residue pLDDT from the confidence JSON:

```python
import requests

entry = "AF-P00520-F1"
conf = requests.get(
    f"https://alphafold.ebi.ac.uk/files/{entry}-confidence_v6.json"
).json()
plddt = conf["confidenceScore"]                       # list, one per residue
high = [i for i, s in enumerate(plddt, 1) if s > 90]  # 1-based residue indices
print(f"{len(high)}/{len(plddt)} residues at very-high confidence")
```

Low-pLDDT stretches are a strong (not definitive) predictor of intrinsic disorder —
useful for flagging linkers and tails before docking or design.

## PAE — relative domain confidence

PAE (Predicted Aligned Error) is an N×N matrix. `pae[i][j]` is the expected error
(Å) in residue *j*'s position when the structure is aligned on residue *i*. It captures
**relative** placement of parts of the chain. The JSON response is a one-element list;
read the matrix as `resp[0]["predicted_aligned_error"]` (see `api-reference.md`).

| PAE (Å) | Interpretation                                       |
| ------- | ---------------------------------------------------- |
| < 5     | Confident relative positioning of the two residues   |
| 5–15    | Moderate                                             |
| > 15    | Uncertain; the two regions may move independently    |

Key mental model: a protein can be **high pLDDT everywhere** (each domain well folded)
yet have **high inter-domain PAE** (their relative orientation is unknown). Low PAE
blocks along the diagonal reveal rigid domains; high PAE between blocks reveals flexible
hinges. Use PAE — not pLDDT — to decide whether a multi-domain arrangement is trustworthy.

Visualize the matrix:

```python
import numpy as np, matplotlib.pyplot as plt, requests

entry = "AF-P00520-F1"
pae = requests.get(
    f"https://alphafold.ebi.ac.uk/files/{entry}-predicted_aligned_error_v6.json"
).json()
m = np.array(pae[0]["predicted_aligned_error"])   # response is a 1-element list

plt.figure(figsize=(8, 7))
plt.imshow(m, cmap="viridis_r", vmin=0, vmax=30)
plt.colorbar(label="PAE (Å)")
plt.xlabel("Residue"); plt.ylabel("Residue")
plt.title(f"Predicted Aligned Error — {entry}")
plt.savefig(f"{entry}_pae.png", dpi=300, bbox_inches="tight")
```

## Parsing structures with Biopython

pLDDT is stored in the B-factor column, so you can read confidence straight from the
coordinate file without the JSON:

```python
from Bio.PDB import MMCIFParser

structure = MMCIFParser(QUIET=True).get_structure("p", f"{entry}-model_v6.cif")
plddt = [res["CA"].get_bfactor()
         for res in structure.get_residues() if "CA" in res]
high_conf = [(i, s) for i, s in enumerate(plddt, 1) if s > 90]
```

Extract Cα coordinates and build a contact map:

```python
import numpy as np
from scipy.spatial.distance import pdist, squareform

ca = np.array([res["CA"].get_coord()
               for res in structure.get_residues() if "CA" in res])
dist = squareform(pdist(ca))
contacts = np.argwhere((dist > 0) & (dist < 8.0))   # residue pairs within 8 Å
print(f"{len(contacts) // 2} contacts, {len(ca)} residues")
```

## Batch multi-protein processing

Summarize confidence across many accessions into a DataFrame. Guard every network
call, since some accessions have no prediction (404) or are fragmented:

```python
import requests, numpy as np, pandas as pd
from Bio.PDB import alphafold_db

rows = []
for acc in ["P00520", "P12931", "P04637"]:
    try:
        preds = list(alphafold_db.get_predictions(acc))
        if not preds:
            continue
        entry = preds[0]["entryId"]
        alphafold_db.download_cif_for(preds[0], directory="./batch")
        conf = requests.get(
            f"https://alphafold.ebi.ac.uk/files/{entry}-confidence_v6.json"
        ).json()["confidenceScore"]
        rows.append({
            "uniprot": acc,
            "entry": entry,
            "length": len(conf),
            "mean_plddt": float(np.mean(conf)),
            "frac_very_high": sum(s > 90 for s in conf) / len(conf),
        })
    except Exception as err:            # network/404/parse — log and continue
        print(f"skip {acc}: {err}")

df = pd.DataFrame(rows)
```

## Analysis caveats

- **High pLDDT ≠ functional accuracy.** Confidence measures geometric reliability, not
  that the modeled conformation is the biologically relevant one.
- **Apo, single-chain models.** No ligands, ions, cofactors, PTMs, or partner chains —
  binding-site geometry may differ from the holo state.
- **Fragmented proteins** (`F1, F2, …`) overlap; stitch or analyze fragments deliberately.
- **PAE is asymmetric** — do not assume `pae[i][j] == pae[j][i]`.
