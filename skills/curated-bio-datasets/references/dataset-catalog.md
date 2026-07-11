# Dataset Catalog

Per-dataset access details: download URLs, formats, key columns, parse snippets,
and caveats. All code assumes `import pandas as pd`. Verify API parameter names
against each provider's current docs — public bio APIs version their endpoints
and occasionally rename fields.

---

## 1. COSMIC — Catalogue of Somatic Mutations in Cancer

**Access:** free academic account (paid commercial) at
`https://cancer.sanger.ac.uk/cosmic/register`. Download the Cancer Gene Census
(CGC) CSV from `https://cancer.sanger.ac.uk/census`, or larger exports via SFTP
or the `cosmic` CLI. Data is licensed — respect the terms.

**Two things you usually want:**

- **Cancer Gene Census** (`cancer_gene_census.csv`) — the curated ~700-gene list.
  Key columns: `Gene Symbol`, `Tier` (1 = strong evidence, 2 = emerging),
  `Role in Cancer` (oncogene / TSG / fusion), `Hallmark`, `Mutation Types`,
  `Tumour Types(Somatic)`, `Tumour Types(Germline)`, `Molecular Genetics`.
- **Somatic mutation export** (`CosmicMutantExportCensus.tsv.gz`) — the full
  variant table (~30 GB uncompressed). Key columns: `Gene name`,
  `Mutation Description`, `Primary site`.

```python
census = pd.read_csv("cancer_gene_census.csv")
tier1 = census[census["Tier"] == 1]
# Genes implicated in a tumour type (free-text match on the somatic column):
breast = census[census["Tumour Types(Somatic)"].str.contains("breast", case=False, na=False)]
# Roles explode from a comma-joined string:
roles = census["Role in Cancer"].str.split(", ").explode().value_counts()
```

Roll the census up into oncogene / TSG / fusion counts and a tier breakdown:

```python
from collections import Counter
def summarize_census(df):
    roles = Counter()
    for cell in df["Role in Cancer"].dropna():
        for r in (x.strip().lower() for x in cell.split(",")):
            if "oncogene" in r: roles["oncogene"] += 1
            elif "tsg" in r or "tumor suppressor" in r: roles["TSG"] += 1
            elif "fusion" in r: roles["fusion"] += 1
    return {"total": len(df), "by_tier": df["Tier"].value_counts().to_dict(),
            "roles": dict(roles)}
```

---

## 2. GTEx — Genotype-Tissue Expression

**Access:** open. Portal REST API at `https://gtexportal.org/api/v2` plus bulk
downloads. v8 uses GRCh38 coordinates.

**Bulk files:**
- TPM matrix: `GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_tpm.gct.gz` (~2 GB)
- Sample annotations: `GTEx_Analysis_v8_Annotations_SampleAttributesDS.txt`
- eQTLs: `GTEx_Analysis_v8_eQTL.tar`

The TPM file is GCT format — two header lines before the table:

```python
tpm = pd.read_csv("GTEx_..._gene_tpm.gct.gz", sep="\t", skiprows=2)
genes = tpm["Name"]            # ENSG IDs
descriptions = tpm["Description"]  # gene symbols
expression = tpm.iloc[:, 2:]   # samples
```

**REST API — median expression across tissues.** The v2 endpoint is
`GET /api/v2/expression/medianGeneExpression`. Provide the gene (recent v2
prefers a `gencodeId` / ENSG identifier; a `datasetId` such as `gtex_v8`) and
read `data` from the JSON. **Confirm the exact query-parameter names against the
live GTEx API docs** — v2 tightened them relative to v1.

```python
import requests
resp = requests.get("https://gtexportal.org/api/v2/expression/medianGeneExpression",
                    params={"gencodeId": "ENSG00000141510.16", "datasetId": "gtex_v8"})
rows = resp.json().get("data", [])
# each row carries a tissue id (tissueSiteDetailId) and a median TPM value
```

Guidance: median TPM for cross-tissue comparison, raw counts for differential
expression, eQTL tables for variant interpretation.

---

## 3. GWAS Catalog

**Access:** open. Full associations dump:
`https://www.ebi.ac.uk/gwas/api/search/downloads/full`
→ `gwas_catalog_v1.0.2-associations_e*.tsv`.

Key columns: `DISEASE/TRAIT`, `SNPS`, `MAPPED_GENE`, `REPORTED GENE(S)`,
`P-VALUE`, `OR or BETA`.

```python
gwas = pd.read_csv("gwas_catalog_...-associations.tsv", sep="\t", low_memory=False)
gwas["P-VALUE"] = pd.to_numeric(gwas["P-VALUE"], errors="coerce")

def by_trait(df, keyword, pmax=5e-8):
    hits = df[df["DISEASE/TRAIT"].str.contains(keyword, case=False, na=False)]
    return hits[hits["P-VALUE"] < pmax].sort_values("P-VALUE")

def by_gene(df, symbol):
    m = df["MAPPED_GENE"].str.contains(symbol, case=False, na=False) | \
        df["REPORTED GENE(S)"].str.contains(symbol, case=False, na=False)
    return df[m].sort_values("P-VALUE")
```

Guidance: apply the genome-wide threshold 5e-8, check LD with the lead SNP, and
prefer `MAPPED_GENE` (positional) over `REPORTED GENE(S)` (author-assigned).

---

## 4. GeneBass — gene-based exome association (UK Biobank)

**Access:** open at `https://genebass.org/`; bulk results per phenotype as TSV.

Typical columns: `gene_symbol`, `annotation` (`pLoF`, `missense|LC`,
`synonymous`), `pvalue`, `beta`. Exome-wide significance ≈ 2.5e-6.

