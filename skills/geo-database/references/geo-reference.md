# GEO Database — Reference

Deep reference for NCBI GEO retrieval. The parent `SKILL.md` is the router; this
file holds exact parameters, format specs, and worked code. Nothing here invents
APIs — `GEOparse` and `Bio.Entrez` signatures are as documented upstream.

---

## 1. E-utilities API

NCBI's Entrez Programming Utilities give programmatic access to GEO metadata.
Base URL: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`. Default output is
XML. Relevant databases: **`gds`** (GEO DataSets/Series) and **`geoprofiles`**
(gene-centric expression). Access them through Biopython's `Bio.Entrez`, which
wraps every program below and parses responses with `Entrez.read(handle)`.

Set `Entrez.email` (required) and optionally `Entrez.api_key` before any call.

### esearch — query → UID list

Params: `db` (required), `term` (required), `retmax` (default 20, max 10000),
`retstart` (pagination), `usehistory` (`"y"` to stash results server-side),
`sort`, `field`, `datetype`, `reldate`, `mindate`/`maxdate` (`YYYY/MM/DD`).

```python
from Bio import Entrez
Entrez.email = "you@example.com"

h = Entrez.esearch(db="gds", term="breast cancer AND Homo sapiens",
                   retmax=100, usehistory="y")
res = Entrez.read(h); h.close()
# res keys: Count, RetMax, RetStart, IdList, and (if usehistory) QueryKey, WebEnv
```

### esummary — document summaries

Params: `db`, `id` (comma-separated UIDs, or `query_key`+`WebEnv`), `retmode`
(`xml`/`json`), `version` (`"2.0"` recommended).

```python
h = Entrez.esummary(db="gds", id="200000001,200000002", version="2.0")
summaries = Entrez.read(h); h.close()
# gds summary fields: Accession, title, summary, PDAT, n_samples, taxon/Organism,
#                     GPL, PubMedIds, gdsType
```

### efetch — full records

Params: `db`, `id`, `retmode` (`xml`/`text`), `rettype` (db-specific).

```python
h = Entrez.efetch(db="gds", id="200000001", retmode="xml")
records = Entrez.read(h); h.close()
```

### elink — cross-database links

Params: `dbfrom` (required), `db` (target), `id`, `cmd`
(`neighbor` default, `neighbor_score`, `acheck`, `ncheck`, `llinks`).

```python
# GEO dataset -> linked PubMed articles
h = Entrez.elink(dbfrom="gds", db="pubmed", id="200000001")
links = Entrez.read(h); h.close()
```

### epost — upload a UID list to the history server

Params: `db`, `id`. Returns `QueryKey` + `WebEnv` for use in later calls — the
right way to process large ID lists without stuffing them into every URL.

```python
ids = ",".join(str(i) for i in range(200000001, 200000101))
r = Entrez.read(Entrez.epost(db="gds", id=ids))
query_key, webenv = r["QueryKey"], r["WebEnv"]
```

### einfo — database metadata / searchable fields

Params: `db` (omit for the list of all databases), `version="2.0"` for field
detail. Use it to discover valid search fields for `gds` before guessing.

```python
info = Entrez.read(Entrez.einfo(db="gds", version="2.0"))
```

### Batched metadata fetch (rate-limited)

```python
import time
from Bio import Entrez
Entrez.email = "you@example.com"

def fetch_metadata(accessions, delay=0.34):   # 0.34s -> ~3 req/s (no API key)
    out = {}
    for acc in accessions:
        try:
            s = Entrez.read(Entrez.esearch(db="gds", term=f"{acc}[Accession]"))
            if s["IdList"]:
                summ = Entrez.read(Entrez.esummary(db="gds", id=s["IdList"][0]))
                out[acc] = summ[0]
        except Exception as e:
            out[acc] = {"error": str(e)}
        time.sleep(delay)
    return out
```

---

## 2. Search-field qualifiers

Attach `[Field]` to a term to constrain it. Combine with `AND`/`OR`/`NOT` and
parentheses.

**General**: `[Accession]`, `[Title]`, `[Author]`, `[Organism]`,
`[Entry Type]` (e.g. `Expression profiling by array`), `[Platform]`,
`[PubMed ID]`.
**Study type**: `[DataSet Type]` (e.g. `RNA-seq`, `ChIP-seq`), `[Sample Type]`.
**Dates**: `[Publication Date]`, `[Submission Date]`, `[Modification Date]`
(`YYYY` or `YYYY/MM/DD`, ranges with `:`).
**MeSH**: `[MeSH Terms]`, `[MeSH Major Topic]`.

```python
term = ("(breast cancer[MeSH] OR breast neoplasms[Title]) AND "
        "Homo sapiens[Organism] AND "
        "expression profiling by array[Entry Type] AND "
        "2020:2024[Publication Date] AND GPL570[Platform]")
