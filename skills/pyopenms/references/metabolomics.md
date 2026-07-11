# Metabolomics Workflows

Untargeted metabolomics turns raw LC-MS runs into a features-by-samples quant
table. The stages: feature finding tuned for small molecules → adduct grouping →
RT alignment → cross-sample linking → normalization → QC filtering → export.
Feature-finding and linking APIs live in `feature-detection.md`; this reference
covers the metabolomics-specific glue and post-processing.

## Untargeted pipeline

```python
import pyopenms as ms

def metabolomics_pipeline(input_files, output_dir):
    feature_maps = []
    for mzml in input_files:
        exp = ms.MSExperiment()
        ms.MzMLFile().load(mzml, exp)

        # Centroid if the run is profile-mode (SpectrumType: UNKNOWN=0, CENTROID=1, PROFILE=2)
        if exp.size() and exp.getSpectrum(0).getType() == 2:   # 2 == PROFILE
            picker = ms.PeakPickerHiRes()
            centroided = ms.MSExperiment()
            picker.pickExperiment(exp, centroided)
            exp = centroided

        # Mass-trace feature finding (see feature-detection.md)
        mtd = ms.MassTraceDetection()
        p = mtd.getParameters()
        p.setValue("mass_error_ppm", 5.0)          # tight for metabolites
        p.setValue("noise_threshold_int", 1000.0)
        mtd.setParameters(p)
        traces = []
        mtd.run(exp, traces, 0)

        epd = ms.ElutionPeakDetection()
        traces_split = []
        epd.detectPeaks(traces, traces_split)

        ffm = ms.FeatureFindingMetabo()
        fm = ms.FeatureMap()
        chrom_out = []
        ffm.run(traces_split, fm, chrom_out)
        fm.setPrimaryMSRunPath([mzml.encode()])
        feature_maps.append(fm)

    # Adduct grouping
    dech = ms.MetaboliteAdductDecharger()
    p = dech.getParameters()
    p.setValue("potential_adducts", "[M+H]+,[M+Na]+,[M+K]+,[M+NH4]+,[M-H]-,[M+Cl]-")
    p.setValue("charge_min", 1); p.setValue("charge_max", 1)
    dech.setParameters(p)
    grouped = []
    for fm in feature_maps:
        out = ms.FeatureMap()
        dech.compute(fm, out, ms.ConsensusMap())
        grouped.append(out)

    # RT alignment: align every map to the one with the most features (in place)
    ref_index = max(range(len(grouped)), key=lambda i: grouped[i].size())
    aligner = ms.MapAlignmentAlgorithmPoseClustering()
    aligner.setReference(grouped[ref_index])
    transformer = ms.MapAlignmentTransformer()
    for i, fm in enumerate(grouped):
        if i == ref_index:
            continue
        trafo = ms.TransformationDescription()
        aligner.align(fm, trafo)
        transformer.transformRetentionTimes(fm, trafo, True)

    # Link across samples
    grouper = ms.FeatureGroupingAlgorithmQT()
    p = grouper.getParameters()
    p.setValue("distance_RT:max_difference", 60.0)   # seconds
    p.setValue("distance_MZ:max_difference", 5.0)    # ppm
    p.setValue("distance_MZ:unit", "ppm")
    grouper.setParameters(p)
    consensus = ms.ConsensusMap()
    grouper.group(grouped, consensus)   # now RT-aligned in place

    ms.ConsensusXMLFile().store(f"{output_dir}/consensus.consensusXML", consensus)
    consensus.get_df().to_csv(f"{output_dir}/metabolite_table.csv", index=False)
    return consensus
```

Gap filling (re-quantifying missing values from raw traces) is not exposed in
the Python API; run the TOPP tool `FeatureFinderMetaboIdent` externally if you
need it.

## Adduct configuration

Choose adducts by ionization polarity.

```python
positive = ["[M+H]+", "[M+Na]+", "[M+K]+", "[M+NH4]+", "[2M+H]+", "[M+H-H2O]+"]
negative = ["[M-H]-", "[M+Cl]-", "[M+FA-H]-", "[2M-H]-"]

dech = ms.MetaboliteAdductDecharger()
p = dech.getParameters()
p.setValue("potential_adducts", ",".join(positive))
p.setValue("charge_min", 1); p.setValue("charge_max", 1); p.setValue("max_neutrals", 1)
dech.setParameters(p)
```

## Mass-based annotation

Match neutral masses against a compound list within a ppm tolerance. This gives
candidate formulas only; confirm with MS/MS.

```python
compounds = [
    {"name": "Glucose", "mass": 180.0634},
    {"name": "Citric acid", "mass": 192.0270},
]
proton = 1.007276
tol_ppm = 5.0

for feat in fm:
    neutral = feat.getMZ() - proton               # assumes [M+H]+
    for c in compounds:
        err_ppm = abs(neutral - c["mass"]) / c["mass"] * 1e6
        if err_ppm <= tol_ppm:
            print(f"{c['name']}  err={err_ppm:.2f} ppm")
```

For structure-level work on candidates (formula validation, isotope patterns,
depiction) hand the formula to `rdkit`.

## Normalization

TIC normalization to the median sample.

```python
import numpy as np
cm = ms.ConsensusMap()
ms.ConsensusXMLFile().load("consensus.consensusXML", cm)

n = len(cm.getColumnHeaders())
tic = np.zeros(n)
for cf in cm:
    for h in cf.getFeatureList():
        tic[h.getMapIndex()] += h.getIntensity()

factors = np.median(tic) / tic
# apply `factors[map_idx]` per handle intensity, or scale the exported DataFrame
```

## Quality control

Work on the exported DataFrame — clearer than mutating the consensus map.

```python
df = cm.get_df()

# CV filter: keep features stable across pooled QC injections
qc = [c for c in df.columns if "QC" in c]
if qc:
    cv = df[qc].std(axis=1) / df[qc].mean(axis=1) * 100
    df = df[cv < 30]

# Blank filter: drop features not >=3x above blanks
blanks = [c for c in df.columns if "Blank" in c]
samples = [c for c in df.columns if "Sample" in c]
if blanks and samples:
    ratio = df[samples].mean(axis=1) / (df[blanks].mean(axis=1) + 1)
    df = df[ratio > 3]
```

## Missing values

```python
import numpy as np
df = df.replace(0, np.nan)
for col in df.select_dtypes("number").columns:
    df[col] = df[col].fillna(df[col].min() / 2)   # half-minimum imputation
```

## Export

`consensus_map.get_df()` gives the fastest path to a CSV; for a labeled
features-by-samples matrix (feature IDs as rows/columns for tools like
MetaboAnalyst), build the table from `getColumnHeaders()` labels and each
consensus feature's `getFeatureList()` intensities, then `to_csv`.

## Experimental-design notes

- Inject a pooled QC every 5-10 samples; use it to tune parameters and compute
  CV.
- Run blanks to catch contamination.
- At least 3 biological replicates per group; randomize injection order.
- Scale RT-difference tolerances to gradient length (e.g. ~30 s for a 10-min
  gradient, ~90 s for 60 min).

Hand the cleaned quant table to `statistical-analysis`, `scikit-learn`,
`umap-learn`, or `pymc` for downstream modeling and to `matplotlib`/`seaborn`
for figures.
