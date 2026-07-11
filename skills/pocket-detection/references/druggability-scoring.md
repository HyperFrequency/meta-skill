# Druggability Scoring

A transparent, reproducible 6-axis model that turns raw pocket geometry into a
single 0-1 druggability score and a class. It is a **heuristic for
prioritization**, not a validated predictor — see the caveats at the end.

## The six axes

Each axis maps one geometric/chemical property of a pocket to a 0-1 sub-score
with a smooth curve (no flat plateaus, so similar pockets still separate), then a
fixed-weight sum produces the composite.

| Axis            | Weight | Curve                                  | Rationale                                           |
| --------------- | ------ | -------------------------------------- | --------------------------------------------------- |
| volume          | 0.25   | Gaussian, peak ≈ 500 Å³, σ ≈ 250       | drug-like pockets cluster near ~300-800 Å³          |
| enclosure       | 0.25   | logistic centered at 0.5               | buried, wall-surrounded cavities beat open grooves  |
| hydrophobicity  | 0.20   | Gaussian, peak ≈ 0.5, σ ≈ 0.15         | some desolvation drive, but not a greasy slab       |
| depth           | 0.15   | logistic rising through ~5-10 Å (mid 6 Å) | deeper pockets bury more ligand surface           |
| H-bond capacity | 0.10   | Gaussian, peak ≈ 4-5 polar contacts    | anchors specificity; too many = desolvation penalty |
| aromaticity     | 0.05   | Gaussian, peak ≈ 3-4 aromatics         | π-stacking partners help, in moderation             |

Each sub-score is floored at a small value (~0.05) so one bad axis cannot zero
out an otherwise reasonable pocket.

**Composite** = Σ (weight × sub-score). The weights sum to 1.0, so the composite
is itself in [0, 1].

## Classes

| Class        | Composite | Reading                                                         |
| ------------ | --------- | -------------------------------------------------------------- |
| druggable    | > 0.7     | well-suited to a small-molecule inhibitor                      |
| difficult    | 0.4-0.7   | consider fragment-based or otherwise specialized approaches     |
| undruggable  | < 0.4     | unlikely to bind drug-like molecules; think PPI inhibitors/peptides |

## Volume vs molecule class

Volume alone is a fast triage before the full score:

| Volume        | Interpretation                                                    |
| ------------- | ----------------------------------------------------------------- |
| < 150 Å³      | too small for drug-like molecules; may bind fragments or ions     |
| 150-300 Å³    | fragment-sized; suitable for fragment-based design                |
| 300-800 Å³    | ideal drug-like pocket; most approved oral drugs bind here        |
| 800-1500 Å³   | large; may need extended molecules, macrocycles, or PROTACs       |
| > 1500 Å³     | very large or flat; often a protein-protein surface, not a pocket |

## Caveats — read before you quote a score

- **Heuristic, not a model.** Thresholds derive from the literature
  (Halgren 2009; Volkamer 2012), not from a fit to a held-out benchmark. Use the
  score to rank pockets against each other, never as a standalone go/no-go.
- **Geometry in, geometry out.** The score reflects shape and coarse chemistry of
  a single static conformation. Cryptic pockets, induced fit, and metal/cofactor
  chemistry are outside its scope.
- **Preparation matters.** Hydrogens, protonation states, and retained
  heteroatoms shift enclosure/hydrophobicity/H-bond counts. Score every structure
  the same way before comparing.
- **Ties are informative.** If several pockets score within ~0.05, the protein
  genuinely has multiple comparable sites — do not force a single winner; carry
  the top few into docking and let poses decide.

## References

- Halgren, T.A. Identifying and characterizing binding sites and assessing
  druggability. *J. Chem. Inf. Model.* 49, 377-389 (2009).
- Volkamer, A. et al. DoGSiteScorer: a web server for automatic binding site
  prediction, analysis and druggability assessment. *Bioinformatics* 28,
  2074-2075 (2012).
