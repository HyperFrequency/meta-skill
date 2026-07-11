# Scoring Methods Reference

Theory, accuracy expectations, applicability domain, and selection guidance for
the four binding-affinity method families. Implementation recipes (real library
APIs) are in [implementation.md](implementation.md).

---

## Method 1 — Empirical Descriptor + Contact Scoring

### What it computes

A predicted pKd from two feature groups extracted from the protein-ligand
complex.

**Ligand descriptors (RDKit):**

- Molecular weight (MW), LogP (lipophilicity), topological polar surface area
  (TPSA)
- Hydrogen-bond donors / acceptors, rotatable bonds, aromatic rings, formal
  charge, heavy-atom count

**Typed contact features (protein-ligand geometry):**

| Feature | Definition |
|---------|------------|
| `n_hydrophobic` | carbon-carbon contacts within 4.5 Å |
| `n_hbond` | N/O to N/O contacts within 3.5 Å |
| `n_aromatic` | aromatic-C to aromatic-C contacts within 5.0 Å |
| `n_charged` | charged-atom contacts within 4.0 Å |
| `burial_fraction` | fraction of ligand atoms with a protein atom < 4 Å |
| `energy_proxy` | Σ 1/r⁶ over close contacts (0.5-6 Å) |

Features are combined into pKd by a **linear model**. The weights are not
sacred: they should be fit (least squares or a regularized regression) to a
benchmark such as PDBbind, or replaced entirely by a trained model like RF-Score
(random forest on the same style of contact descriptors). Treat any hard-coded
coefficient set as a rough starting heuristic, not a validated predictor.

Convert pKd to the other units with exact thermodynamics (T = 298.15 K):

- ΔG = −R·T·ln(10)·pKd  (R = 1.987×10⁻³ kcal·mol⁻¹·K⁻¹)
- Kd = 10^(−pKd) mol/L  → ×10⁹ for nM

### Accuracy

- Typical error: **1-2 log units of pKd** (10-100× in Kd).
- Correlation with experiment: Pearson r ≈ 0.5-0.6 on PDBbind-style benchmarks.
- **Best for:** drug-like molecules (MW 200-600, LogP -1 to 5).
- **Worst for:** peptides, macrocycles, metal chelators, covalent binders, very
  large molecules — all outside the domain the features were designed for.

This is a ranking heuristic, not a quantitative measurement. Round outputs to
avoid false precision (pKd to 1 decimal; Kd to ~1 significant figure).

### When to use

Quick ranking of docked poses, virtual-screening triage, or any case with no
MD budget and no experimental anchor.

---

## Method 2 — MM/GBSA Rescoring

### What it computes

Molecular-Mechanics / Generalized-Born Surface-Area binding free energy as an
end-point difference:

```
ΔG_bind ≈ ΔG_MMGBSA = G(complex) − G(protein) − G(ligand)
```

Each end-point energy sums:

- **Bonded** terms (bond, angle, dihedral) from a protein force field (e.g.
  Amber ff14SB / amber14).
- **van der Waals** (Lennard-Jones) and **electrostatics** (Coulomb).
- **Polar solvation** from an implicit Generalized-Born model (e.g. OBC2).
- **Nonpolar solvation** proportional to solvent-accessible surface area (SASA).

### Two code paths

**Full path (OpenMM present).** Amber14 protein force field + OBC2 GB implicit
solvent, optional energy minimization, computed for all three end-points. The
hard part is the **ligand** and **complex** end-points: the ligand needs valid
parameters (partial charges + LJ), typically via GAFF/OpenFF
(`openff-toolkit` / `openmmforcefields`), and the complex needs a combined
topology. A protein-only Generalized-Born energy is straightforward in OpenMM;
a rigorous ΔG_MMGBSA requires all three systems built consistently. Do not
report a partial/ligand-only shortcut as a full MM/GBSA result.

**Fallback path (RDKit only).** MMFF94 force-field energy for the ligand plus a
crude solvation proxy from TPSA/LogP. Very approximate — use only for coarse
filtering when OpenMM is unavailable.

### Accuracy

| Path | Typical error | Correlation | Best for |
|------|--------------|-------------|----------|
| Full OpenMM MM/GBSA | 2-3 kcal/mol | r ≈ 0.5-0.7 | relative ranking within a congeneric series |
| RDKit MMFF fallback | 5-10 kcal/mol | r ≈ 0.3-0.4 | very rough filtering only |

### Known limitations

1. **No entropy.** Configurational/conformational entropy loss on binding
   (3-10 kcal/mol) is omitted.
2. **Single snapshot.** One docked pose, no conformational sampling/averaging.
3. **Implicit solvent.** GB approximates explicit water and misses specific
   water-mediated bridges.
4. **Ligand parameterization.** The fallback path does not properly parameterize
   the ligand; even the full path depends on the quality of GAFF/OpenFF charges.

Consequently ΔG_MMGBSA ≠ experimental ΔG_binding. It is a *ranking* signal.

### When to use

Rescoring a set of poses for better relative ordering, especially a congeneric
series, and preferentially when OpenMM is available (the full path is materially
better than the fallback).

---

## Method 3 — Consensus Scoring

### What it computes

A single ranking that combines several scoring sources (docking score, empirical
pKd, MM/GBSA ΔG, interaction counts) to average out individual-method bias.