```

**GEO Profiles** (gene-centric, `db="geoprofiles"`):

```python
term = "TP53[Gene Name] AND Homo sapiens[Organism]"
```

---

## 3. GEOparse — advanced usage

`GEOparse.get_GEO()` downloads (and caches in `destdir`) then parses. Key
parameters (as documented upstream): `geo=` (accession) **or** `filepath=`
(local file), `destdir=`, `how=` (`"full"`/`"quick"`/`"brief"`),
`annotate_gpl=True` (merge platform annotation), `silent=`, `geotype=`.

Parsed object holds: `.metadata` (dict of lists), `.gsms` (dict of samples),
`.gpls` (dict of platforms), `.phenotype_data`. Each sample/platform exposes
`.metadata` and `.table` (a pandas DataFrame).

### Expression matrix, robustly

```python
# Preferred: series-matrix pivot (may be absent for old/seq submissions)
try:
    expr = gse.pivot_samples("VALUE")
except Exception:
    expr = None

if expr is None or expr.empty:            # fall back to per-sample tables
    import pandas as pd
    data = {name: g.table.set_index("ID_REF")["VALUE"]
            for name, g in gse.gsms.items()
            if hasattr(g, "table") and "VALUE" in g.table.columns}
    expr = pd.DataFrame(data)
```

### Probe → gene mapping via platform annotation

```python
gpl = list(gse.gpls.values())[0]
annot = gpl.table                          # columns vary by platform:
# ID, Gene Symbol, Gene Title, GB_ACC, Gene ID (Entrez), RefSeq, UniGene ...

probe_to_gene = dict(zip(annot["ID"], annot["Gene Symbol"]))
gene_to_probes = {}
for probe, gene in probe_to_gene.items():
    if gene and gene != "---":             # '---' / '' mark unmapped probes
        gene_to_probes.setdefault(gene, []).append(probe)
# Multiple probes per gene is normal — collapse by max/mean or keep all.
```

### Parse per-sample characteristics into a dict

```python
def characteristics(gsm):
    out = {}
    for key, vals in gsm.metadata.items():
        if key.startswith("characteristics"):
            for v in (vals if isinstance(vals, list) else [vals]):
                if ":" in v:
                    k, val = v.split(":", 1)
                    out[k.strip()] = val.strip()
    return out
```

### Large series in chunks

```python
def process_in_chunks(gse, chunk=1000):
    samples = list(gse.gsms.keys())
    for i in range(0, len(samples), chunk):
        block = {s: gse.gsms[s].table["VALUE"]
                 for s in samples[i:i+chunk] if hasattr(gse.gsms[s], "table")}
        pd.DataFrame(block).to_csv(f"chunk_{i//chunk}.csv")
```

---

## 4. SOFT file format

SOFT (Simple Omnibus Format in Text) is GEO's primary text format: `^` marks a
section, `!` a metadata key=value, `#` a table-column definition, and
`!*_table_begin` / `!*_table_end` bracket the data table.

**File types**: `GSExxxxx_family.soft.gz` (complete series, can be 100s of MB) ·
`GSExxxxx_series_matrix.txt.gz` (expression matrix + minimal metadata, smaller,
fastest) · `GPLxxxxx.soft` (platform annotation).

Abbreviated structure:

```
^SERIES = GSExxxxx
!Series_title = ...
!Series_type = Expression profiling by array
!Series_sample_id = GSMxxxxxx
^PLATFORM = GPLxxxxx
!Platform_organism = Homo sapiens
!platform_table_begin
ID    GB_ACC    Gene Symbol    Gene Title
1007_s_at    U48705    DDR1    discoidin domain receptor...
!platform_table_end
^SAMPLE = GSMxxxxxx
!Sample_source_name_ch1 = cell line XYZ
!Sample_characteristics_ch1 = treatment: control
!Sample_data_processing = RMA normalization
!sample_table_begin
ID_REF    VALUE
1007_s_at    8.456
!sample_table_end
```

Prefer GEOparse for parsing. A minimal manual parser, if you must:

```python
import gzip

def parse_soft(path):
    sections, section, meta, table, in_table = {}, None, {}, [], False
    with gzip.open(path, "rt") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("^"):
                if section:
                    sections[section] = {"metadata": meta, "table": table}
                section, meta, table, in_table = line[1:].split(" = ")[-1], {}, [], False
            elif line.startswith("!"):
                in_table = False
                kv = line[1:].split(" = ", 1)
                if len(kv) == 2:
                    k, v = kv
                    meta.setdefault(k, [])
                    (meta[k] if isinstance(meta[k], list) else [meta[k]]).append(v)
            elif line.startswith("#") or in_table:
                in_table = True
                table.append(line)
    if section:
        sections[section] = {"metadata": meta, "table": table}
    return sections
```

---

## 5. MINiML format

MINiML (MIAME Notation in Markup Language) is GEO's XML equivalent of SOFT,
shipped as `GSExxxxx_family.xml.tgz`. Top-level elements are `<Series>`,
`<Platform>`, and `<Sample>`, each with `<Status>` dates, descriptive fields,
and a `<Data-Table>` of `<Column>` definitions plus `<Row>`/`<Cell>` data.
`<Characteristics tag="...">` carries sample annotation; `<Organism taxid="...">`
carries taxonomy. Parse with a real XML parser (`lxml`/`xml.etree`), never regex.

