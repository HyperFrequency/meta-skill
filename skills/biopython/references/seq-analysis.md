# Sequence Analysis & Utilities

Grab-bag of the remaining `Bio` sub-packages: motifs, `SeqUtils`, restriction
analysis, codon tables, features, population genetics.

## Motifs — `Bio.motifs`

```python
from Bio import motifs
from Bio.Seq import Seq

m = motifs.create([Seq("TACAA"), Seq("TACGC"), Seq("TACAC"), Seq("AATGC")])
m.counts                       # position counts matrix
m.counts.consensus             # consensus sequence
m.counts.degenerate_consensus  # IUPAC ambiguity consensus
m.counts.information_content()

pwm  = m.counts.normalize(pseudocounts=0.5)   # position weight matrix
pssm = pwm.log_odds()                          # position-specific scoring matrix
for pos, score in pssm.search(Seq("ATACAGGACATACGC"), threshold=5.0):
    print(pos, score)
```

Read/write JASPAR, MEME, TRANSFAC, PFM:

```python
with open("m.jaspar") as h:
    m = motifs.read(h, "jaspar")        # or motifs.parse(h, "jaspar") for many
open("out.jaspar", "w").write(m.format("jaspar"))
```

Always add pseudocounts before `log_odds()` or zero-count cells blow up to
`-inf`.

## `Bio.SeqUtils`

```python
from Bio.SeqUtils import gc_fraction, molecular_weight, gc_skew
from Bio.SeqUtils import MeltingTemp as mt
from Bio.Seq import Seq

gc_fraction(Seq("ATCGATCG"))                       # 0.0–1.0
molecular_weight(Seq("ATCG"), seq_type="DNA")      # g/mol; "RNA" / "protein" too
gc_skew(Seq("ATCGGGCCC"), window=100)

mt.Tm_NN(Seq("ATCGATCGATCG"))                      # nearest-neighbor Tm (°C)
mt.Tm_NN(Seq("ATCG..."), Na=50, Mg=1.5)            # salt-corrected
mt.Tm_Wallace(Seq("ATCGATCG"))                     # 2·(A+T)+4·(G+C), short primers
```

### Protein analysis — `ProtParam`

```python
from Bio.SeqUtils.ProtParam import ProteinAnalysis
p = ProteinAnalysis("ACDEFGHIKLMNPQRSTVWY")
p.molecular_weight()
p.isoelectric_point()
p.instability_index()
p.aromaticity()
p.gravy()                              # grand average of hydropathy
p.secondary_structure_fraction()       # (helix, turn, sheet)
p.get_amino_acids_percent()
p.molar_extinction_coefficient()
```

`ProteinAnalysis` takes a plain string, not a `Seq`; strip stop `*` first.

## Restriction analysis — `Bio.Restriction`

```python
from Bio import Restriction
from Bio.Seq import Seq

seq = Seq("GAATTCATCGATGAATTC")
Restriction.EcoRI.search(seq)          # cut positions (1-based)

rb = Restriction.RestrictionBatch(["EcoRI", "BamHI", "PstI"])
{enz: sites for enz, sites in rb.search(seq).items() if sites}

ana = Restriction.Analysis(rb, seq)
ana.with_sites()                        # enzymes that cut
```

## Codon tables — `Bio.Data.CodonTable`

```python
from Bio.Data import CodonTable
std  = CodonTable.unambiguous_dna_by_id[1]     # standard
mito = CodonTable.unambiguous_dna_by_id[2]     # vertebrate mitochondrial
std.forward_table["ATG"]      # 'M'
std.start_codons, std.stop_codons
```

Pass the table id to `Seq.translate(table=2)` for non-standard codes.

## Ambiguity codes — `Bio.Data.IUPACData`

```python
from Bio.Data import IUPACData
IUPACData.ambiguous_dna_values["N"]    # 'GATC'
IUPACData.ambiguous_dna_values["R"]    # 'AG'
```

## Features — `Bio.SeqFeature`

```python
from Bio.SeqFeature import SeqFeature, FeatureLocation
f = SeqFeature(FeatureLocation(10, 50), type="CDS", strand=1,
               qualifiers={"gene": ["ABC1"]})
f.extract(record.seq)          # pull the feature's subsequence (strand-aware)
```

## Population genetics — `Bio.PopGen`

```python
from Bio.PopGen import GenePop
with open("data.gen") as h:
    rec = GenePop.read(h)
rec.loci_list, len(rec.populations)
```

`Bio.PopGen.GenePop.Controller.GenePopController` wraps the external GenePop
program for Fst / Hardy–Weinberg tests (requires the binary installed).

## FASTQ quality (per-letter annotations)

```python
from Bio import SeqIO
for r in SeqIO.parse("reads.fastq", "fastq"):
    q = r.letter_annotations["phred_quality"]
    avg, worst = sum(q)/len(q), min(q)
```

## Worked example — six-frame ORF finder

```python
def find_orfs(seq, min_aa=100):
    orfs = []
    for strand, nuc in [(+1, seq), (-1, seq.reverse_complement())]:
        for frame in range(3):
            prot = nuc[frame:].translate()
            start = 0
            while start < len(prot):
                stop = prot.find("*", start)
                if stop == -1:
                    stop = len(prot)
                if stop - start >= min_aa:
                    a, b = frame + start*3, frame + stop*3
                    orfs.append(dict(start=a, end=b, strand=strand,
                                     seq=nuc[a:b]))
                start = stop + 1
    return orfs
```

## Deprecated / removed

- `Bio.pairwise2` → use `Bio.Align.PairwiseAligner` (see `alignment.md`).
- `Bio.*.Applications` command-line wrappers were removed → use `subprocess`.
- `GenomeDiagram` and some graphics need `reportlab` installed separately.

## Gotchas

- Motif PWMs need pseudocounts; otherwise `log_odds` produces `-inf`.
- `gc_fraction` returns a fraction (0–1), not a percentage.
- `molecular_weight` needs the right `seq_type`; the wrong one silently returns
  a nonsense number.
- Restriction site positions are **1-based**, unlike most Python indexing.