1. **Rank-normalize** each source: sort by its own score direction (higher- or
   lower-is-better), convert to ranks, map to [0, 1] (best → 1.0, worst → 0.0).
2. **Weighted combination** of normalized ranks (default: equal weights).
3. **Agreement** between sources via mean pairwise Kendall τ.

### Why rank-based?

Sources live on incompatible scales — Vina ≈ −12…−2 kcal/mol, empirical pKd
1-12, MM/GBSA can be hundreds of kcal/mol, interaction counts 0-50. Rank
normalization puts them all on [0, 1] so combination is meaningful regardless of
scale, and it is robust to outliers.

### Agreement interpretation

| Mean Kendall τ | Class | Meaning |
|----------------|-------|---------|
| > 0.7 | high | methods largely agree; ranking is trustworthy |
| 0.4-0.7 | moderate | partial agreement; top/bottom more reliable than middle |
| < 0.4 | low | methods disagree; treat the ranking as uncertain |

### Accuracy

Consensus generally beats any single method (rank-by-rank consensus has
outperformed individual functions and improved screening enrichment in the
literature). Caveat: combining several *poor* methods does not guarantee a good
result — garbage in, garbage out.

### When to use

Whenever ≥2 score sources exist. Especially valuable when methods disagree on a
few compounds (the disagreement itself flags uncertainty), and for screening
campaigns where controlling false positives matters.

---

## Method 4 — Batch Virtual Screening

Apply Method 1 (the fast empirical model) across a whole library: parse the
protein once, iterate the compound SDF, score each molecule, filter by a pKd
threshold and/or keep the top-N, and emit a ranked table (with SMILES, pKd,
Kd, ΔG, confidence). For very large libraries (>10k), filter early with a
`--threshold` to avoid writing low-value rows, then feed survivors into
consensus with docking scores. Screening output is a **prioritized shortlist for
assays**, not a set of affinity claims.

---

## Confidence / Applicability Domain

The empirical model should self-report confidence from where the molecule and
its contacts fall relative to the training-style domain:

| Level | Criteria | Action |
|-------|----------|--------|
| **high** | MW 200-600, LogP -1 to 5, > 30 contacts | use for ranking |
| **moderate** | partially in domain (one borderline flag) | use with caution; verify |
| **low** | outside domain (extreme MW/LogP, or < 10 contacts) | do not trust |

Flags that push toward low confidence: MW < 200 or > 600, LogP < −1 or > 5,
fewer than ~10 protein-ligand contacts.

---

## Method Selection Guide

| Scenario | Recommended approach |
|----------|---------------------|
| Quick virtual screen, no OpenMM | Method 1 empirical only (batch) |
| Careful study with OpenMM | empirical + MM/GBSA + consensus |
| Full pipeline with docking scores | consensus over all available sources |
| Congeneric-series ranking | MM/GBSA (full OpenMM path) |
| Diverse library screening | batch empirical → consensus with docking scores |

---

## Interpretation Tables

### pKd → Kd → reading

| pKd | Kd (approx) | Interpretation |
|-----|-------------|----------------|
| > 9 | < 1 nM | very potent (clinical-candidate range) |
| 7-9 | 1-100 nM | potent (lead range) |
| 5-7 | 100 nM - 10 µM | moderate (hit range) |
| 3-5 | 10 µM - 10 mM | weak (fragment range) |
| < 3 | > 10 mM | very weak / non-binder |

A predicted pKd carries ~1-2 log units of uncertainty: pKd 7.2 → true value
plausibly 5.7-8.7 (Kd ~2 nM to ~2 µM). Report the band, not just the point.

### MM/GBSA energies

- More negative = stronger predicted binding.
- Valid for relative ranking within a series, not absolute binding energies.
- ΔG_MMGBSA ≠ experimental ΔG_binding (missing entropy, single-snapshot).

---

## Core Caveats

1. **No method replaces experiment.** The gold standard is ITC, SPR, or
   biochemical assay. Everything here prioritizes what to measure.
2. **False precision is dangerous.** A pKd of 7.2 is not "7.2" — it is a range.
3. **Relative ranking beats absolute values.** These methods order a set far
   better than they pin any single compound's affinity.
4. **Domain matters.** Empirical features were designed for drug-like complexes;
   peptides, chelators, covalent, and macrocyclic ligands get unreliable scores.

---

## References

- Wang, R. et al. "The PDBbind database." *J. Med. Chem.* 47, 2977-2980 (2004).
- Ballester, P.J. & Mitchell, J.B.O. "A machine learning approach to predicting
  protein-ligand binding affinity." *Bioinformatics* 26, 1169-1175 (2010).
- Hou, T. et al. "Assessing the performance of the MM/PBSA and MM/GBSA methods."
  *J. Chem. Inf. Model.* 51, 69-82 (2011).
- Houston, D.R. & Walkinshaw, M.D. "Consensus docking: improving the reliability
  of docking in a virtual screening context." *J. Chem. Inf. Model.* 53,
  384-390 (2013).
- Wang, R. et al. "Further development and validation of empirical scoring
  functions." *J. Comput. Aided Mol. Des.* 16, 11-26 (2003).
- Li, H. et al. "Improving AutoDock Vina Using Random Forest." *J. Chem. Inf.
  Model.* 55, 1291-1299 (2015).