```python
gb = pd.read_csv("genebass_phenotype.tsv", sep="\t")
gb["pvalue"] = pd.to_numeric(gb["pvalue"], errors="coerce")
sig = gb[gb["pvalue"] < 2.5e-6]

# Compare burden categories for one gene:
for ann in ["pLoF", "missense|LC", "synonymous"]:  # synonymous = negative control
    row = gb[(gb.gene_symbol == "LDLR") & (gb.annotation == ann)]
    if len(row): print(ann, row.iloc[0][["pvalue", "beta"]].to_dict())
```

`synonymous` acts as a negative control — a signal there suggests confounding.

---

## 5. BioGRID — protein-protein interactions

**Access:** open. Latest release archive:
`https://downloads.thebiogrid.org/BioGRID/Release-Archive/`
→ use tab3 format (`BIOGRID-ALL-*.tab3.txt`).

Filter both interactors to one organism (NCBI taxid 9606 = human) and, for
confidence, to specific experiment types. Key columns: `Official Symbol
Interactor A/B`, `Organism ID Interactor A/B`, `Experimental System`,
`Experimental System Type`, `Throughput`, and a PubMed ID column used to weight
edges by publication support.

```python
cols = ["Official Symbol Interactor A", "Official Symbol Interactor B",
        "Organism ID Interactor A", "Organism ID Interactor B",
        "Experimental System"]
bg = pd.read_csv("BIOGRID-ALL-LATEST.tab3.txt", sep="\t", usecols=cols, low_memory=False)
bg = bg[(bg["Organism ID Interactor A"] == 9606) &
        (bg["Organism ID Interactor B"] == 9606)]
bg = bg[bg["Experimental System"].isin(["Affinity Capture-MS", "Two-hybrid"])]
```

Network construction and topology metrics live in
`enrichment-and-networks.md`.

---

## 6. MSigDB — Molecular Signatures Database

**Access:** open (registration). Collections at
`https://www.gsea-msigdb.org/gsea/msigdb/collections.jsp`. Download `.gmt`
files. Collections: **H** (50 hallmark sets, most interpretable), C1
(positional), C2 (curated: KEGG/Reactome/BioCarta/WikiPathways), C3 (regulatory),
C4 (computational), C5 (ontology: GO BP/CC/MF, HPO), C6 (oncogenic), C7
(immunologic), C8 (cell type).

GMT format is one gene set per line: `name <tab> description <tab> gene1 <tab>
gene2 ...`. Parsing + enrichment are in `enrichment-and-networks.md`.

Collection prefixes (for filtering a merged `.gmt` by name):

| Collection | Name prefixes |
| --- | --- |
| H | `HALLMARK_` |
| C2 | `KEGG_`, `REACTOME_`, `BIOCARTA_`, `PID_`, `WP_` |
| C5 | `GOBP_`, `GOCC_`, `GOMF_`, `HP_` |
| C6 | `ONCOGENIC_` |
| C7 | `IMMUNESIGDB_`, `GSE...` |
| C8 | `CELL_TYPE_` |

---

## 7. DisGeNET — disease-gene associations

**Access changed in 2023.** The old open `curated_gene_disease_associations.tsv.gz`
dumps were retired; current access is via a free-account API key at
`https://www.disgenet.com/`. Verify your access method before scripting.

If you have a legacy or licensed TSV, key columns are `geneSymbol`,
`diseaseName`, `score` (0-1 confidence), `NofPmids`.

```python
dg = pd.read_csv("gene_disease_associations.tsv", sep="\t")

def diseases_for_gene(df, symbol, min_score=0.3):
    r = df[(df.geneSymbol == symbol) & (df.score >= min_score)]
    return r.sort_values("score", ascending=False)

def genes_for_disease(df, keyword, min_score=0.3):
    m = df.diseaseName.str.contains(keyword, case=False, na=False)
    return df[m & (df.score >= min_score)].sort_values("score", ascending=False)
```

Guidance: `score > 0.3` for moderate confidence; prefer curated sources; cross-
reference OMIM for Mendelian disease.

---

## 8. Gene Ontology

**Access:** open. OBO: `http://purl.obolibrary.org/obo/go.obo`;
JSON: `https://purl.obolibrary.org/obo/go.json`. Single-term lookups via the
QuickGO REST API.

**Parse the OBO** into `{id: {name, namespace, parents}}`, skipping obsolete
terms, then walk `is_a` edges upward for ancestors:

```python
def parse_go_obo(path):
    terms, cur = {}, None
    for line in open(path):
        line = line.strip()
        if line == "[Term]": cur = {}
        elif line == "" and cur is not None:
            if "id" in cur: terms[cur["id"]] = cur
            cur = None
        elif cur is not None and ": " in line:
            k, v = line.split(": ", 1)
            if k in ("id", "name", "namespace"): cur[k] = v
            elif k == "is_a": cur.setdefault("parents", []).append(v.split(" ! ")[0])
            elif k == "is_obsolete" and v == "true": cur = None
    return terms

def ancestors(terms, go_id):
    seen, queue = set(), [go_id]
    while queue:
        for p in terms.get(queue.pop(), {}).get("parents", []):
            if p not in seen: seen.add(p); queue.append(p)
    return seen
```

**QuickGO single-term lookup** (real endpoint):

```python
import requests
r = requests.get(f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}",
                 headers={"Accept": "application/json"})
term = r.json()["results"][0]  # name, aspect (BP/CC/MF), definition.text
```

The three GO namespaces are biological_process, molecular_function, and
cellular_component.
