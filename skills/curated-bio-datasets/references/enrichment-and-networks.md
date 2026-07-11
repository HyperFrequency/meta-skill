# Enrichment and PPI Networks

The two analyses these datasets exist to feed. Enrichment turns a gene list plus
a gene-set collection (MSigDB, GO, KEGG) into ranked pathways. PPI network
construction turns BioGRID interactions into a graph you can query for hubs and
neighborhoods.

---

## Part A — Pathway / Overlap Enrichment

### Parse a GMT collection

MSigDB `.gmt` files are one gene set per line: `name <tab> description <tab>
gene1 <tab> gene2 ...`.

```python
from collections import OrderedDict

def parse_gmt(path):
    sets = OrderedDict()
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, description, *genes = parts
        genes = {g.strip().upper() for g in genes if g.strip()}
        if name and genes:
            sets[name] = {"description": description.strip(), "genes": genes}
    if not sets:
        raise ValueError(f"No valid gene sets in {path}")
    return sets
```

Filter a merged collection by name prefix (see the collection-prefix table in
`dataset-catalog.md`) or by keyword before running enrichment on the whole thing.

### Option 1 — gseapy (online Enrichr libraries)

Easiest path when your genes are HUGO symbols and you want a maintained library.
`enrichr` hits the Enrichr web service; `enrich` runs a local `.gmt`.

```python
import gseapy as gp

# Online named library:
enr = gp.enrichr(gene_list=["TP53", "BRCA1", "ATM", "CHEK2", "PTEN"],
                 gene_sets="MSigDB_Hallmark_2020", outdir=None)
sig = enr.results[enr.results["Adjusted P-value"] < 0.05]
print(sig[["Term", "Adjusted P-value", "Overlap", "Combined Score"]].head(10))

# Local GMT (offline): gp.enrich(gene_list=..., gene_sets="my.gmt", ...)
```

Common Enrichr library names: `MSigDB_Hallmark_2020`, `KEGG_2021_Human`,
`GO_Biological_Process_2021`, `GO_Molecular_Function_2021`,
`GO_Cellular_Component_2021`, `Reactome_2022`.

### Option 2 — local hypergeometric / Fisher test with BH-FDR

When you need a fully offline, dependency-light test (no network, no scipy), the
one-sided hypergeometric upper tail *is* Fisher's exact test for enrichment.
Model: population `M` background genes, `n` in the gene set, `N` in your query
list, `k` observed in the overlap.

```python
import math

def _log_fact(n):
    return 0.0 if n <= 1 else sum(math.log(i) for i in range(2, n + 1))

def _log_comb(n, k):
    if k < 0 or k > n:
        return float("-inf")
    return _log_fact(n) - _log_fact(k) - _log_fact(n - k)

def hypergeom_pvalue(k, M, n, N):
    """P(X >= k), X ~ Hypergeometric(M, n, N). One-sided enrichment p-value."""
    if k <= 0:
        return 1.0
    if min(M, n, N) <= 0:
        return 1.0
    total = 0.0
    for i in range(k, min(n, N) + 1):
        total += math.exp(_log_comb(n, i) + _log_comb(M - n, N - i) - _log_comb(M, N))
    return min(total, 1.0)
```

Score every gene set, then rank by p-value:

```python
def enrichment(gene_sets, query, background=20000):
    query = {g.upper() for g in query}
    M, N = max(background, len(query)), len(query)
    rows = []
    for name, data in gene_sets.items():
        gs = data["genes"]
        overlap = query & gs
        k, n = len(overlap), len(gs)
        rows.append({
            "gene_set": name,
            "size": n,
            "overlap": k,
            "overlap_genes": sorted(overlap),
            "pvalue": hypergeom_pvalue(k, M, n, N),
            "fold": (k / N) / (n / M) if n and N else 0.0,
        })
    rows.sort(key=lambda r: (r["pvalue"], -r["overlap"]))
    return rows
```

