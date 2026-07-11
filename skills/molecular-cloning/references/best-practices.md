# Best Practices, Cross-Cutting Checks & Resources

Design-rule summary that spans capabilities, plus the primary literature and
docs. Per-capability failure modes live in the other three reference files.

## Design checklist

- **Primer design** — keep forward/reverse Tm within ~2 °C of each other; 40–60%
  GC; avoid 3' self- and cross-complementarity (primer-dimers); keep the
  annealing portion 18–25 nt. Tails (restriction sites, overhangs, Gibson
  homology) do not count toward the early-cycle Tm.
- **Restriction digest** — verify compatible cohesive ends before planning a
  ligation; check dam/dcm methylation sensitivity for the host DNA; always set
  the correct `linear` flag; prefer single-cutters for linearization.
- **Golden Gate** — 4 bp overhangs must be unique *and* non-palindromic; domesticate
  parts (remove internal Type IIS sites); pick overhangs from a published
  high-fidelity set for large (>4-part) assemblies; confirm the enzyme (BsaI vs
  BsmBI/Esp3I vs BbsI) and its cut offset.
- **Gibson / HiFi** — 20–40 bp overlaps with matched junction Tm; unique junction
  sequences (no internal repeats); ≥2 fragments.
- **CRISPR guides** — no `TTTT` (Pol III terminator); prefer early constitutive
  exons for knockouts; treat the built-in score as a filter and validate
  survivors with a genome-aware off-target tool and an on-target activity model.
- **Plasmid annotation** — confirm ORF reading frame and look for an upstream
  promoter/RBS before trusting a called CDS; map all unique restriction sites so
  you know your future cloning handles; watch for features that cross the origin.

## Coordinate conventions (recurring source of bugs)

- `Bio.Restriction` `.search()` / `Analysis` → **1-based** cut positions.
- `Bio.Seq` slicing and the PCR/CRISPR position fields here → **0-based**.
- None of the linear scans wrap a circular origin; rotate or duplicate the
  sequence when a feature/amplicon/ORF straddles position 0.

## Primary references

- Biopython `Bio.Restriction` — https://biopython.org/wiki/Restriction
- Biopython `Bio.SeqUtils.MeltingTemp` — Tm models (`Tm_NN`, salt corrections)
- primer3-py docs — https://libnano.github.io/primer3-py/
- Engler et al. 2008, *PLoS ONE* — Golden Gate one-pot cloning
  (doi:10.1371/journal.pone.0003647)
- Potapov et al. 2018, *ACS Synth. Biol.* — Type IIS overhang ligation fidelity
  (high-fidelity overhang sets)
- Gibson et al. 2009, *Nat. Methods* — isothermal one-step DNA assembly
  (doi:10.1038/nmeth.1318)
- Doench et al. 2016, *Nat. Biotechnol.* — Rule Set 2 on-target sgRNA scoring
  (doi:10.1038/nbt.3437)
- Bae et al. 2014, *Bioinformatics* — Cas-OFFinder genome-wide off-target search
