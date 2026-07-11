# Data Structures

pyOpenMS objects are Python handles over C++ classes. They are stateful, mutate
in place, and often return `bytes` for string fields. Most collection containers
expose `.get_df()` to hand data to pandas.

## Spectra and Experiments

### MSExperiment

Container for a whole LC-MS run: a list of spectra plus chromatograms.

```python
import pyopenms as ms

exp = ms.MSExperiment()
ms.MzMLFile().load("data.mzML", exp)

exp.getNrSpectra()            # spectrum count
exp.getNrChromatograms()      # chromatogram count
spec = exp.getSpectrum(0)     # index access

for spectrum in exp:          # iterable
    if spectrum.getMSLevel() == 2:
        rt = spectrum.getRT()

# Experimental metadata
settings = exp.getExperimentalSettings()
instrument_name = settings.getInstrument().getName()

# Deep copy (originals are otherwise mutated by filters)
exp_copy = ms.MSExperiment(exp)
```

### MSSpectrum

A single spectrum: parallel m/z and intensity arrays.

```python
spec = exp.getSpectrum(0)
spec.getMSLevel()             # 1 (survey) or 2 (fragment)
spec.getRT()                  # retention time, seconds
spec.size()                   # peak count

mz, intensity = spec.get_peaks()   # two numpy arrays
spec.set_peaks((mz, intensity))    # write back a tuple

# Precursor info on MS2 spectra
if spec.getMSLevel() == 2 and spec.getPrecursors():
    prec = spec.getPrecursors()[0]
    prec.getMZ(); prec.getCharge(); prec.getIntensity()
```

`get_peaks()` returns numpy arrays, so vectorized filtering works directly:
`mz[intensity > 1000]`.

### MSChromatogram

A chromatographic trace (TIC, XIC, or an SRM/MRM transition).

```python
for chrom in exp.getChromatograms():
    chrom.getNativeID()
    rt, intensity = chrom.get_peaks()
    chrom.getPrecursor().getMZ()   # for XIC / transitions
```

## Features

### Feature and FeatureMap

A `Feature` is a detected chromatographic peak with a 2D extent in RT-m/z space;
a `FeatureMap` is the set of features from one run.

```python
fm = ms.FeatureMap()
ms.FeatureXMLFile().load("features.featureXML", fm)
fm.size()

feat = fm[0]
feat.getMZ(); feat.getRT(); feat.getIntensity()
feat.getCharge()
feat.getOverallQuality()      # 0..1 fit quality
feat.getWidth()               # RT width

# Convex hull / bounding box (spatial extent)
hull = feat.getConvexHull()
bbox = hull.getBoundingBox()
rt_min, mz_min = bbox.minPosition()[0], bbox.minPosition()[1]

# Isotopic envelope as subordinate features
for sub in feat.getSubordinates():
    sub.getMZ(); sub.getIntensity()

# Arbitrary metadata
if feat.metaValueExists("label"):
    feat.getMetaValue("label")

# Build / mutate a map
new = ms.Feature(); new.setMZ(500.0); new.setRT(300.0); new.setIntensity(1e4)
fm.push_back(new)
fm.sortByRT()                 # also sortByMZ(), sortByIntensity()
df = fm.get_df()              # to pandas
```

### ConsensusFeature and ConsensusMap

A `ConsensusFeature` is one analyte linked across several runs; a `ConsensusMap`
is the cross-sample table.

```python
cm = ms.ConsensusMap()
ms.ConsensusXMLFile().load("consensus.consensusXML", cm)
cm.size()

# Which runs contributed which columns
for map_idx, hdr in cm.getColumnHeaders().items():
    hdr.filename; hdr.label; hdr.size

cf = cm[0]
cf.getMZ(); cf.getRT(); cf.getIntensity()
for handle in cf.getFeatureList():        # per-run measurements
    handle.getMapIndex(); handle.getIntensity(); handle.getMZ(); handle.getRT()

df = cm.get_df()
```

## Identifications

### PeptideIdentification and PeptideHit

One `PeptideIdentification` per spectrum; each holds ranked `PeptideHit`s.

```python
protein_ids, peptide_ids = [], []
ms.IdXMLFile().load("ids.idXML", protein_ids, peptide_ids)

pid = peptide_ids[0]
pid.getRT(); pid.getMZ()
pid.getScoreType()
pid.isHigherScoreBetter()     # ALWAYS check before thresholding

for hit in pid.getHits():
    hit.getSequence().toString()
    hit.getScore(); hit.getRank(); hit.getCharge()
    for acc in hit.extractProteinAccessionsSet():
        acc.decode()          # bytes -> str
```

### ProteinIdentification and ProteinHit

```python
prot = protein_ids[0]
prot.getSearchEngine(); prot.getSearchEngineVersion()

sp = prot.getSearchParameters()
sp.db; sp.missed_cleavages; sp.precursor_mass_tolerance
sp.digestion_enzyme.getName()

for hit in prot.getHits():
    hit.getAccession(); hit.getScore(); hit.getCoverage()
    hit.getDescription(); hit.getSequence()
```

## Sequences and Formulas

### AASequence

Peptide sequence with modification support.

```python
seq = ms.AASequence.fromString("PEPTIDE")
seq.toString(); seq.size()
seq.getMonoWeight()           # monoisotopic mass
seq.getAverageWeight()

for i in range(seq.size()):
    res = seq.getResidue(i)
    res.getOneLetterCode(); res.getMonoWeight(); res.getFormula().toString()

# Residue and terminal modifications
mod = ms.AASequence.fromString("PEPTIDEM(Oxidation)K")
mod.isModified()
term = ms.AASequence.fromString(".(Acetyl)PEPTIDE")   # N-terminal mod
```

### EmpiricalFormula

```python
f = ms.EmpiricalFormula("C6H12O6")        # glucose
f.toString(); f.getMonoWeight(); f.getAverageWeight()
f.getElementalComposition()[b"C"]          # per-element counts; dict keyed by element-symbol bytes
combined = f + ms.EmpiricalFormula("H2O")  # formula arithmetic
```

## Param

Every algorithm is configured through a `Param` object.

```python
algo = ms.GaussFilter()
params = algo.getParameters()

for key in params.keys():
    key, params.getValue(key)              # keys are colon-nested, e.g. b"mass_trace:mz_tolerance"

params.setValue("gaussian_width", 0.2)
algo.setParameters(params)
params_copy = ms.Param(params)             # copy to reuse across runs
```

## Handling large files

For multi-GB mzML, avoid full in-memory loading; use on-disc access that reads
spectra lazily.

```python
od = ms.OnDiscMSExperiment()
od.openFile("huge.mzML")
n = od.getNrSpectra()
spec = od.getSpectrum(100)     # loaded on demand
```
