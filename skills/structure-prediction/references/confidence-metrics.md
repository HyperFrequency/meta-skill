# Confidence Metrics for Structure Prediction

Deep reference for interpreting ESMFold confidence and deciding when to escalate to
AlphaFold2. Linked from `SKILL.md`.

## pLDDT (predicted Local Distance Difference Test)

pLDDT is the primary per-residue confidence output by ESMFold (and AlphaFold2). It estimates
how accurately each residue is placed relative to the true structure, on a 0-100 scale, and
is written into the B-factor column of the PDB.

### Tier-by-tier

**Very high — pLDDT > 90.** Backbone and side-chain positions are expected within ~1-2 Å of
truth. Typical of well-packed core residues and stable secondary structure. Reliable for
atomic-level work: docking, binding-site characterization, mutagenesis design.

**Confident — pLDDT 70-90.** Backbone topology is reliable; side-chain rotamers may deviate.
Typical of surface residues in stable elements and well-defined loops. Good for fold-level
comparison and general structural analysis; treat side chains with some caution.

**Low — pLDDT 50-70.** Overall topology may be roughly right, but local detail is uncertain.
Typical of flexible loops, exposed turns, and segments with few contacts. Use only the
general shape; this can reflect genuine flexibility rather than error.

**Very low — pLDDT < 50.** Do not trust the coordinates for any quantitative analysis.
Typical of intrinsically disordered regions, long linkers, and terminal tails. The useful
signal here is the *identification* of disorder, not the atomic positions.

| pLDDT | Confidence | Backbone | Side chains | Use cases |
|-------|-----------|----------|-------------|-----------|
| > 90  | Very high | Accurate | Likely accurate | Docking, binding-site analysis, mutagenesis design |
| 70-90 | Confident | Reliable | Approximate | Fold comparison, domain analysis, general structural biology |
| 50-70 | Low       | Approximate | Unreliable | Topology assessment only; loop-modelling candidate |
| < 50  | Very low  | Unreliable | Unreliable | Disorder prediction; do not use for structural analysis |

## When to trust a prediction

**Higher trust:**
- Members of well-studied families with many known structures — the language model has seen
  the patterns.
- Compact globular domains with pLDDT > 70.
- Evolutionarily constrained motifs (catalytic sites, DNA-binding domains).
- Short-to-medium chains (< 400 residues).

**Lower trust:**
- Intrinsically disordered proteins/regions — low pLDDT is *correct*, not a failure.
- Membrane proteins — transmembrane spans lack their lipid context.
- Multi-domain proteins with flexible linkers — individual domains may be good, but their
  relative orientation is often wrong (and ESMFold gives no PAE to check it).
- Novel folds with no detectable homologs — the hardest case for a single-sequence model.
- Very long chains (> 800 residues) — memory limits and degraded quality.
- Metal-/cofactor-dependent folds that need the ligand to fold correctly.

## ESMFold vs. AlphaFold2 metrics

**pLDDT.** Both use it with the same ranges and interpretation. AlphaFold2's pLDDT tends to
be better calibrated because MSA gives evolutionary constraints; ESMFold's single-sequence
pLDDT is generally well-behaved but can be over- or under-confident on some regions.

**PAE (Predicted Aligned Error).** AlphaFold2's pairwise error estimate for every residue
pair — essential for judging domain-domain orientation and complex predictions. **ESMFold
does not emit PAE** in its standard pipeline. If you need inter-domain/inter-chain
confidence, use AlphaFold2.

**pTM (predicted TM-score).** A single global-quality estimate. ESMFold computes it
internally but it is not always exposed in the default output. When available: pTM > 0.5
suggests the fold is likely correct; pTM > 0.8 suggests high overall quality.

### Method-selection cheat sheet

| Criterion              | ESMFold                     | AlphaFold2                   |
|------------------------|-----------------------------|------------------------------|
| Speed                  | Seconds (single GPU)        | Minutes-hours (with MSA)     |
| MSA required           | No                          | Yes                          |
| Hardware               | Single GPU (≥16 GB)         | Multiple GPUs recommended    |
| Best for               | Rapid screening, triage     | Maximum accuracy, hard targets |
| Accuracy — easy targets| Comparable                  | Slightly better              |
| Accuracy — hard targets| Lower                       | Significantly better         |
| Multi-chain            | No                          | Yes (AlphaFold-Multimer)     |
| PAE output             | No                          | Yes                          |

### Recommended escalation workflow

1. **Screen** every target with ESMFold — seconds each, a first look at viability.
2. **Triage by pLDDT** — mean pLDDT > 70 is usually good enough; those may not need
   AlphaFold2.
3. **Refine** critical targets or anything with mean pLDDT < 70 using AlphaFold2 + full MSA.
4. **Cross-validate** — if ESMFold and AlphaFold2 agree (TM-score > 0.8), confidence is high
   regardless of which produced the model.
