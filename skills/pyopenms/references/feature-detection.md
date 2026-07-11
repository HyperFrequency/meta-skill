# Feature Detection and Linking

A *feature* is a persistent LC-MS signal (a chromatographic peak) described by
m/z, retention time, intensity, a quality score, and a convex hull in RT-m/z
space. *Linking* combines features across samples into a `ConsensusMap` for
quantitative comparison. All feature finders expect centroided input — run
`PeakPickerHiRes` first for profile data (see `signal-processing.md`).

## Feature finding

### Metabolomics: MassTraceDetection → ElutionPeakDetection → FeatureFindingMetabo

This three-stage pipeline is the current recommended route for small molecules.

```python
import pyopenms as ms

exp = ms.MSExperiment()
ms.MzMLFile().load("centroided.mzML", exp)

# 1. Assemble mass traces
mtd = ms.MassTraceDetection()
p = mtd.getParameters()
p.setValue("mass_error_ppm", 5.0)
p.setValue("noise_threshold_int", 1000.0)
mtd.setParameters(p)
mass_traces = []
mtd.run(exp, mass_traces, 0)                 # 0 = no max-trace limit

# 2. Split traces into elution peaks
epd = ms.ElutionPeakDetection()
mass_traces_split = []
epd.detectPeaks(mass_traces, mass_traces_split)

# 3. Group isotopes into features
ffm = ms.FeatureFindingMetabo()
p = ffm.getParameters()
p.setValue("isotope_filtering_model", "metabolites (5% RMS)")
ffm.setParameters(p)
features = ms.FeatureMap()
chrom_out = []
ffm.run(mass_traces_split, features, chrom_out)

ms.FeatureXMLFile().store("features.featureXML", features)
```

### Proteomics / generic centroided: FeatureFinder

Legacy but still used for centroided proteomics data. `run(name, in, out,
param, seeds)`.

```python
ff = ms.FeatureFinder()
p = ff.getParameters("centroided")
p.setValue("mass_trace:mz_tolerance", 10.0)   # ppm
p.setValue("mass_trace:min_spectra", 7)       # min scans per feature
p.setValue("isotopic_pattern:charge_low", 1)
p.setValue("isotopic_pattern:charge_high", 4)

features = ms.FeatureMap()
ff.run("centroided", exp, features, p, ms.FeatureMap())
```

## Inspecting features

```python
fm = ms.FeatureMap()
ms.FeatureXMLFile().load("features.featureXML", fm)

for feat in fm:
    feat.getMZ(); feat.getRT(); feat.getIntensity()
    feat.getCharge(); feat.getOverallQuality(); feat.getWidth()
    for iso in feat.getSubordinates():        # isotopic envelope
        iso.getMZ(); iso.getIntensity()

df = fm.get_df()                              # RT, mz, intensity, charge, quality
```

## RT alignment

Align retention times before linking.

```python
fm1, fm2 = ms.FeatureMap(), ms.FeatureMap()
ms.FeatureXMLFile().load("s1.featureXML", fm1)
ms.FeatureXMLFile().load("s2.featureXML", fm2)

# Align each map to a chosen reference (in place); align() takes one map + one trafo
aligner = ms.MapAlignmentAlgorithmPoseClustering()
aligner.setReference(fm1)
transformer = ms.MapAlignmentTransformer()
for fm in (fm2,):
    trafo = ms.TransformationDescription()
    aligner.align(fm, trafo)
    transformer.transformRetentionTimes(fm, trafo, True)   # shifts fm's RTs in place
```

## Linking across samples

```python
grouper = ms.FeatureGroupingAlgorithmQT()
p = grouper.getParameters()
p.setValue("distance_RT:max_difference", 30.0)   # seconds
p.setValue("distance_MZ:max_difference", 10.0)   # ppm
p.setValue("distance_MZ:unit", "ppm")
grouper.setParameters(p)

consensus = ms.ConsensusMap()
grouper.group([fm1, fm2, fm3], consensus)
ms.ConsensusXMLFile().store("consensus.consensusXML", consensus)

for cf in consensus:
    cf.getMZ(); cf.getRT()
    for handle in cf.getFeatureList():
        handle.getMapIndex(); handle.getIntensity()
```

## Adduct detection (small molecules)

Group different ionization forms of one neutral molecule and assign neutral
mass.

```python
dech = ms.MetaboliteAdductDecharger()
p = dech.getParameters()
p.setValue("potential_adducts", "[M+H]+,[M+Na]+,[M+K]+,[M-H]-")
p.setValue("charge_min", 1)
p.setValue("charge_max", 1)
p.setValue("max_neutrals", 1)
dech.setParameters(p)

fm_out = ms.FeatureMap()
dech.compute(fm, fm_out, ms.ConsensusMap())

for feat in fm_out:
    if feat.metaValueExists("adduct"):
        feat.getMetaValue("adduct"); feat.getMetaValue("dc_charge_adduct_mass")
```

## Filtering features

```python
kept = ms.FeatureMap()
for feat in fm:
    if feat.getOverallQuality() > 0.5 and feat.getIntensity() >= 1e4:
        if 200.0 <= feat.getMZ() <= 800.0:
            kept.push_back(feat)
```

Or filter the exported DataFrame with pandas for interactive work.

## Annotating features with identifications

Map peptide/protein IDs onto features by RT/m/z proximity.

```python
protein_ids, peptide_ids = [], []
ms.IdXMLFile().load("ids.idXML", protein_ids, peptide_ids)

mapper = ms.IDMapper()
mapper.annotate(fm, peptide_ids, protein_ids)

for feat in fm:
    for pid in feat.getPeptideIdentifications():
        for hit in pid.getHits():
            hit.getSequence().toString()
```

## End-to-end: detect + align + link across samples

```python
def detect_and_link(input_files, output_consensus):
    feature_maps = []
    for mzml in input_files:
        exp = ms.MSExperiment()
        ms.MzMLFile().load(mzml, exp)

        ff = ms.FeatureFinder()
        p = ff.getParameters("centroided")
        p.setValue("mass_trace:mz_tolerance", 10.0)
        p.setValue("mass_trace:min_spectra", 7)
        fm = ms.FeatureMap()
        ff.run("centroided", exp, fm, p, ms.FeatureMap())
        fm.setPrimaryMSRunPath([mzml.encode()])
        feature_maps.append(fm)

    # Align every map to the one with the most features (alignment is in place)
    ref_index = max(range(len(feature_maps)), key=lambda i: feature_maps[i].size())
    aligner = ms.MapAlignmentAlgorithmPoseClustering()
    aligner.setReference(feature_maps[ref_index])
    transformer = ms.MapAlignmentTransformer()
    for i, fm in enumerate(feature_maps):
        if i == ref_index:
            continue
        trafo = ms.TransformationDescription()
        aligner.align(fm, trafo)
        transformer.transformRetentionTimes(fm, trafo, True)

    grouper = ms.FeatureGroupingAlgorithmQT()
    p = grouper.getParameters()
    p.setValue("distance_RT:max_difference", 30.0)
    p.setValue("distance_MZ:max_difference", 10.0)
    p.setValue("distance_MZ:unit", "ppm")
    grouper.setParameters(p)

    consensus = ms.ConsensusMap()
    grouper.group(feature_maps, consensus)   # now RT-aligned in place
    ms.ConsensusXMLFile().store(output_consensus, consensus)
    return consensus
```
