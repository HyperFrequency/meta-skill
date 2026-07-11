# Expression Signatures (NMF Metagenes) and DDR Networks

Extracting transcriptional programs from tumor expression matrices and analyzing
DNA-damage-response (DDR) pathway coordination.

## NMF metagene extraction

Non-negative Matrix Factorization decomposes a non-negative expression matrix
`V` (genes x samples) into `V ≈ W · H`, where `W` (genes x k) holds the
**metagene** loadings — additive gene programs — and `H` (k x samples) holds each
sample's activation of those programs. Because NMF forbids negative weights, the
factors are parts-based and directly interpretable as up-regulated gene sets,
unlike PCA components.

```python
from sklearn.decomposition import NMF
import numpy as np
import pandas as pd

def extract_metagenes(expression_matrix, n_components=5, top_genes=50):
    """Decompose a genes x samples matrix into k metagene programs.

    expression_matrix: DataFrame, genes as index, samples as columns,
                       NON-NEGATIVE (use TPM/RPKM/counts, never log-ratios).
    """
    X = np.clip(expression_matrix.values, 0, None)  # enforce non-negativity

    model = NMF(n_components=n_components, init="nndsvda",
                random_state=42, max_iter=500)
    W = model.fit_transform(X)  # genes x k  (gene loadings)
    H = model.components_        # k x samples (sample activations)

    metagenes = {}
    for k in range(n_components):
        loadings = pd.Series(W[:, k], index=expression_matrix.index)
        metagenes[f"Metagene_{k + 1}"] = loadings.nlargest(top_genes)

    print(f"Reconstruction error: {model.reconstruction_err_:.4f}")
    return metagenes, W, H, model
```

Key parameter facts:

- **Input must be non-negative.** Feed TPM, RPKM, or raw/normalized counts —
  never log2 fold-changes or z-scores. Clip tiny negatives from upstream
  normalization to zero.
- `init="nndsvda"` (NNDSVD with zeros filled by the data average) gives a
  deterministic, sensible starting point and usually converges faster than
  `init="random"`.
- Regularization uses `alpha_W`/`alpha_H` (and `l1_ratio` to mix L1/L2). Setting
  `l1_ratio` alone does nothing — you must also set a nonzero `alpha_W` for
  sparsity to take effect.
- Raise `max_iter` (500-1000) if you see a `ConvergenceWarning`.

### Choosing the rank k (consensus / cophenetic correlation)

The number of programs `k` is the central modeling choice. The standard method
(Brunet et al. 2004) runs NMF many times per candidate `k`, builds a consensus
matrix of how often each sample pair co-clusters, and scores stability with the
**cophenetic correlation** of that consensus. Pick the largest `k` before the
cophenetic coefficient drops sharply.

```python
import numpy as np
from sklearn.decomposition import NMF
from scipy.cluster.hierarchy import cophenet, linkage
from scipy.spatial.distance import squareform

def select_rank(expression_matrix, k_range=range(2, 9), n_runs=20):
    """Cophenetic-correlation stability across candidate NMF ranks."""
    X = np.clip(expression_matrix.values, 0, None)
    n_samples = X.shape[1]
    scores = {}
    for k in k_range:
        consensus = np.zeros((n_samples, n_samples))
        for seed in range(n_runs):
            model = NMF(n_components=k, init="random", random_state=seed, max_iter=300)
            H = model.fit_transform(X.T).T          # cluster samples
            assignment = np.argmax(H, axis=0)
            consensus += (assignment[:, None] == assignment[None, :])
        consensus /= n_runs
        distance = 1 - consensus
        linkage_matrix = linkage(squareform(distance, checks=False), method="average")
        coph_corr, _ = cophenet(linkage_matrix, squareform(distance, checks=False))
        scores[k] = coph_corr
    best_k = max(scores, key=scores.get)
    return best_k, scores
```

Consensus clustering is compute-heavy (`n_runs` NMF fits per `k`); start with a
small `n_runs` for a coarse sweep, then confirm the chosen `k` with more runs.

### Interpreting metagenes by enrichment

Turn each metagene's top genes into a biological label via over-representation
analysis. `gseapy` wraps Enrichr:

```python
import gseapy as gp

for name, loadings in metagenes.items():
    result = gp.enrichr(gene_list=list(loadings.index),
                        gene_sets="KEGG_2021_Human", outdir=None)
    top = result.results.iloc[0]["Term"] if len(result.results) else "None"
    print(f"{name}: {top}  |  top genes: {', '.join(loadings.index[:5])}")
```

Swap `gene_sets` for `MSigDB_Hallmark_2020`, `Reactome_2022`, or a custom `.gmt`.
For ranked GSEA (not just top-N over-representation), use `gp.prerank` on the full
metagene loading vector.

## DNA-damage-response (DDR) correlation networks

DDR genes coordinate their expression; tumors with a defective DDR pathway (e.g.
`BRCA1/2` loss, "BRCAness") lose that coordination. Comparing DDR co-expression
networks between tumor and normal surfaces disrupted regulatory edges.

```python
import networkx as nx
import pandas as pd

DDR_GENES = [
    "TP53", "BRCA1", "BRCA2", "ATM", "ATR", "CHEK1", "CHEK2",
    "RAD51", "PALB2", "XRCC1", "PARP1", "MLH1", "MSH2", "MSH6",
    "ERCC1", "XPA", "XPC", "POLH", "REV3L", "FANCA", "FANCD2",
]

def build_ddr_network(expression_df, ddr_genes=DDR_GENES, threshold=0.5):
    """Spearman co-expression graph over DDR genes present in the matrix."""
    present = [g for g in ddr_genes if g in expression_df.index]
    corr = expression_df.loc[present].T.corr(method="spearman")
    graph = nx.Graph()
    for i, a in enumerate(present):
        for b in present[i + 1:]:
            if abs(corr.loc[a, b]) > threshold:
                graph.add_edge(a, b, weight=corr.loc[a, b])
    return graph, corr

def disrupted_edges(tumor_expr, normal_expr, delta_threshold=0.3):
    """Edges whose DDR co-expression shifts most from normal to tumor."""
    _, corr_normal = build_ddr_network(normal_expr)
    _, corr_tumor = build_ddr_network(tumor_expr)
    rows = []
    for a in corr_normal.index:
        for b in corr_normal.columns:
            if a < b and a in corr_tumor.index and b in corr_tumor.columns:
                delta = abs(corr_normal.loc[a, b] - corr_tumor.loc[a, b])
                if delta > delta_threshold:
                    rows.append({"gene1": a, "gene2": b,
                                 "normal_corr": corr_normal.loc[a, b],
                                 "tumor_corr": corr_tumor.loc[a, b],
                                 "delta": delta})
    return pd.DataFrame(rows).sort_values("delta", ascending=False)
```

Caveats:

- Correlation networks need adequate sample size — Spearman correlations over
  fewer than ~20-30 samples per group are noisy; treat small-cohort edges as
  exploratory.
- A lost edge is a hypothesis about pathway disruption, not proof; corroborate
  with the corresponding somatic/CNV status of the driver gene (e.g. confirm
  `BRCA1/2` mutation or deletion alongside a BRCAness network signature).
- Extend `DDR_GENES` with the specific repair sub-pathway you care about (HRR,
  MMR, NER, BER, Fanconi) rather than treating DDR as one monolith.
