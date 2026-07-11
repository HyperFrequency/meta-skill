# Glycan Structure & Database Resources

The sequence-level predictors in this skill locate **candidate sites on the
protein**. They say nothing about the **glycan** attached (its monosaccharide
composition, branching, or 3D shape) and give no learned occupancy probability.
When the question moves past "where are the sites" to "how likely, and what
sugar," hand off to the tools below.

## Occupancy-probability predictors (better than the motif heuristic)

These take a FASTA sequence and return per-residue probabilities, using sequence
context the rule-based scans ignore. Prefer them for any quantitative claim.

| Tool | Predicts | Home |
| --- | --- | --- |
| **NetNGlyc** | N-glycosylation probability per Asn (context-aware neural net) | DTU Health Tech services (`services.healthtech.dtu.dk`) |
| **NetOGlyc 4.0** | Mucin-type O-GalNAc probability per Ser/Thr (trained on glycoproteomics) | DTU Health Tech services |

Use these to rank the candidates this skill enumerates. A sequon that NetNGlyc
scores low is a plausible non-occupied site; one it scores high is worth an assay.

## Glycan structure, 3D modeling, and MS

| Tool | Use | Input → Output |
| --- | --- | --- |
| **GLYCAM-Web** (`glycam.org`) | Build glycan 3D structures and AMBER/MD parameters | IUPAC glycan sequence → PDB coords + force-field params |
| **GlycoWorkbench** | Draw glycan structures and annotate MS fragment spectra | MS peak list → glycan structure assignments |
| **GlycoSHIELD** | Model the conformational "shield" a glycan casts over a protein surface for MD | Protein PDB + site list → ensemble of glycan conformers |

GlycoSHIELD and GlycoWorkbench are actively maintained but have moved hosting over
time — search for the current repository/release rather than hardcoding a URL, as
the download locations change.

## Glycoproteomics & annotation databases

| Resource | Contains |
| --- | --- |
| **UniProt** `CARBOHYD` features | Experimentally supported / predicted glyco sites per protein; the primary validation source. Pull programmatically via the `bioservices` sibling skill. |
| **GlyConnect** (ExPASy) | Curated site-specific glycoprotein structures and glycoforms |
| **GlyGen** | Integrated glycan + glycoprotein data across databases (glycosylation sites, glycan structures, enzymes) |
| **Essentials of Glycobiology** (NCBI Bookshelf, NBK310274) | Authoritative open textbook for the underlying biology |

## Choosing the right tool

- "Is this predicted site real?" → NetNGlyc / NetOGlyc probability, then UniProt.
- "Which glycan is on it?" → GlyConnect / GlyGen (data), GlycoWorkbench (MS).
- "How does the glycan affect the protein surface / dynamics?" → GLYCAM-Web +
  GlycoSHIELD with a structure.
- "Is the site solvent-exposed at all?" → a structure (AlphaFold DB, PDB) — glycan
  attachment requires surface accessibility that sequence cannot report.
- "Where are the candidate sites to begin with?" → this skill.
