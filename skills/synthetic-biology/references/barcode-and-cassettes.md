# Barcode Fitness & Expression Cassettes

Two loosely related design/analysis capabilities: reducing barcode-sequencing
counts to per-lineage fitness, and assembling annotated expression cassettes for
genome insertion.

---

## Barcode-sequencing fitness

In a pooled fitness screen or lineage-tracking experiment, each cell/strain
carries a unique DNA barcode; sequencing at several timepoints gives a
`barcode × timepoint` count matrix. Fitness is the change in a lineage's
relative abundance over time.

Uses pandas, NumPy, and `scipy.cluster.hierarchy`.

### Fitness from counts

```python
import numpy as np, pandas as pd

def analyze_barcode_fitness(counts, reference_timepoint="T0", min_reads=10):
    """counts: DataFrame, barcodes as index, timepoints as columns."""
    keep = counts[counts[reference_timepoint] >= min_reads].copy()   # drop noisy lineages
    freq = keep.div(keep.sum(axis=0), axis=1)                        # per-timepoint relative freq
    fitness = np.log2(freq.div(freq[reference_timepoint], axis=0) + 1e-10)
    return fitness.drop(columns=[reference_timepoint])               # log2 fold change vs reference
```

Steps and rationale:

1. **Filter** barcodes with fewer than `min_reads` (default 10) at the reference
   timepoint — low counts are dominated by PCR/sequencing sampling noise and
   produce wild fold-changes.
2. **Normalize** each timepoint column to relative frequency (sum to 1), so
   sequencing-depth differences between timepoints cancel.
3. **Log2 fold change** of each lineage's frequency vs its reference frequency.
   A small pseudocount (`1e-10`) avoids `log2(0)`; positive ⇒ enriched (fit),
   negative ⇒ depleted (unfit).

Report, per timepoint, how many barcodes have positive vs negative fitness as a
quick landscape summary.

### Clustering fitness trajectories

Group lineages with similar fitness profiles by Ward hierarchical clustering:

```python
from scipy.cluster.hierarchy import linkage, fcluster

def cluster_lineage_fitness(fitness, n_clusters=5):
    Z = linkage(fitness.values, method="ward")
    fitness = fitness.copy()
    fitness["cluster"] = fcluster(Z, n_clusters, criterion="maxclust")
    return fitness
```

Then summarize each cluster's mean fitness to identify enriched vs depleted
cohorts. Choose `n_clusters` from a dendrogram or a silhouette scan rather than
fixing it blindly.

### Caveats

- **Relative fitness only.** Frequencies are compositional — one lineage
  exploding drives every other's relative frequency down. Do not read absolute
  growth from this; pair with a total-population measurement if you need it.
- **Reference choice matters.** T0 is the usual baseline; a mid-experiment
  reference changes the sign/scale of every value.
- Barcodes below the filter are dropped, not zero-imputed — state the retained
  fraction.

---

## Expression cassette design & genome insertion

Assemble a promoter–RBS–CDS–terminator cassette as annotated Biopython
`SeqFeature`s and splice it into a genome `SeqRecord`, keeping downstream feature
coordinates correct. Uses `Bio.Seq`, `Bio.SeqRecord`, `Bio.SeqFeature`,
`Bio.SeqIO`.

### Assemble and insert

```python
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation

def insert_expression_cassette(genome, cds_dna, locus_position,
                               promoter_seq, rbs_seq, terminator_seq,
                               promoter_name="Ptac", gene_name="gfp",
                               terminator_name="T7_term"):
    # 1. build the cassette sequence and its internal (0-based) feature layout
    parts = [("promoter", promoter_name, promoter_seq),
             ("RBS", "RBS", rbs_seq),
             ("CDS", gene_name, cds_dna),
             ("terminator", terminator_name, terminator_seq)]
    cassette, feats, pos = "", [], 0
    for ftype, label, seq in parts:
        quals = {"label": label}
        if ftype == "CDS":
            quals["translation"] = str(Seq(seq).translate())
        feats.append(SeqFeature(FeatureLocation(pos, pos + len(seq)),
                                type=ftype, qualifiers=quals))
        cassette += seq
        pos += len(seq)
    offset = len(cassette)

    # 2. splice cassette into the genome at locus_position
    new_seq = str(genome.seq[:locus_position]) + cassette + str(genome.seq[locus_position:])

    # 3. shift existing features at/after the insert; keep upstream ones as-is
    new_features = []
    for f in genome.features:
        if int(f.location.start) >= locus_position:
            new_features.append(SeqFeature(
                FeatureLocation(f.location.start + offset, f.location.end + offset,
                                f.location.strand),
                type=f.type, qualifiers=f.qualifiers))
        else:
            new_features.append(f)

    # 4. place cassette features at their genomic coordinates
    for f in feats:
        new_features.append(SeqFeature(
            FeatureLocation(f.location.start + locus_position,
                            f.location.end + locus_position),
            type=f.type, qualifiers=f.qualifiers))

    return SeqRecord(Seq(new_seq), id=genome.id, name=genome.name,
                     description=f"{genome.description} + {gene_name} cassette",
                     features=new_features)
```

Write the annotated construct to GenBank:

```python
from Bio import SeqIO
SeqIO.write(new_record, "construct.gb", "genbank")
```

### Coordinate care (the part that bites)

- **Provide real part sequences.** Promoter, RBS, and terminator are placeholders
  unless you pass genuine parts (e.g. from the iGEM Registry). The RBS spacing and
  strength directly set expression.
- **Shift downstream features by the full insert length**, and only those at or
  after the insertion point — upstream features are untouched. A feature that
  *spans* the insertion site needs manual handling (split or extend); the simple
  offset above assumes clean, non-spanning features.
- **CDS frame & stops.** Ensure `cds_dna` starts with ATG and has no premature
  stop; `translate()` fills the `translation` qualifier for inspection.
- **GenBank vs 0-based slicing.** `FeatureLocation` is 0-based half-open (matches
  Python slicing); GenBank display is 1-based. Do not double-convert.
- For designing the CDS itself (host-optimal codons, GC, restriction-site-free),
  run it through `codon-optimization.md` first. For simulating the cloning steps
  that build the cassette (digest, Golden Gate, Gibson), use `molecular-cloning`.
