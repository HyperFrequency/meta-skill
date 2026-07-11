# File I/O, BIOM Tables & Embeddings

Deep reference for reading/writing biological formats, the BIOM feature table,
and protein/sequence embeddings. Return to `SKILL.md` for the capability map.

## The `skbio.io` registry

scikit-bio has one reader/writer registry that dispatches by format and target
type. Two entry points:

- `Obj.read(path, format=...)` / `obj.write(path, format=...)` — convenient for a
  single object (a `DNA`, `TreeNode`, `DistanceMatrix`, `TabularMSA`, ...).
- `skbio.io.read(path, format=..., constructor=...)` / `skbio.io.write(...)` —
  the general form, and the one that gives you a **generator** for large files.

```python
import skbio

# Single object
seq  = skbio.DNA.read("seq.fasta", format="fasta")
tree = skbio.TreeNode.read("tree.nwk")            # format auto-detected

# Stream many records — memory-safe for huge files
for seq in skbio.io.read("big.fasta", format="fasta", constructor=skbio.DNA):
    process(seq)

# Materialize to a list only if it fits in memory
seqs = list(skbio.io.read("in.fastq", format="fastq", constructor=skbio.DNA))
```

### Supported formats (partial)

- **Sequences:** FASTA, FASTQ, GenBank, EMBL, QSeq
- **Alignments:** Clustal, PHYLIP, Stockholm
- **Trees:** Newick
- **Tables:** BIOM (HDF5 and JSON)
- **Distances:** delimited square matrices (LSMat/TSV)
- **Analysis:** BLAST+ tabular (fmt 6/7), GFF3, ordination results
- **Metadata:** TSV/CSV with validation

Format is auto-detectable when writing `into=` a path, but pass `format=`
explicitly for clarity and to avoid ambiguous sniffing.

### Writing & conversion

```python
seq.write("out.fasta", format="fasta")

# Write many at once
skbio.io.write(seqs, format="fasta", into="out.fasta")

# Convert FASTQ → FASTA by piping read into write
recs = skbio.io.read("in.fastq", format="fastq", constructor=skbio.DNA)
skbio.io.write(recs, format="fasta", into="out.fasta")
```

### FASTQ quality

Quality scores land in `positional_metadata["quality"]`. Specify the encoding
with `variant=` (e.g. `"illumina1.8"`) or `phred_offset=` to avoid mis-decoded
scores.

```python
for read in skbio.io.read("reads.fastq", format="fastq",
                          constructor=skbio.DNA, variant="illumina1.8"):
    if read.positional_metadata["quality"].mean() < 20:
        continue
```

## BIOM feature tables — `skbio.Table`

`skbio.Table` is the BIOM `Table` (OTU/ASV feature table) — the standard
container in QIIME 2 workflows. It stores a sparse features × samples matrix with
IDs and metadata on both axes. Requires the `biom-format` package installed.

```python
from skbio import Table

table = Table.read("table.biom")                  # HDF5 or JSON auto-detected
sample_ids  = table.ids(axis="sample")
feature_ids = table.ids(axis="observation")       # OTUs/ASVs
mat = table.matrix_data                            # scipy sparse matrix

# Filtering: predicate over (values, id, metadata)
deep   = table.filter(lambda v, i, md: v.sum() > 1000, axis="sample",
                      inplace=False)
common = table.filter(lambda v, i, md: (v > 0).sum() >= 3, axis="observation",
                      inplace=False)

rel = table.norm(axis="sample", inplace=False)     # relative abundance
df  = table.to_dataframe()                          # pandas (dense) view
table.write("filtered.biom")
```

Notes:

- BIOM orients data as **features (rows / observations) × samples (columns)**.
  Transpose to get the samples × features matrix that `beta_diversity` expects
  (`table.matrix_data.toarray().T`).
- Prefer **HDF5** over JSON for large tables (smaller, faster).
- To build a `Table` from a pandas DataFrame or NumPy array, use the
  `biom.Table` constructor / helpers from the `biom-format` package — consult its
  docs for the exact signature rather than assuming a classmethod.

## Embeddings — `skbio.embedding`

Bridges protein-language-model vectors (ESM, ProtTrans, etc.) into scikit-bio's
distance/ordination ecosystem.

```python
from skbio.embedding import ProteinEmbedding, SequenceEmbedding

emb = ProteinEmbedding(embedding_array, sequence)   # per-residue embedding + seq
```

Capabilities (consult the `skbio.embedding` API for exact method/function names,
which are still stabilizing across 0.6.x):

- Wrap per-residue or per-sequence embeddings alongside their sequence.
- Reduce a collection of embeddings to a **`DistanceMatrix`** (e.g. Euclidean /
  cosine) so the whole diversity/ordination/statistics stack applies.
- Produce an **`OrdinationResults`** (PCoA of the embedding space) for
  visualization.
- Export to NumPy / pandas for downstream ML (clustering, classification).

This lets language-model representations feed the same PCoA + PERMANOVA analyses
you would run on UniFrac distances.

## Ecosystem interop

- **pandas / polars / NumPy** — `to_data_frame()` / `to_dataframe()` on distance
  matrices and tables; diversity results are pandas Series.
- **scikit-learn** — condensed distance matrices and coordinate arrays feed
  clustering/classifiers.
- **matplotlib / seaborn** — plot PCoA coordinates and distance-matrix heatmaps.
- **QIIME 2** — export artifacts (`qiime tools export`) to BIOM/Newick/distance
  matrices, analyze here, re-import if needed. scikit-bio objects are the native
  substrate of QIIME 2.
- **Biopython** — hand off for NCBI/BLAST/structure work via shared formats.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `MemoryError` reading a big file | Iterate with `skbio.io.read(...)` as a generator; do not `list()` it. |
| Wrong/garbled FASTQ quality | Set `variant=` or `phred_offset=` to the correct encoding. |
| `beta_diversity` gets a transposed matrix | BIOM is features × samples — transpose to samples × features. |
| Ambiguous-format read error | Pass `format=` explicitly instead of relying on sniffing. |
| BIOM I/O `ImportError` | Install `biom-format` (`uv pip install biom-format`). |
| `ValueError: IDs must be unique` | Duplicate sample/feature IDs in the table — dedupe before load. |