---

## 6. FTP directory scheme

Path pattern replaces the **last three digits** of the accession with `nnn`:

```
Series:    ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE{nnn}nnn/GSE{full}/
Sample:    ftp://ftp.ncbi.nlm.nih.gov/geo/samples/GSM{nnn}nnn/GSM{full}/
Platform:  ftp://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL{nnn}nnn/GPL{full}/
```

Examples: `GSE123456` → `GSE123nnn/GSE123456/`; `GSE1234` → `GSE1nnn/GSE1234/`;
`GSE100001` → `GSE100nnn/GSE100001/`.

Series subdirectories and files:

```
matrix/  GSE123456_series_matrix.txt.gz    # expression + minimal metadata
soft/    GSE123456_family.soft.gz          # full series (metadata + tables)
miniml/  GSE123456_family.xml.tgz          # XML equivalent
suppl/   GSE123456_RAW.tar, filelist.txt, ...   # raw / supplementary files
```

Platforms additionally carry `annot/GPLxxxxx.annot.gz` (enhanced annotation)
when available. Downloads:

```bash
wget ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE123nnn/GSE123456/matrix/GSE123456_series_matrix.txt.gz
wget -r -np -nd ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE123nnn/GSE123456/suppl/   # all suppl
```

Python FTP client (`ftplib`): construct the path from the accession, `login()`
anonymously, `cwd()`, then `retrbinary("RETR <file>", fh.write)`.

---

## 7. Downstream analysis (examples)

This skill delivers a clean matrix; do serious statistics with `statsmodels` /
`scikit-learn`. Minimal illustrations:

**QC / log-transform decision:**

```python
import numpy as np
if expr.isnull().values.any():
    print("missing:", int(expr.isnull().sum().sum()))
if expr.min().min() > 0 and expr.max().max() > 100:   # looks un-logged
    expr = np.log2(expr + 1)
```

**Simple differential expression (t-test + BH FDR):**

```python
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ctrl, treat = ["GSM1", "GSM2", "GSM3"], ["GSM4", "GSM5", "GSM6"]
rows = []
for gene in expr.index:
    c, t = expr.loc[gene, ctrl], expr.loc[gene, treat]
    tstat, p = stats.ttest_ind(t, c)
    rows.append({"gene": gene, "log2fc": t.mean() - c.mean(), "p": p})
de = pd.DataFrame(rows)
de["q"] = multipletests(de["p"], method="fdr_bh")[1]
sig = de[(de["q"] < 0.05) & (de["log2fc"].abs() > 1)]
```

**Sample correlation / clustering:** `expr.corr()` for a sample-sample heatmap;
`scipy.cluster.hierarchy.linkage(pdist(expr.T, metric="correlation"))` for a
dendrogram. GEO2R (`https://www.ncbi.nlm.nih.gov/geo/geo2r/?acc=GSExxxxx`) does
this in-browser and emits an R script if you want a no-code first pass.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| GEOparse download times out | Network / NCBI hiccup | Retry; or `wget` the file over FTP and parse with `get_GEO(filepath=...)`. |
| `pivot_samples()` empty/errors | No series-matrix file (old or seq submission) | Build from per-sample `.table` (section 3). |
| Probe IDs differ across samples | Mixed platform versions / processing | Reindex every sample onto the union of probe IDs before concatenating. |
| HTTP 429 from E-utilities | Rate limit exceeded | Get an API key (10 req/s); sleep `0.1`s (key) / `0.34`s (none); retry with backoff. |
| `MemoryError` on a big matrix | float64 dense matrix | Use `float32`, read only needed columns, or `scipy.sparse` for mostly-zero data. |
| NCBI blocks your requests | `Entrez.email` unset | Always set it; add an API key for heavy use. |

---

## 9. Platform-specific notes

- **Affymetrix**: probe IDs like `1007_s_at`, suffixes `_at`/`_s_at`/`_x_at`;
  many probe sets per gene; often needs RMA/MAS5 normalization.
- **Illumina**: probe IDs like `ILMN_1234567`; watch duplicate probes and
  BeadChip-specific processing.
- **RNA-seq**: no classic "probes" — expect gene IDs (Ensembl/Entrez) and either
  raw counts or FPKM/TPM; count matrices often live only in `suppl/`.
- **Two-channel arrays**: `_ch1`/`_ch2` suffixes; `VALUE_ch1`/`VALUE_ch2`; decide
  ratio vs intensity and watch for dye-swap designs.

---

## 10. Good practice

Set `Entrez.email` (and an API key for volume) · cache locally and reuse ·
inspect scale/normalization before analysis · verify platform annotation is
current (genes get renamed, IDs deprecated) · watch batch effects in
cross-study meta-analysis and validate on an independent cohort · cite the
original study **and** Barrett et al. (2013, *Nucleic Acids Research*) for GEO.
