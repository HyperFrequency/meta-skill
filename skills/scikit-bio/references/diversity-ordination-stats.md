# Diversity, Ordination & Statistics

Deep reference for the microbiome / community-ecology core. Return to `SKILL.md`
for the capability map.

Everything here revolves around **counts** (an integer samples × features
matrix) and **`DistanceMatrix`** objects. The typical flow:

```
counts → beta_diversity → DistanceMatrix → pcoa (visualize) + permanova (test)
counts (+ tree) → alpha_diversity(faith_pd) / UniFrac
```

## Distance matrices

```python
import numpy as np
from skbio import DistanceMatrix, DissimilarityMatrix

dm = DistanceMatrix(
    np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0]]),
    ids=["A", "B", "C"],
)
dm["A", "B"]                 # scalar distance
dm.filter(["A", "C"])        # subset by ID
dm.condensed_form()          # 1D vector for scipy
dm.to_data_frame()           # pandas DataFrame
dm.write("dists.tsv"); DistanceMatrix.read("dists.tsv")

asym = DissimilarityMatrix(np.array([[0, 1], [3, 0]]), ids=["X", "Y"])
```

`DistanceMatrix` enforces symmetry and a zero diagonal; use
`DissimilarityMatrix` for asymmetric data. IDs make it join cleanly with
metadata and downstream tests.

## Alpha diversity (per-sample)

```python
from skbio.diversity import alpha_diversity, get_alpha_diversity_metrics

get_alpha_diversity_metrics()                      # list installed metric names

shannon = alpha_diversity("shannon", counts, ids=sample_ids)   # pandas Series
simpson = alpha_diversity("simpson", counts, ids=sample_ids)
chao1   = alpha_diversity("chao1",   counts, ids=sample_ids)
```

Phylogenetic alpha diversity (Faith's PD) needs a tree and the feature IDs that
label the count columns, passed as **`taxa=`** (this was `otu_ids=` before 0.6):

```python
faith = alpha_diversity(
    "faith_pd", counts, ids=sample_ids,
    tree=tree, taxa=feature_ids,
)
```

Metric names are version-dependent (e.g. `observed_otus` → `observed_features` /
`sobs`). Always confirm with `get_alpha_diversity_metrics()`.

## Beta diversity (between samples)

```python
from skbio.diversity import beta_diversity, get_beta_diversity_metrics, partial_beta_diversity

bc = beta_diversity("braycurtis", counts, ids=sample_ids)      # DistanceMatrix
jc = beta_diversity("jaccard",    counts, ids=sample_ids)

# Phylogenetic (UniFrac): pass tree= and taxa=
uu = beta_diversity("unweighted_unifrac", counts, ids=sample_ids,
                    tree=tree, taxa=feature_ids)
wu = beta_diversity("weighted_unifrac",   counts, ids=sample_ids,
                    tree=tree, taxa=feature_ids)
```

The tree's tip set may be a **superset** of `taxa`, but never a subset — every
feature must have a matching tip, or you get `MissingNodeError`. `shear` the tree
to the feature IDs first.

For only a few sample pairs (cheaper than all-pairs), the single-pair helpers
live in `skbio.diversity.beta` — e.g. `unweighted_unifrac(u_counts, v_counts,
taxa, tree)` — and `partial_beta_diversity(metric, counts, ids, id_pairs=...)`
computes a chosen subset of pairs.

## Rarefaction

```python
from skbio.diversity import subsample_counts

rarefied = subsample_counts(count_vector, n=1000)   # one sample, depth 1000
```

Rarefy per sample to a common depth, then recompute diversity. For confidence
intervals, repeat the subsample many times and aggregate.

## Ordination

```python
from skbio.stats.ordination import pcoa, ca, cca, rda

# PCoA from any distance matrix
res = pcoa(bc)
res.samples["PC1"], res.samples["PC2"]   # coordinates (DataFrame)
res.proportion_explained                 # variance fraction per axis
res.eigvals                              # eigenvalues
res.write("ordination.txt")
from skbio import OrdinationResults
res = OrdinationResults.read("ordination.txt")
```

Constrained/other ordinations take a species matrix (and, for CCA/RDA, an
environmental matrix):

```python
cca_res = cca(species_matrix, env_matrix)   # canonical correspondence analysis
rda_res = rda(species_matrix, env_matrix)   # redundancy analysis (linear)
ca_res  = ca(contingency_table)             # correspondence analysis
cca_res.biplot_scores                       # env-variable arrows
```

- **PCoA** works on any dissimilarity matrix.
- **CCA/RDA** reveal which environmental variables drive community structure.
- Results plot directly with `matplotlib` / `seaborn` — scale axes by
  `proportion_explained`.

## Statistical tests (permutation-based)

```python
from skbio.stats.distance import permanova, anosim, permdisp, mantel

r = permanova(dm, grouping, permutations=999)   # pandas Series of results
r["test statistic"], r["p-value"]

anosim(dm, grouping, permutations=999)          # alternative group test
permdisp(dm, grouping, permutations=999)        # test dispersion homogeneity

# Mantel: correlation between two distance matrices → (r, p_value, n)
corr, p, n = mantel(dm1, dm2, method="pearson", permutations=999)
```

- `grouping` is a per-sample list/Series aligned to the matrix IDs (or a
  metadata column name plus a DataFrame).
- **PERMANOVA is sensitive to unequal dispersion** — a significant result may
  reflect spread rather than centroid location. Always run `permdisp` alongside.
- `mantel` returns a `(coefficient, p_value, n)` tuple; `method` is `"pearson"`
  or `"spearman"`. For partial Mantel controlling a third matrix, see
  `skbio.stats.distance.pwmantel` / the `mantel` docs.
- `bioenv` (`skbio.stats.distance.bioenv`) finds the subset of environmental
  variables best correlated with community distances.

## Worked pipeline (microbiome diversity)

```python
from skbio import Table
from skbio.diversity import beta_diversity
from skbio.stats.ordination import pcoa
from skbio.stats.distance import permanova

table   = Table.read("feature-table.biom")
counts  = table.matrix_data.toarray().T           # samples × features
sids    = list(table.ids(axis="sample"))
fids    = list(table.ids(axis="observation"))

dm  = beta_diversity("braycurtis", counts, ids=sids)
ord = pcoa(dm)
res = permanova(dm, grouping, permutations=999)    # grouping from metadata
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ValueError: Counts must be integers` | You passed relative abundances — convert to integer counts. |
| `TypeError: unexpected keyword 'otu_ids'` | 0.6+ renamed the phylogenetic arg to `taxa=`. |
| `MissingNodeError` / `DuplicateNodeError` | Feature IDs and tree tips disagree — `shear` the tree, dedupe IDs. |
| PERMANOVA significant but suspicious | Confirm it is location, not dispersion — run `permdisp`. |
| Unknown metric name | Call `get_alpha_diversity_metrics()` / `get_beta_diversity_metrics()`. |
| PCoA slow/huge | Distance matrix is O(n²) — subsample samples or reduce features first. |
