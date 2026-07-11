# DiffDock Confidence Scores, Scope, and Limitations

## What the confidence score is

DiffDock attaches one confidence value to each predicted pose, produced by a
separate confidence model. It measures the model's certainty that the pose is
close to the true bound structure (roughly, likelihood of ligand RMSD < 2 Å from
the crystal pose). It is **not** binding affinity, not a docking energy, and not
a probability of activity.

| Score range | Level | Reading |
|-------------|-------|---------|
| `> 0` | High | Strong prediction; the top pose is likely near-native. |
| `-1.5` to `0` | Moderate | Reasonable; inspect visually and validate. |
| `< -1.5` | Low | Uncertain; treat as a hypothesis, not an answer. |

### Reading confidence correctly

- **Confidence ≠ affinity.** A high-confidence pose can be a weak binder; a
  low-confidence pose is not necessarily a non-binder. To rank *strength* of
  binding, rescore poses (see `binding-affinity`).
- **Calibrate to the system.** Expect *lower* confidence for large ligands
  (>500 Da), many-chain complexes, apo/unbound conformations that need to
  rearrange, and novel protein families under-represented in training. Expect
  *higher* confidence for drug-like small molecules (150–500 Da), single-chain
  proteins, and targets similar to the training data.
- **Use consensus.** Review the top 3–5 poses. Tight clustering of high-confidence
  poses in one site is a much stronger signal than a single lucky rank-1.

## What DiffDock does and does not output

Predicts: 3D binding poses, per-pose confidence, and multiple alternative binding
modes. Blind docking — it searches the whole surface and does not require a
pre-specified pocket.

Does NOT predict: binding affinity (ΔG, Kd, Ki), binding kinetics (on/off rates,
residence time), ADMET properties, or target selectivity.

## Scope

**Designed for:** small-molecule organic ligands (~100–1000 Da), drug-like
compounds, short peptides (<~20 residues), short oligonucleotides, single- or
multi-chain protein targets.

**NOT designed for — use the noted alternative:**

| Out of scope | Use instead |
|--------------|-------------|
| Protein–protein docking | DiffDock-PP, AlphaFold-Multimer, RoseTTAFold2NA |
| Large peptide/protein ligands (>~20 residues) | Dedicated peptide/complex docking |
| Covalent (irreversible) docking | Specialized covalent-docking tools |
| Metal-coordination specifics | Methods with explicit metal handling |
| Membrane-embedded targets | Not trained for this; use with caution |
| Binding-affinity ranking | Rescore poses (`binding-affinity`, GNINA, MM/GBSA, FEP) |

### Training-data caveats

DiffDock-L was trained largely on PDBBind and BindingMOAD complexes. It performs
best on chemistry and folds resembling that distribution and can underperform on
novel protein families, unusual chemotypes, and allosteric sites poorly covered
in training.

## Validation workflow

1. **Generate poses** with DiffDock; rank by confidence.
2. **Inspect visually** in a molecular viewer — check for plausible hydrogen
   bonds, hydrophobic contacts, steric complementarity, and no severe clashes.
3. **Rescore for affinity** with one or more of: GNINA (fast NN scoring),
   MM/GBSA or MM/PBSA (MMPBSA.py, gmx_MMPBSA), or alchemical free-energy methods
   (FEP/TI via OpenMM+OpenFE or GROMACS) for the most accurate ranking.
4. **Validate experimentally** — biochemical assays (IC50/Kd), X-ray/cryo-EM.

## Troubleshooting prediction quality

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Uniformly low confidence | Large/flexible ligand, ambiguous pocket, apo conformation | Raise `--samples_per_complex` to 20–40; try ensemble docking; validate the input structure |
| Unrealistic poses / clashes | Poor protein prep, ligand too large, wrong site | Fill missing residues, drop distant waters, set protonation at physiological pH; more samples |
| Poses on the surface | True pocket blocked or occluded | Check for a bound cofactor/ion; consider isolating the relevant chains |
| Multiple scattered sites | Genuine multi-site or model uncertainty | Increase samples; cluster poses and inspect each cluster |

## Citation

- Corso et al. (2023) "DiffDock: Diffusion Steps, Twists, and Turns for Molecular
  Docking," ICLR 2023, arXiv:2210.01776.
- Stärk et al. (2024) "DiffDock-L: Improving Molecular Docking with Diffusion
  Models" (improved generalization; current default), arXiv:2402.18396.
- Evaluated with the PoseBusters benchmark for physical validity of poses.
</content>
