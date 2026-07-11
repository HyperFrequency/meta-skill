# File I/O and Formats

Every format has a dedicated file handler class named `<Format>File` with
`.load(path, container)` and `.store(path, container)`. Loaders mutate the
container passed by reference.

## Supported formats

| Category | Formats |
|---|---|
| Spectra | mzML, mzXML, mzData (deprecated) |
| Identification | idXML (OpenMS native), mzIdentML, pepXML, protXML |
| Features / quant | featureXML, consensusXML, mzTab |
| Sequences / targeted | FASTA, TraML |

mzML is the canonical, actively maintained format. Convert older formats to mzML
early in a pipeline.

## Reading mzML

### In-memory (small/medium files)

```python
import pyopenms as ms
exp = ms.MSExperiment()
ms.MzMLFile().load("sample.mzML", exp)
exp.getNrSpectra()
```

### On-disc (large files)

Reads spectra lazily instead of holding the whole run in RAM. Prefer this for
files that do not comfortably fit in memory.

```python
od = ms.OnDiscMSExperiment()
od.openFile("large.mzML")
for i in range(od.getNrSpectra()):
    spec = od.getSpectrum(i)   # loaded on demand
```

Guidance: use in-memory only when the file fits with headroom; otherwise on-disc.
Process spectra one at a time and avoid accumulating them into a list, which
would defeat the purpose.

## Writing mzML

```python
ms.MzMLFile().store("output.mzML", exp)

# Enable numpress/zlib compression via PeakFileOptions
handler = ms.MzMLFile()
opts = ms.PeakFileOptions()
opts.setCompression(True)
handler.setOptions(opts)
handler.store("compressed.mzML", exp)
```

## Identification files

`load` takes two lists (proteins, peptides), both populated in place.

```python
protein_ids, peptide_ids = [], []
ms.IdXMLFile().load("ids.idXML", protein_ids, peptide_ids)      # OpenMS native
ms.MzIdentMLFile().load("results.mzid", protein_ids, peptide_ids)
ms.PepXMLFile().load("results.pep.xml", protein_ids, peptide_ids)

ms.IdXMLFile().store("out.idXML", protein_ids, peptide_ids)
```

## Feature and consensus files

```python
fm = ms.FeatureMap()
ms.FeatureXMLFile().load("features.featureXML", fm)
ms.FeatureXMLFile().store("features.featureXML", fm)

cm = ms.ConsensusMap()
ms.ConsensusXMLFile().load("consensus.consensusXML", cm)
ms.ConsensusXMLFile().store("consensus.consensusXML", cm)
```

## FASTA and TraML

```python
entries = []
ms.FASTAFile().load("database.fasta", entries)
for e in entries:
    e.identifier; e.description; e.sequence
ms.FASTAFile().store("db.fasta", entries)

texp = ms.TargetedExperiment()
ms.TraMLFile().load("transitions.TraML", texp)
for tr in texp.getTransitions():
    tr.getPrecursorMZ(); tr.getProductMZ()
```

## mzTab reporting

```python
mztab = ms.MzTab()
md = mztab.getMetaData()
md.mz_tab_version.set("1.0.0")
md.title.set("Analysis results")
ms.MzTabFile().store("report.mzTab", mztab)
```

## Format conversion

Read with one handler, store with another over the same container.

```python
exp = ms.MSExperiment()
ms.MzXMLFile().load("data.mzXML", exp)
ms.MzMLFile().store("data.mzML", exp)      # mzXML -> mzML
```

## Instrument and sample metadata

```python
exp = ms.MSExperiment()
ms.MzMLFile().load("sample.mzML", exp)
settings = exp.getExperimentalSettings()

instr = settings.getInstrument()
instr.getName(); instr.getModel()
settings.getSample().getName()
for sf in settings.getSourceFiles():
    sf.getNameOfFile()
```

## Robust loading

Guard I/O — loaders raise on missing or malformed files.

```python
import os
path = "data.mzML"
if not (os.path.exists(path) and os.path.isfile(path)):
    raise FileNotFoundError(path)
try:
    exp = ms.MSExperiment()
    ms.MzMLFile().load(path, exp)
except Exception as err:
    print(f"Failed to load {path}: {err}")
    raise
```
