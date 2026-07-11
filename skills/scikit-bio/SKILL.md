---
name: scikit-bio
version: 0.1.0
description: >-
  scikit-bio (imported as `skbio`) is a BSD-licensed Python toolkit for
  bioinformatics, microbial ecology, and multivariate community statistics. Use
  it to manipulate DNA/RNA/protein sequences (transcribe, translate,
  reverse-complement, motifs, k-mers); read/write bioinformatics formats (FASTA,
  FASTQ, GenBank, Newick, BIOM); align sequences (Smith-Waterman via
  `pair_align`/SSW, plus `TabularMSA`); build and compare phylogenetic trees
  (`nj`, `upgma`, `gme`, `bme`, Robinson-Foulds); compute alpha/beta diversity
  including Faith's PD and weighted/unweighted UniFrac; run ordination (PCoA, CA,
  CCA, RDA); and test ecological hypotheses (PERMANOVA, ANOSIM, PERMDISP,
  Mantel) over `DistanceMatrix` objects. Reach for it for microbiome /
  QIIME 2-style diversity pipelines and ecology statistics. NOT for
  NCBI/BLAST/3D-structure work or general scriptable sequence pipelines (use
  `biopython`); single-cell count matrices (use `scanpy` / `anndata`); SAM/BAM/VCF
  (use `pysam`); or quick gene/accession lookups (use `gget`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (scikit-bio)"
---

# scikit-bio: Bioinformatics & Community Ecology

## Overview

scikit-bio (`skbio`) is the Python foundation of the QIIME 2 microbiome stack.
Its value is a set of composable, well-tested primitives plus the statistics
that turn them into biology: **grammared sequences** (`DNA`, `RNA`, `Protein`),
**alignments** (`TabularMSA`), **phylogenetic trees** (`TreeNode`), and — most
distinctively — **distance-matrix ecology**: diversity metrics, ordination, and
permutation tests over `DistanceMatrix` objects.

The mental model for the microbiome half is a pipeline of typed objects:

```
counts table  →  DistanceMatrix  →  ordination (PCoA)  +  hypothesis test (PERMANOVA)
     │                  ↑
   (+ tree)  →  UniFrac / Faith's PD
```

Learn the object types once — `Sequence`, `TabularMSA`, `TreeNode`,
`DistanceMatrix`, `OrdinationResults`, `Table` — and every function reads as a
transform between them.

This skill is a **router**. It gives the setup path, a capability map with
one-line quick-starts, and the non-obvious failure modes, then delegates full
API surface and worked examples to `references/`. Read the linked reference
before writing non-trivial code — the quick-starts are orientation, not the
whole API.

Target version: scikit-bio 0.6.x+ (Python 3.9+, requires NumPy/SciPy/pandas).
Several parameter names changed at 0.6 — see [When NOT / gotchas](#version-gotchas).

## When to Use This Skill

Trigger when the user wants to:

- Analyze **microbiome / community-ecology** data: alpha/beta diversity,
  UniFrac, Faith's PD, rarefaction.
- Reduce a distance matrix to coordinates with **ordination** (PCoA, CA, CCA,
  RDA) and interpret sample/feature axes.
- Run **permutation-based ecological tests** — PERMANOVA, ANOSIM, PERMDISP,
  Mantel / partial Mantel, BIOENV.
- Build, prune, reroot, traverse, or **compare phylogenetic trees** (distances,
  Robinson-Foulds) from distance matrices or Newick files.
- Manipulate DNA/RNA/protein sequences and **align** them (pairwise
  Smith-Waterman / SSW, or multiple-sequence `TabularMSA`).
- Read/write biological formats — FASTA, FASTQ, GenBank, Newick, **BIOM** tables
  — with streaming for large files.
- Work with **protein-language-model embeddings** inside the diversity /
  ordination / distance ecosystem.

## When NOT to Use This Skill

- **NCBI/Entrez access, BLAST, 3D structures (PDB/mmCIF), or a general scriptable
  sequence pipeline** — use `biopython`. scikit-bio has no database or BLAST layer.
- **Single-cell / bulk omics count matrices, embeddings, DE** — use `scanpy` /
  `anndata` (containers, scRNA pipelines) or `pydeseq2` (bulk DE).
- **High-throughput read files (SAM/BAM/CRAM/VCF/tabix)** — use `pysam`.
- **Quick one-off gene/accession lookups** — use `gget`.
- **Publication-grade tree figures** — scikit-bio only draws ASCII; export
  Newick and render with `etetoolkit` (ETE) or ggtree.
- **Generic ML / dimensionality reduction not tied to distance-matrix ecology**
  — use `scikit-learn`, `umap-learn`, `matplotlib`, `seaborn`.

## Setup

```bash
uv pip install scikit-bio          # pulls in numpy, scipy, pandas
# For BIOM table I/O you also need the biom-format package:
uv pip install biom-format
```

```python
import skbio
from skbio import DNA, TreeNode, DistanceMatrix
```

## Capability Map

Each capability has a deep reference. The quick-start is orientation only.

### 1. Sequences & alignment → `references/sequences-alignment.md`

Grammared `DNA`/`RNA`/`Protein` sequences, transforms, metadata, k-mers, and
pairwise/multiple alignment.

```python
from skbio import DNA
seq = DNA("ATGGCCATTGTAATG", metadata={"id": "s1"})
protein = seq.transcribe().translate()          # DNA → RNA → Protein
starts  = seq.find_with_regex("ATG")            # motif positions
```

Covers: sequence transforms (reverse-complement/transcribe/translate with
genetic-code tables), sequence/positional/interval metadata, Hamming & k-mer
distances; the modern `pair_align(seq1, seq2, mode=...)` interface, the classic
tuple-returning `local/global_pairwise_align*` functions, `StripedSmithWaterman`,
`TabularMSA` (consensus, conservation, column slicing), and CIGAR/`AlignPath`.

### 2. Phylogenetic trees → `references/trees.md`

`TreeNode` construction, manipulation, and comparison.

```python
from skbio.tree import nj
tree = nj(distance_matrix)                       # neighbor joining
sub  = tree.shear(["taxonA", "taxonB", "taxonC"])
```

Covers: construction (`nj`, `upgma`, `gme`, `bme`), Newick I/O, traversal, prune
(`shear`)/reroot (`root_at_midpoint`)/`find`/append/remove, patristic &
`cophenetic_matrix` distances, **`compare_rfd`** (Robinson-Foulds) and
`rf_dists`, `tip_tip_distances`, and `ascii_art`.

### 3. Diversity, ordination & statistics → `references/diversity-ordination-stats.md`

The microbiome-ecology core built on `DistanceMatrix`.

```python
from skbio.diversity import beta_diversity
from skbio.stats.ordination import pcoa
bc = beta_diversity("braycurtis", counts, ids=sample_ids)
pc = pcoa(bc)                                     # PCoA coordinates
```

Covers: `alpha_diversity` / `beta_diversity` (incl. phylogenetic `faith_pd`,
weighted/unweighted UniFrac via `tree=` + `taxa=`), `get_*_diversity_metrics`,
`partial_beta_diversity`, rarefaction (`subsample_counts`); `DistanceMatrix` /
`DissimilarityMatrix`; ordination (`pcoa`, `ca`, `cca`, `rda`,
`OrdinationResults`); and permutation tests (`permanova`, `anosim`, `permdisp`,
`mantel`, `bioenv`).

### 4. File I/O, BIOM tables & embeddings → `references/io-tables-embeddings.md`

Format-agnostic reader/writer, feature tables, and protein embeddings.

```python
import skbio
for seq in skbio.io.read("reads.fastq", format="fastq", constructor=skbio.DNA):
    ...                                           # streamed, memory-safe
```

Covers: `skbio.io.read`/`write` with auto-detection and generators, quality
scores from FASTQ, format conversion; the BIOM `Table` (filter/normalize/
`to_dataframe`); and `skbio.embedding` (`ProteinEmbedding`, `SequenceEmbedding`)
bridging language-model vectors into distances/ordination.

## Cross-Cutting Guidance

- **Counts are integers, not frequencies.** Diversity metrics expect abundance
  counts (samples × features). Convert relative abundances back to counts or the
  call will error or mislead.
- **Tree tips must cover feature IDs.** For UniFrac / Faith's PD, every count
  column must have a matching tip; the tree may be a superset. Align IDs and
  `shear` the tree first — this is the #1 source of errors.
- **`DistanceMatrix` is the hub.** It enforces symmetry + zero diagonal, is
  ID-indexed, and feeds ordination and every permutation test. Use
  `DissimilarityMatrix` for asymmetric data.
- **Stream large files.** Iterate with `skbio.io.read(...)` generators instead
  of materializing lists; use BIOM HDF5 (not JSON) for large tables.
- **PERMANOVA is sensitive to dispersion.** A significant PERMANOVA can reflect
  spread, not location — pair it with `permdisp`.
- **Use enough permutations.** 999+ for stable p-values in permutation tests.

<a id="version-gotchas"></a>
### Version gotchas (0.5 → 0.6+)

- Phylogenetic-diversity argument is now **`taxa=`**, not `otu_ids=`.
- Tree Robinson-Foulds is the method **`TreeNode.compare_rfd(other)`** (and
  `skbio.tree.rf_dists` for many trees) — there is no `robinson_foulds` method.
- Some alpha metrics were renamed (e.g. `observed_otus` → `observed_features` /
  `sobs`). Call `get_alpha_diversity_metrics()` to list what your install exposes.
- The classic `local/global_pairwise_align*` functions return a **3-tuple**
  `(TabularMSA, score, start_end_positions)`, not an object with `.score`. Prefer
  the newer `pair_align`, which returns a `PairAlignResult`.

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `ValueError: Counts must be integers` | Passed relative abundances — convert to integer counts. |
| `MissingNodeError` in UniFrac/Faith's PD | Feature ID absent from tree — `tree.shear(feature_ids)`, verify `taxa=` list. |
| `AttributeError: 'tuple' has no attribute 'score'` | Using classic `*_pairwise_align*` return as an object — unpack the 3-tuple or use `pair_align`. |
| `TypeError: unexpected keyword 'otu_ids'` | 0.6+ renamed it to `taxa=`. |
| `ValueError: IDs must be unique` | Duplicate sequence/sample IDs — dedupe before building the object. |
| Alignment errors on equal-length seqs | Inputs are pre-aligned — `degap()` both first. |

More failure modes and fixes live in each reference's troubleshooting section.

## Additional Resources

- Docs: https://scikit.bio/docs/latest/
- Repository: https://github.com/scikit-bio/scikit-bio
- Ecosystem: interoperates with QIIME 2 artifacts (BIOM, trees, distance
  matrices), pandas/polars/NumPy, and `scikit-learn`.