Correct for multiple testing with Benjamini-Hochberg (monotone-enforced):

```python
def bh_fdr(rows):
    """Add an 'fdr' field. rows must already be p-value ascending."""
    m = len(rows)
    for i, r in enumerate(rows):
        r["fdr"] = min(r["pvalue"] * m / (i + 1), 1.0)
    running = 1.0
    for r in reversed(rows):            # enforce monotonic non-increasing FDR
        running = min(running, r["fdr"])
        r["fdr"] = running
    return rows
```

For high-precision or very large runs, prefer `scipy.stats.hypergeom` /
`scipy.stats.fisher_exact` — the pure-Python factorials above lose precision at
large `M`. `background=20000` approximates the protein-coding genome; set it to
your actual assayed universe when you have one (e.g. genes expressed in the
experiment) for a less anti-conservative test.

### Enrichment pitfalls

- Gene symbols must match the collection's namespace (HUGO). Non-matching
  symbols silently contribute zero overlap.
- Require the query list to have more than ~5 genes; tiny lists produce
  unstable, uninterpretable p-values.
- Report FDR, not raw p-values, and quote fold-enrichment + overlap size so a
  reader can judge whether a "significant" set is driven by one or two genes.

---

## Part B — Protein-Interaction Networks from BioGRID

### Build the graph

Parse BioGRID tab3 (see column list in `dataset-catalog.md`), collapse duplicate
interactor pairs, weight each edge by the number of supporting publications, and
build an undirected `networkx` graph. Filter to one organism and, for
confidence, to specific experiment types before graphing.

```python
import networkx as nx
from collections import defaultdict

def build_ppi(interactions):
    """interactions: iterable of (gene_a, gene_b, experiment, pubmed_id)."""
    pub, exp = defaultdict(set), defaultdict(set)
    for a, b, experiment, pubmed in interactions:
        a, b = a.strip().upper(), b.strip().upper()
        if not a or not b or a in ("-",) or b in ("-",) or a == b:
            continue
        pair = tuple(sorted((a, b)))
        pub[pair].add(pubmed)
        exp[pair].add(experiment)

    G = nx.Graph()
    for (a, b), pubmeds in pub.items():
        G.add_edge(a, b, weight=len(pubmeds), experiments=exp[(a, b)])
    return G
```

Weighting edges by distinct PubMed IDs lets you threshold on evidence: an edge
seen in one paper is weaker than one replicated across several. Apply a
`min_publications` cutoff by dropping edges whose `weight` is below it.

### Extract a subnetwork around genes of interest

```python
def neighborhood(G, genes):
    genes = {g.upper() for g in genes}
    present = genes & set(G.nodes())
    if not present:
        return nx.Graph()
    keep = set(present)
    for g in present:
        keep.update(G.neighbors(g))          # 1st-degree neighbors
    return G.subgraph(keep).copy()
```

### Topology statistics

```python
def topology(G):
    if G.number_of_nodes() == 0:
        return {}
    degrees = dict(G.degree())
    hubs = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(G),
        "avg_clustering": nx.average_clustering(G),
        "components": nx.number_connected_components(G),
        "hubs": hubs,                        # (gene, degree), top 10
    }
```

Export for Cytoscape / downstream tools with `nx.write_graphml(G, "ppi.graphml")`
— convert any set-valued edge attribute (e.g. `experiments`) to a
comma-joined string first, since GraphML cannot serialize Python sets.

### PPI pitfalls

- **Self-interactions** (`a == b`) and **cross-species rows** inflate the graph;
  drop them during parsing (organism filter on *both* interactors).
- **High-throughput screens** dominate BioGRID by volume. `Affinity Capture-MS`
  and `Two-hybrid` are the conventional high-confidence experiment types; filter
  to them, or weight by publication count, when precision matters.
- Hub genes are often study bias (well-characterized proteins get assayed more),
  not biology — corroborate hubs against an independent line of evidence.
