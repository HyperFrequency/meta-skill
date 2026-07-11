# gget Workflows

Worked pipelines that chain multiple `gget` modules. Each is a template — swap in
your genes/species and prune steps you do not need. All snippets are Python
unless marked bash. Wrap network calls with error handling and caching (helpers
at the end) when running at scale.

---

## 1. Gene discovery → sequence → function

```python
import gget

# Discover, then narrow to top hits
hits = gget.search(["GABA", "receptor"], species="homo_sapiens", andor="and")
gene_ids = hits["ensembl_id"].tolist()[:5]

# Metadata (with PDB IDs) and sequences
info = gget.info(gene_ids, pdb=True)
nt = gget.seq(gene_ids)                 # nucleotide FASTA (str)
aa = gget.seq(gene_ids, translate=True) # protein FASTA (str)

# Correlated genes → enrichment
correlated = gget.archs4(info["gene_name"].iloc[0], which="correlation")
enrich = gget.enrichr(correlated["gene_symbol"].tolist()[:50],
                      database="ontology", plot=True)
```

## 2. Comparative structural biology (across species)

```python
human, mouse = "ENSG00000169174", "ENSMUSG00000044254"   # PCSK9 / Pcsk9

# Protein sequences → align
h_aa = gget.seq(human, translate=True)
m_aa = gget.seq(mouse, translate=True)
with open("pcsk9.fasta", "w") as f:
    f.write(h_aa + "\n" + m_aa)
alignment = gget.muscle("pcsk9.fasta")   # ClustalW-format

# Find existing structures before predicting new ones
pdb_hits = gget.blast(h_aa, database="pdbaa", limit=5)
gget.pdb("7S7U", save=True)              # download a known structure
# gget.alphafold(m_aa, plot=True)        # predict only if no structure exists
orthologs = gget.bgee(human, type="orthologs")
```

## 3. Cancer genomics (targets → mutations → pathways)

```python
targets = ["BRCA1", "BRCA2", "TP53", "PIK3CA", "ESR1"]
gene_ids = [gget.search([g], species="homo_sapiens", limit=1)["ensembl_id"].iloc[0]
            for g in targets]

for gid, name in zip(gene_ids, targets):
    print(name, gget.opentargets(gid, resource="diseases", limit=3))
    print(name, gget.opentargets(gid, resource="drugs", limit=3))

studies = gget.cbio_search(["breast", "cancer"])
gget.cbio_plot(studies[:2], targets, stratification="cancer_type",
               variation_type="mutation_occurrences", show=False)
gget.enrichr(targets, database="pathway", plot=True)
# gget.cosmic("BRCA1", cosmic_tsv_path="cosmic_cancer.tsv", limit=10)  # needs DB
```

## 4. Single-cell expression (fetch, then analyze elsewhere)

```python
import gget, scanpy as sc

genes = ["ACE2", "TMPRSS2", "CD4", "CD8A"]

# Inspect what exists before a large download
meta = gget.cellxgene(gene=genes, tissue="lung",
                      species="homo_sapiens", meta_only=True)

# Pull the AnnData, then hand off to scanpy / `anndata`
adata = gget.cellxgene(gene=genes, tissue="lung",
                       species="homo_sapiens", census_version="stable")
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.normalize_total(adata, target_sum=1e4); sc.pp.log1p(adata)
```

`gget` only *fetches* the matrix. QC, clustering, and differential expression
belong in an `anndata` / scanpy pipeline, not in gget.

## 5. Build a reference transcriptome (bash)

```bash
gget ref --list_species > species.txt

SPECIES=homo_sapiens; RELEASE=110    # pin release for reproducibility
gget ref -w gtf  -r $RELEASE -d $SPECIES
gget ref -w cdna -r $RELEASE -d $SPECIES

# Downstream indexing (example: kallisto)
CDNA=$(ls *.cdna.all.fa.gz)
kallisto index -i transcriptome.idx "$CDNA"

gget ref -w dna -r $RELEASE -d $SPECIES   # genome for alignment-based methods
```

## 6. Mutation impact assessment

```python
import gget, pandas as pd

mutations = [
    {"gene": "TP53", "mutation": "c.818G>A"},   # R273H hotspot
    {"gene": "EGFR", "mutation": "c.2573T>G"},  # L858R activating
]
for m in mutations:
    m["ensembl_id"] = gget.search([m["gene"]], species="homo_sapiens",
                                  limit=1)["ensembl_id"].iloc[0]
    wt = gget.seq(m["ensembl_id"])                       # FASTA str
    seq = "".join(wt.split("\n")[1:])                    # strip header
    m["mutated"] = gget.mutate([seq], mutations=pd.DataFrame(
        {"seq_ID": [m["gene"]], "mutation": [m["mutation"]]}))
    print(m["gene"], gget.opentargets(m["ensembl_id"], resource="diseases", limit=5))
```

## 7. Drug-target discovery

```python
import gget, pandas as pd

genes = gget.search(["alzheimer"], species="homo_sapiens", limit=50)
gene_info = gget.info(genes["ensembl_id"].tolist()[:10])   # keep <1000 IDs/call

scored = []
for gid, name in zip(gene_info["ensembl_id"], gene_info["gene_name"]):
    d = gget.opentargets(gid, resource="diseases", limit=10)
    hit = d[d["disease_name"].str.contains("Alzheimer", case=False, na=False)]
    if len(hit):
        scored.append({"ensembl_id": gid, "gene_name": name,
                       "score": hit["overall_score"].max()})

top = pd.DataFrame(scored).sort_values("score", ascending=False).head(5)
for _, r in top.iterrows():
    gget.opentargets(r["ensembl_id"], resource="tractability")
    gget.opentargets(r["ensembl_id"], resource="drugs", limit=5)
    gget.opentargets(r["ensembl_id"], resource="interactions", limit=10)
gget.enrichr(top["gene_name"].tolist(), database="pathway", plot=True)
```

---

## Robustness Helpers

### Error handling
```python
def safe(func, *a, **k):
    try:
        return func(*a, **k)
    except Exception as e:
        print(f"{func.__name__} failed: {e}")
        return None
```

### Rate limiting
```python
import time
def rate_limited(gene_ids, delay=1):
    out = []
    for i, gid in enumerate(gene_ids):
        out.append(gget.info([gid]))
        if i < len(gene_ids) - 1:
            time.sleep(delay)
    return pd.concat(out, ignore_index=True)
```

### Caching
```python
import os, pickle
def cached(path, func, *a, **k):
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    res = func(*a, **k)
    pickle.dump(res, open(path, "wb"))
    return res
```

Cross-skill handoffs: analyze fetched single-cell matrices with `anndata`; run
heavy/custom sequence work in `biopython`; orchestrate many databases
programmatically with `bioservices`; take cancer cohorts further in
`cancer-genomics-analysis`.
