---
name: matchms
version: 0.1.0
description: >-
  Spectral similarity scoring and small-molecule identification for untargeted
  metabolomics with the matchms Python library. Use to import MS/MS spectra
  (mzML, mzXML, MGF, MSP, GNPS JSON, USI), harmonize metadata and clean peaks
  with matchms filters, compute pairwise similarity (CosineGreedy,
  CosineHungarian, ModifiedCosine, NeutralLossesCosine, FingerprintSimilarity,
  precursor/parent-mass match), match unknown spectra against reference
  libraries, and build spectral/molecular networks. Best for metabolite
  annotation, library search, spectral-network construction, and reproducible
  preprocessing pipelines. Not for raw-file peak-picking or feature detection
  (use MZmine or OpenMS/`pyopenms`), full LC-MS/MS proteomics identification
  (`pyopenms`), deep-learning spectral embeddings (MS2DeepScore / Spec2Vec), or
  cheminformatics on molecular structures alone (`rdkit`, `datamol`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (matchms); chemistry extras require RDKit (BSD-3-Clause)"
---

# Matchms

## Overview

`matchms` is an open-source Python library for processing tandem mass
spectrometry (MS/MS) data and scoring spectral similarity. It gives you a
compact pipeline: **import → filter/harmonize → score → match**. The end goal is
usually to annotate an unknown fragmentation spectrum by matching it against a
reference library, or to cluster many spectra into a molecular network.

Everything centers on the `Spectrum` object (peak `mz` + `intensities` arrays
plus a metadata dictionary). Filters transform one `Spectrum` at a time and
return either a cleaned copy or `None` when the spectrum fails a requirement.
Similarity functions consume two `Spectrum` objects; `calculate_scores` applies
one across every reference/query pair and returns a `Scores` object.

matchms is licensed Apache-2.0. Structure-based features (SMILES/InChI
derivation, fingerprints) require the optional RDKit dependency.

## When to Use This Skill

Reach for matchms when the task involves:

- **Metabolite annotation / library search** — matching unknown MS/MS spectra
  against GNPS, MoNA, MassBank, NIST, or in-house `.msp`/`.mgf` libraries.
- **Spectral similarity** — cosine, modified cosine (mass-shift tolerant),
  neutral-loss, or molecular-fingerprint scores between spectra.
- **Spectral networking** — all-vs-all similarity to build a molecular network
  (feed the score matrix into `networkx`).
- **Reproducible preprocessing** — harmonizing messy metadata (adducts, charge,
  precursor m/z, compound names) and cleaning peaks before analysis.
- **Format conversion** — reading mzML/mzXML/MGF/MSP/JSON and writing a
  standardized, filtered library back out.

## When NOT to Use This Skill

- **Raw-file peak-picking / feature detection / alignment** — matchms consumes
  already-centroided spectra; do detection in MZmine, OpenMS/`pyopenms`, or a
  vendor tool first.
- **Full LC-MS/MS proteomics identification** (database search, FDR, protein
  inference) — use `pyopenms`.
- **Learned spectral embeddings** — for deep-learning similarity use
  MS2DeepScore or Spec2Vec (sibling libraries from the same authors), not the
  peak-based scores here.
- **Cheminformatics on structures alone** (no spectra) — use `rdkit`, `datamol`,
  or `molfeat` for fingerprints, descriptors, and structure similarity.
- **Retrieval over molecule/paper corpora** — use `molecular-rag`.

## Installation

```bash
uv pip install matchms            # core: import, filter peaks, similarity
uv pip install "matchms[chemistry]"  # + RDKit for SMILES/InChI/fingerprints
```

## Core Pattern

A minimal end-to-end library search — process references and queries the **same
way**, then score and rank:

```python
from matchms.importing import load_from_mgf
from matchms.filtering import default_filters, normalize_intensities, \
    select_by_relative_intensity, require_minimum_number_of_peaks
from matchms import calculate_scores
from matchms.similarity import CosineGreedy

def clean(spectrum):
    spectrum = default_filters(spectrum)                 # harmonize metadata
    spectrum = normalize_intensities(spectrum)           # scale peaks to max=1
    spectrum = select_by_relative_intensity(spectrum, intensity_from=0.01)
    return require_minimum_number_of_peaks(spectrum, n_required=5)  # -> None if too few

references = [s for s in map(clean, load_from_mgf("library.mgf")) if s is not None]
queries    = [s for s in map(clean, load_from_mgf("unknowns.mgf")) if s is not None]

scores = calculate_scores(references, queries, CosineGreedy(tolerance=0.1))

# Rank references for one query. Sort by the "<Function>_score" column.
best = scores.scores_by_query(queries[0], name="CosineGreedy_score", sort=True)
for reference, (score, n_matches) in best[:5]:
    print(reference.get("compound_name"), round(float(score), 4), int(n_matches))
```

Two rules that prevent most mistakes: **apply identical filtering to references
and queries**, and **check for `None`** after any `require_*` / filter that can
reject a spectrum.

## Capabilities

Each area has a dedicated reference. Load the one you need.

### Importing & exporting

Read spectra from mzML, mzXML, MGF, MSP, GNPS JSON, USI, or pickle; write MGF,
MSP, JSON, or pickle. Import functions return **generators** (memory-efficient
for large files) and harmonize metadata keys by default. See
[references/importing-exporting.md](references/importing-exporting.md).

### Filtering & metadata harmonization

40+ filters in three families: metadata processing (adducts, charge, precursor
m/z, compound names, ionmode, chemical structures), peak processing (normalize,
select by m/z / intensity, remove precursor peaks, reduce peak count), and
quality gates (`require_*`, which return `None` on failure). `default_filters`
runs the standard metadata-harmonization bundle. See
[references/filtering.md](references/filtering.md).

### Similarity scoring

Peak-based (`CosineGreedy`, `CosineHungarian`, `ModifiedCosine`,
`NeutralLossesCosine`), structure-based (`FingerprintSimilarity`), and metadata
gates (`PrecursorMzMatch`, `ParentMassMatch`, `MetadataMatch`). Choosing the
right metric and reading the `Scores` object (including the structured-array
gotcha) is covered in [references/similarity.md](references/similarity.md).

### Workflows

End-to-end recipes: library matching, QC/cleaning, precursor-filtered search,
all-vs-all networking with `is_symmetric=True`, multi-metric consensus scoring,
ion-mode splitting, metadata enrichment, and identification reports. See
[references/workflows.md](references/workflows.md).

## Building Reproducible Pipelines

The safest, version-stable approach is a plain function that applies filters in
order and drops rejected spectra (the `clean()` function above). Order matters —
e.g. `normalize_intensities` before `select_by_relative_intensity`.

matchms also ships pipeline objects for convenience:

- **`SpectrumProcessor`** builds a reusable filter chain and can emit a
  processing report (how many spectra each filter removed). Construct it with a
  predefined pipeline or an empty one, add filters, then process a batch:

  ```python
  from matchms import SpectrumProcessor
  processor = SpectrumProcessor(predefined_pipeline="default")
  processor.add_matchms_filter(("normalize_intensities", {}))
  processor.add_matchms_filter(("select_by_relative_intensity", {"intensity_from": 0.01}))
  processed, report = processor.process_spectrums(spectra, create_report=True)
  ```

- **`matchms.Pipeline`** wraps import → filter → score → export as a single
  configurable run (often from a workflow config), for repeatable end-to-end
  jobs.

The exact constructor keywords, predefined-pipeline names, and method
signatures of these two classes have changed across matchms releases. Confirm
against the API of your installed version before relying on them; the plain
functional loop always works. Reference:
`https://matchms.readthedocs.io/en/latest/`.

## Common Pitfalls & Failure Modes

- **Filters return `None`.** Any `require_*` (and some repair filters) reject a
  spectrum by returning `None`. Guard before the next step or you get
  `AttributeError: 'NoneType'`.
- **Asymmetric processing.** Different filtering on references vs queries
  silently distorts scores. Use one shared function.
- **Reading `Scores` wrong.** `scores.scores_by_query(query, name="<Fn>_score",
  sort=True)` yields `(reference, (score, n_matches))` pairs — the score is a
  structured value, not a bare float. For the full matrix use
  `scores.to_array()["<Fn>_score"]`. Details in
  [references/similarity.md](references/similarity.md).
- **Missing precursor m/z.** `ModifiedCosine`, `NeutralLossesCosine`, and
  `PrecursorMzMatch` need valid `precursor_mz`; run `add_precursor_mz` /
  `default_filters` first and drop spectra that still lack it.
- **Structure features without RDKit.** `derive_inchi_from_smiles`,
  `add_fingerprint`, and `FingerprintSimilarity` require the `[chemistry]`
  extra.
- **All-vs-all cost.** A self-comparison of N spectra is N² pairs. Pass
  `is_symmetric=True` to `calculate_scores`, and pre-filter with
  `PrecursorMzMatch` before an expensive metric on large libraries.

## References

- [references/importing-exporting.md](references/importing-exporting.md) — file
  formats, load/save signatures, streaming large files.
- [references/filtering.md](references/filtering.md) — full filter catalogue and
  standard filter combinations.
- [references/similarity.md](references/similarity.md) — every similarity
  function, parameters, when to use each, and reading `Scores`.
- [references/workflows.md](references/workflows.md) — eight complete analysis
  recipes.
