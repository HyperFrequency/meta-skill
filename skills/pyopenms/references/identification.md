# Peptide and Protein Identification

pyOpenMS does not implement a database search. It provides *adapters* that shell
out to an externally installed engine (Comet, MSGF+, X!Tandem, OMSSA,
MSFragger, Mascot, Myrimatch), and — more importantly for scripting — a rich set
of tools to post-process the results: FDR control, protein inference, ID
mapping, in-silico digestion, and theoretical spectrum generation.

## Reading results

`load` populates two lists (proteins, peptides) in place.

```python
import pyopenms as ms
protein_ids, peptide_ids = [], []
ms.IdXMLFile().load("ids.idXML", protein_ids, peptide_ids)
len(protein_ids); len(peptide_ids)
```

### Peptide-level

```python
for pid in peptide_ids:
    pid.getRT(); pid.getMZ()
    pid.isHigherScoreBetter()                 # decides thresholding direction
    for hit in pid.getHits():                 # ranked best-first
        seq = hit.getSequence()
        seq.toString(); hit.getScore(); hit.getCharge()
        if seq.isModified():
            for i in range(seq.size()):
                res = seq.getResidue(i)
                if res.isModified():
                    res.getModificationName()
```

### Protein-level

```python
for prot in protein_ids:
    sp = prot.getSearchParameters()
    prot.getSearchEngine(); sp.db
    for hit in prot.getHits():
        hit.getAccession(); hit.getScore(); hit.getCoverage()
```

## False discovery rate

`FalseDiscoveryRate.apply` transforms scores to q-values in place (requires a
target-decoy search, see below). Filter on the resulting q-value, not the raw
engine score.

```python
fdr = ms.FalseDiscoveryRate()
fdr.apply(peptide_ids)

kept = []
for pid in peptide_ids:
    good = [h for h in pid.getHits() if h.getMetaValue("q-value") <= 0.01]
    if good:
        pid.setHits(good)
        kept.append(pid)
```

### Target-decoy database

FDR estimation needs decoys. Generate a reversed/shuffled decoy set and search
the combined database.

```python
entries = []
ms.FASTAFile().load("target.fasta", entries)

gen = ms.DecoyGenerator()
decoys = []
for e in entries:
    d = ms.FASTAEntry(e)
    d.identifier = "DECOY_" + e.identifier
    d.sequence = gen.reverseProtein(ms.AASequence.fromString(e.sequence)).toString()
    decoys.append(d)

ms.FASTAFile().store("target_decoy.fasta", entries + decoys)
```

(Exact decoy-generation calls vary by pyOpenMS version; confirm the
`DecoyGenerator` signature against the installed version's docstrings.)

## Protein inference

```python
mapper = ms.IDMapper()                          # attach IDs to features
fm = ms.FeatureMap()
ms.FeatureXMLFile().load("features.featureXML", fm)
mapper.annotate(fm, peptide_ids, protein_ids)

inference = ms.BasicProteinInferenceAlgorithm()  # group by shared peptides
inference.run(peptide_ids, protein_ids)
```

## Peptide sequences

```python
seq = ms.AASequence.fromString("PEPTIDE")
seq.getMonoWeight(); seq.getAverageWeight(); seq.size()

mod = ms.AASequence.fromString("PEPTIDEM(Oxidation)K")
mod.isModified(); mod.getMonoWeight()
```

## In-silico digestion

```python
enzyme = ms.ProteaseDigestion()
enzyme.setEnzyme("Trypsin")
enzyme.setMissedCleavages(2)

protein = ms.AASequence.fromString("MKTAYIAKQRQISFVKSHFSRQLEER")
peptides = []
enzyme.digest(protein, peptides)
for pep in peptides:
    pep.toString(); pep.getMonoWeight()
```

## Theoretical fragment spectra

Generate b/y ions for scoring or spectral prediction. Signature:
`getSpectrum(out_spectrum, peptide, min_charge, max_charge)`.

```python
gen = ms.TheoreticalSpectrumGenerator()
theo = ms.MSSpectrum()
gen.getSpectrum(theo, ms.AASequence.fromString("PEPTIDE"), 1, 1)
mz, intensity = theo.get_peaks()
```

To control which ion series are produced, tune the generator's `Param`
(`add_b_ions`, `add_y_ions`, `add_metainfo`, etc.) before calling `getSpectrum`.

## Post-processing workflow

```python
def process_ids(raw_idxml, output_idxml, q_cutoff=0.01):
    protein_ids, peptide_ids = [], []
    ms.IdXMLFile().load(raw_idxml, protein_ids, peptide_ids)

    ms.FalseDiscoveryRate().apply(peptide_ids)

    kept = []
    for pid in peptide_ids:
        good = [h for h in pid.getHits() if h.getMetaValue("q-value") <= q_cutoff]
        if good:
            pid.setHits(good)
            kept.append(pid)

    ms.BasicProteinInferenceAlgorithm().run(kept, protein_ids)
    ms.IdXMLFile().store(output_idxml, protein_ids, kept)
    return protein_ids, kept
```

## Interpreting scores

Score meaning differs by engine: some report E-values (lower is better), others
report ion scores (higher is better). Never hard-code a direction — read
`pid.isHigherScoreBetter()` and threshold accordingly, or work in q-value space
after `FalseDiscoveryRate.apply`.
