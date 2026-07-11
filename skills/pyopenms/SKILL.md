---
name: pyopenms
version: 0.1.0
description: >-
  pyOpenMS gives Python bindings to the OpenMS C++ framework for computational
  mass spectrometry. Use it to read/write MS formats (mzML, mzXML, featureXML,
  consensusXML, idXML, mzIdentML, pepXML, mzTab, FASTA, TraML), process raw
  spectra (smoothing, centroiding/peak picking, normalization, baseline
  removal), detect and link LC-MS features across samples, post-process
  proteomics identifications (FDR control, protein inference, ID mapping,
  in-silico digestion, theoretical spectra), and build untargeted metabolomics
  pipelines (mass-trace feature finding, adduct grouping, RT alignment,
  consensus quantification, QC filtering). Reach for it for full LC-MS/MS and
  metabolomics workflows on real instrument data. NOT for simple spectral
  matching or small-molecule library ID (a lighter tool like matchms fits
  better), NOT for molecule structure handling or descriptors (use `rdkit`),
  and NOT for running the database search itself — pyOpenMS wraps and
  post-processes search engines, it is not a de-novo search engine.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (OpenMS/pyOpenMS)"
---

# pyOpenMS

## Overview

pyOpenMS wraps the OpenMS C++ library, exposing its mass-spectrometry data
structures and algorithms to Python. It is the tool for handling raw LC-MS/MS
data end to end: parse vendor-neutral formats, clean and centroid spectra,
detect chromatographic features, quantify them across samples, and post-process
peptide/protein or metabolite identifications. Objects are thin Python handles
over C++ classes, so the API is verbose and stateful — you construct an
algorithm, tune its `Param` object, and run it in place.

This SKILL.md is a router. Each capability below links to a reference file with
concrete APIs, parameters, and full workflows. Read the relevant reference
before writing code — the exact method signatures matter.

## When to Use This Skill

- Reading, writing, or converting MS files: mzML, mzXML, featureXML,
  consensusXML, idXML, mzIdentML, pepXML, mzTab, FASTA, TraML.
- Preprocessing raw spectra: Gaussian/Savitzky-Golay smoothing, peak
  picking/centroiding, normalization, baseline reduction, intensity filtering.
- Untargeted metabolomics: mass-trace feature finding, adduct grouping, RT
  alignment, cross-sample consensus, QC/CV/blank filtering, quant tables.
- Label-free proteomics quantification: feature detection + linking into a
  consensus map, then ID mapping.
- Post-processing identifications from a search engine: FDR/q-value filtering,
  protein inference, in-silico digestion, theoretical fragment spectra.
- Working with peptide sequences and molecular formulas: `AASequence`,
  `EmpiricalFormula`, modifications, monoisotopic/average masses.

## When NOT to Use This Skill

- Simple spectral similarity or small-molecule library matching — a focused
  library such as matchms is lighter and less ceremony.
- Molecular structure parsing, descriptors, fingerprints, or 2D/3D depiction of
  identified compounds — use `rdkit` (or `datamol` for high-level pipelines).
- Running the actual database search (Comet, MSGF+, X!Tandem, MSFragger).
  pyOpenMS provides *adapters* that shell out to an externally installed engine
  and consumes their output; it does not implement the search itself.
- Downstream statistics, ML, or plotting on the exported quant table — hand the
  DataFrame to `statistical-analysis`, `scikit-learn`, `matplotlib`, or
  `seaborn`.

## Installation

```bash
uv pip install pyopenms      # or: pip install pyopenms
```

```python
import pyopenms as ms
print(ms.__version__)
```

Wheels ship prebuilt binaries for common platforms; no OpenMS system install is
needed for the Python API. Search-engine *adapters* additionally require the
external engine binary on `PATH`.

## Core Mental Model

Two things recur across every workflow:

