# Interaction Analysis, Scoring, and Pose Ranking

A docking score alone is a weak filter — it carries scoring-function artifacts.
Combining it with the specific protein-ligand contacts a pose makes gives a far
more robust ranking and helps you reason about *why* a compound binds.

## Interaction fingerprinting with ProLIF

ProLIF detects and enumerates protein-ligand interactions from docked poses.

```python
import prolif as plf

# receptor must carry explicit hydrogens (see references/preparation.md)
protein = plf.Molecule.from_rdkit(rdkit_receptor_mol)   # or plf.Molecule.from_mda(universe)
poses = plf.sdf_supplier("poses.sdf")                    # iterable of pose molecules

fp = plf.Fingerprint()                                   # default interaction set
fp.run_from_iterable(poses, protein)
df = fp.to_dataframe()                                   # MultiIndex: (ligand, residue, interaction)
```

Notes:

- `plf.sdf_supplier` / `plf.pdbqt_supplier` iterate poses without loading a
  trajectory; `Fingerprint.run_from_iterable(poses, protein)` is the docking path
  (as opposed to `.run(traj, lig, prot)` for MD).
- Restrict or extend the interaction types via
  `plf.Fingerprint(["Hydrophobic", "HBDonor", "HBAcceptor", "PiStacking",
  "Anionic", "Cationic", "HalogenBond"])`.
- `df` gives per-residue, per-interaction booleans per pose. Convert to bit
  vectors (`fp.to_bitvectors()`) to compute Tanimoto similarity between poses or
  against a reference-ligand fingerprint.
- **Explicit hydrogens are mandatory** on both partners for H-bond and halogen
  detection — a receptor without H silently yields zero hydrogen bonds.

### Interaction types ProLIF reports

Hydrophobic, HBDonor/HBAcceptor (hydrogen bonds), PiStacking (π–π),
PiCation/CationPi, Anionic/Cationic (salt bridges), HalogenBond,
XBAcceptor/XBDonor, MetalDonor/MetalAcceptor, and van der Waals contacts.

## Geometric criteria (interpretation)

Approximate cutoffs these detectors use — useful for sanity-checking a pose:

| Interaction | Geometry | Role |
|---|---|---|
| Hydrogen bond | donor–acceptor < 3.5 Å, angle > 120° | Specificity, directionality |
| Hydrophobic contact | non-polar atoms within 4.5 Å | Desolvation / entropy |
| π-stacking | aromatic centroids < 5.5 Å; <30° (parallel) or >60° (T-shaped) | Aromatic recognition |
| Salt bridge | opposite charges within 4.0 Å | Strong electrostatics |
| Halogen bond | C–X···Y ~165°, distance < 3.5 Å | Directional, tunable |

## Reading docking scores

**Vina (kcal/mol)** — more negative is stronger predicted binding:

- Typical drug-like range: −6 to −12 kcal/mol.
- Below ~−7 kcal/mol is a common "promising hit" cutoff.
- These are **relative rankings**, not measured affinities; do not report a
  Vina score as a ΔG or convert it to a Kd. Use sibling `binding-affinity` for
  that.

**Vina pose RMSD** — `write_poses` reports lower/upper-bound RMSD of each pose
from the top pose; poses within ~2 Å of a known reference are considered
"correctly" placed in redocking validation.

**DiffDock confidence** — higher/positive is better (see
`references/docking-engines.md`); it is a learned pose-confidence, not an energy,
so rescore before comparing across compounds.

## Composite ranking

Rank by a blend of docking energy and interaction quality so a top compound must
be *both* energetically favorable *and* well-anchored:

1. **Normalize** the docking score across the set (e.g. min-max, using the best
   pose per compound). Remember Vina is better when lower.
2. **Score interactions** — count (and optionally weight) key contacts: hydrogen
   bonds and salt bridges to catalytic residues weigh more than a generic
   hydrophobic contact.
3. **Combine**: `composite = w_dock * norm_score + w_int * norm_interactions`
   with weights reflecting how much you trust each signal (start ~0.6 / 0.4).
4. **Rank and take the top N** for follow-up.

Why bother: docking scoring functions produce false positives (over-scored poses
that make no real contacts). Requiring meaningful interactions filters these out
and yields a shortlist a medicinal chemist can rationalize.

### Consensus and rescoring

- **Consensus docking**: keep compounds ranked highly by two engines/scoring
  functions (e.g. Vina + Vinardo, or DiffDock pose + Vina rescore). Reduces
  method-specific bias.
- **Rescore external poses**: run ProLIF and Vina `score()`/`optimize()` on poses
  from another tool, then apply the same composite ranking.

## Validating a virtual screen

If you have known actives, seed them into the library and measure **enrichment**
(fraction of actives recovered in the top X%) — e.g. EF at 1% or a ROC/BEDROC
metric. Good early enrichment matters more than perfect global ranking. A screen
that cannot recover known binders should not be trusted on novel compounds.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Zero hydrogen bonds everywhere | Missing explicit H on receptor/ligand | Add hydrogens before analysis |
| ProLIF import/geometry errors | RDKit/MDAnalysis version mismatch | Match ProLIF's pinned deps; reinstall in a clean env |
| Great score, implausible pose | Scoring-function artifact | Weight interactions higher; inspect in a viewer |
| Ranking unstable run-to-run | Vina stochasticity / low exhaustiveness | Raise exhaustiveness, average replicates |
| All compounds look identical | Box too large / off-site | Tighten box on the true pocket |
