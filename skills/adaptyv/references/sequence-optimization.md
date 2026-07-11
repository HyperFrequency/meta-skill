# Pre-Submission Sequence Optimization

Wet-lab cycles are slow (~weeks) and metered. Spend cheap compute up front to avoid paying to
test sequences that will not express or fold. This is filtering and enrichment, not a
guarantee — predictions are probabilistic, so keep controls and let experimental results
recalibrate your thresholds.

## The three failure modes to screen for

1. **Unpaired cysteines** → form spurious disulfides → aggregation/misfolding → lower yield.
   Remove or repair them unless a cysteine is functionally required (a structural disulfide,
   catalytic residue, etc.). A quick parity check flags the odd-count case:
   ```python
   def unpaired_cysteine_warning(sequence: str) -> int:
       cys = sequence.upper().count("C")
       if cys % 2:
           print(f"Warning: odd cysteine count ({cys}) — possible unpaired thiol")
       return cys
   ```
   Parity is only a heuristic; a full check needs structure (which cysteines are spatially
   paired).

2. **Excessive surface hydrophobicity** → aggregation and poor aqueous solubility. Look at
   hydropathy (Kyte–Doolittle), GRAVY, and — with a structure — solvent-accessible
   hydrophobic exposure.

3. **Low predicted solubility** → inclusion bodies, precipitation, hard purification.

## Tools (capability + where they live)

These are **independent third-party tools with their own installs, weights, and licenses** —
there is no single package. Do not assume a `pip install` name; check each tool's own
repository/service for the current invocation. Discover model weights (ESM, ProteinMPNN
variants, structure predictors) through `hugging-science`.

| Tool | Role | Where it lives / notes |
| --- | --- | --- |
| **NetSolP** | Fast solubility/usability prediction — first-pass filter for large libraries | DTU Health Tech web service (protein language-model based) |
| **SoluProt** | Solubility prediction, complementary second opinion | Loschmidt Labs web service |
| **SolubleMPNN** | Sequence **redesign** for improved solubility while preserving fold | The "soluble" weight set for ProteinMPNN (`dauparas/ProteinMPNN`); structure-conditioned inverse folding |
| **ESM** | Sequence log-likelihood — how "natural" a sequence looks; ranks/filters designs | `facebookresearch/esm` (`fair-esm`); e.g. `esm2_t33_650M_UR50D` |
| **ipTM** | Interface confidence for binders (protein–protein) | Interface pTM from AlphaFold-Multimer / ColabFold |
| **Hydrophobic exposure** | Aggregation risk from solvent-accessible hydrophobic surface | SASA-based; compute from a structure (DSSP/FreeSASA) |

> The upstream source calls the last metric "pSAE" and defines it as the percent of
> solvent-accessible surface occupied by hydrophobic residues. That acronym is not standard —
> the underlying concept (SASA-weighted surface hydrophobicity as an aggregation proxy) is
> real and close in spirit to Spatial Aggregation Propensity (SAP). Use the concept; don't
> rely on the acronym.

## ESM likelihood (accurate `fair-esm` usage)

This is the one snippet with a stable, verifiable API. Higher mean token log-prob ≈ a more
natural sequence.

```python
import torch
from esm import pretrained

model, alphabet = pretrained.esm2_t33_650M_UR50D()
model.eval()
batch_converter = alphabet.get_batch_converter()

def esm_naturalness(sequence: str) -> float:
    _, _, tokens = batch_converter([("protein", sequence)])
    with torch.no_grad():
        logits = model(tokens, repr_layers=[33])["logits"]
    return logits.log_softmax(dim=-1).mean().item()
```

Use it to compare variants and reject unnatural over-mutation from redesign — not as a
standalone quality score.

## Solvent-accessible hydrophobic exposure (needs a structure)

Given a PDB (experimental or predicted), compute the fraction of exposed surface that is
hydrophobic. Lower is better. Sketch with Biopython + DSSP:

```python
from Bio.PDB import PDBParser, DSSP

HYDROPHOBIC = {"ALA","VAL","ILE","LEU","MET","PHE","TRP","PRO"}

def hydrophobic_exposure_pct(pdb_file: str) -> float:
    model = PDBParser(QUIET=True).get_structure("p", pdb_file)[0]
    dssp = DSSP(model, pdb_file)                     # needs the DSSP binary installed
    total = hydrophobic = 0.0
    for key in dssp.keys():
        res_name, rel_acc = dssp[key][1], dssp[key][3]  # relative solvent accessibility
        total += rel_acc
        if res_name in HYDROPHOBIC:
            hydrophobic += rel_acc
    return 100.0 * hydrophobic / total if total else 0.0
```

Rough reading: `< 25%` low aggregation risk, `25–35%` moderate, `> 35%` high. DSSP residue
names are 3-letter; the exact accessibility index into the DSSP tuple can vary by Biopython
version — verify against your installed version.

## Staged pipeline (conceptual)

Order the tools cheapest-first so most sequences are eliminated before you run anything
expensive. This is the pattern, not a drop-in library:

1. **Fast filter** — run NetSolP over the whole library; keep the top solubility scores.
2. **Second opinion + naturalness** — SoluProt and ESM on the survivors; combine into one
   ranking (e.g. weight solubility higher than naturalness).
3. **Redesign the borderline ones** — SolubleMPNN generates more-soluble variants; keep
   functional/critical residues fixed and re-score redesigns with ESM to reject unnatural
   drift.
4. **Structure-gate the finalists** — predict a structure, compute hydrophobic exposure, and
   for binders compute ipTM; drop candidates above your aggregation threshold or below your
   interface-confidence threshold.
5. **Submit** the survivors as a batch (`experiments.md`, `examples.md`), always with a
   wild-type control, and pass your computational scores in `metadata` so you can later
   correlate predictions against wet-lab truth.

## Practical cautions

- Keep functional residues fixed during redesign; provide a structure to SolubleMPNN so
  spatial constraints are respected.
- If redesign tanks ESM likelihood, you optimized too aggressively — dial back.
- If every sequence scores poorly, check for non-standard amino acids / malformed FASTA, or
  accept that the family may just be low-solubility and needs experimental validation.
- Use predictions as enrichment, not absolute filters — host system and buffer conditions
  move real expression, and the experiment is the ground truth.