1. **Data containers hold everything.** `MSExperiment` (spectra +
   chromatograms), `MSSpectrum`/`MSChromatogram`, `FeatureMap` (per-run
   features), `ConsensusMap` (features linked across runs), and the
   identification objects (`PeptideIdentification`, `ProteinIdentification`).
   Most containers expose `.get_df()` to hand data to pandas.
2. **Algorithms are stateful objects tuned via `Param`.** The pattern is always:
   construct the algorithm, `params = algo.getParameters()`, mutate with
   `params.setValue("nested:key", value)`, `algo.setParameters(params)`, then
   run — usually mutating an output object passed by reference.

```python
algo = ms.GaussFilter()
params = algo.getParameters()
params.setValue("gaussian_width", 0.2)
algo.setParameters(params)
algo.filterExperiment(exp)   # modifies exp in place
```

See `references/data-structures.md` for every container and its accessors.

## Capabilities

### File I/O and Formats

Load/store all supported formats, choose in-memory vs. on-disc access for large
files, read/write identification and feature files, convert between formats, and
inspect instrument/sample metadata. See `references/file-io.md`.

### Signal Processing

Smoothing (Gaussian, Savitzky-Golay), peak picking / centroiding
(`PeakPickerHiRes`), normalization, intensity filtering (threshold/window/N
largest), baseline reduction, spectrum merging, RT alignment, and full
preprocessing pipelines. See `references/signal-processing.md`.

### Feature Detection and Linking

Detect chromatographic features (legacy `FeatureFinder` for centroided
proteomics data; the `MassTraceDetection` → `ElutionPeakDetection` →
`FeatureFindingMetabo` pipeline for metabolomics), align retention times, and
link features across samples into a `ConsensusMap`. See
`references/feature-detection.md`.

### Peptide and Protein Identification

Read search-engine output, control FDR / compute q-values, run protein
inference, map IDs onto features, digest proteins in silico, and generate
theoretical fragment spectra. See `references/identification.md`.

### Metabolomics Pipelines

End-to-end untargeted workflow: feature finding tuned for small molecules,
adduct decharging, RT alignment, consensus linking, TIC normalization, QC/CV and
blank filtering, and export of an analysis-ready quant table. See
`references/metabolomics.md`.

## Common Pitfalls

- **In-place mutation.** Filters and pickers modify their argument (or write to a
  passed-by-reference output). Copy first (`ms.MSExperiment(exp)`) to keep the
  original.
- **Profile vs. centroid data.** Feature finders expect centroided input. Run
  `PeakPickerHiRes` first if spectra are profile-mode; feeding profile data to a
  feature finder yields garbage.
- **Byte strings.** Many string-returning accessors (accessions, file paths)
  return `bytes` — call `.decode()` before comparing to Python `str`.
- **Score direction differs by engine.** Always check
  `peptide_id.isHigherScoreBetter()` before thresholding; some engines report
  E-values (lower is better), others report scores (higher is better).
- **Large files.** Do not load multi-GB mzML fully into memory; use on-disc /
  indexed access (see `references/file-io.md`).
- **Adapters need the external binary.** Search-engine adapters fail unless the
  engine is installed and on `PATH`.

## References

- `references/data-structures.md` — core containers, features, identifications, sequences, `Param`.
- `references/file-io.md` — formats, in-memory/on-disc access, reading/writing IDs and features, conversion, metadata.
- `references/signal-processing.md` — smoothing, peak picking, normalization, filtering, baseline, alignment, pipelines.
- `references/feature-detection.md` — feature finding, RT alignment, linking, adducts, filtering, annotation.
- `references/identification.md` — search-engine output, FDR, protein inference, digestion, theoretical spectra.
- `references/metabolomics.md` — untargeted pipeline, adduct grouping, normalization, QC filtering, export.

External: pyOpenMS docs (pyopenms.readthedocs.io), OpenMS project (openms.org),
source (github.com/OpenMS/OpenMS).
