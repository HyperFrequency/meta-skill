# Gene Database — Worked Workflows

End-to-end recipes for NCBI Gene. Every example uses the **correct field tags**
(full list in `eutils-api.md`) and the **v2** Datasets endpoints
(`datasets-api.md`). No helper scripts are assumed — everything is `curl` or
Biopython `Entrez`, so wrap it in whatever driver you like.

Before running any of these:

- Set contact info: `&email=you@example.com&tool=<name>` on E-utilities URLs, or
  `Entrez.email = "..."` in Biopython. NCBI emails you before blocking.
- Pass your key for 10 req/s: `&api_key=<KEY>` (E-utilities) or the
  `api-key: <KEY>` header (Datasets). Serialize calls (~0.34 s apart without a
  key, ~0.1 s with one).
- **Always read back `esearchresult.querytranslation`** to confirm your tags were
  honoured and not silently rewritten to `[All Fields]`.

A tiny helper used throughout:

```python
import json, time, urllib.parse, urllib.request
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def eget(endpoint, **params):
    params.setdefault("db", "gene")
    url = f"{EUTILS}{endpoint}.fcgi?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode()
        except Exception:
            if attempt == 3: raise
            time.sleep(2 ** attempt)      # 1s, 2s, 4s back-off

def esearch(term, retmax=100):
    data = json.loads(eget("esearch", term=term, retmode="json", retmax=retmax))
    res = data["esearchresult"]
    return res["idlist"], res.get("querytranslation", "")  # inspect the translation

def esummary(ids):
    data = json.loads(eget("esummary", id=",".join(ids), retmode="json"))
    return data.get("result", {})
```

---

## 1. Disease / phenotype gene discovery

Find genes annotated to a disease. Use `[Disease/Phenotype]` — **not** the
free-text `[disease]`, which rewrites to `[All Fields]` and inflates the hit
count with any record that merely mentions the word.

```python
ids, qt = esearch("Alzheimer disease[Disease/Phenotype] AND human[Organism]", retmax=50)
print("translated as:", qt)                 # verify the tag survived
res = esummary(ids)
for gid in ids:
    g = res.get(gid, {})
    print(gid, g.get("name"), "-", g.get("description"),
          f"(chr{g.get('chromosome')} {g.get('maplocation')})")
```

Narrow with a second criterion — e.g. genes on chromosome 17 tied to breast
cancer:

```python
ids, _ = esearch("breast cancer[Disease/Phenotype] AND 17[Chromosome] AND human[Organism]")
```

Output: a symbol/description/location table you can filter or hand downstream.
To turn the linked publications into citations, see recipe 6.

---

## 2. Gene annotation pipeline (symbols → table)

Annotate a list of symbols with stable Gene IDs and metadata. Resolve each
symbol to an ID first (batching the *summaries*, not the searches — esearch is
one symbol per call).

`genes.txt`:

```
BRCA1
TP53
EGFR
KRAS
```

```python
symbols = [s.strip() for s in open("genes.txt") if s.strip()]

symbol_to_id = {}
for sym in symbols:
    ids, _ = esearch(f"{sym}[Gene Name] AND human[Organism]", retmax=1)
    symbol_to_id[sym] = ids[0] if ids else None
    time.sleep(0.34)                         # rate limit without a key

valid = [gid for gid in symbol_to_id.values() if gid]
res = esummary(valid)                        # one call, up to ~500 IDs

rows = []
for sym, gid in symbol_to_id.items():
    if not gid:
        rows.append({"query": sym, "status": "not_found"}); continue
    g = res.get(gid, {})
    rows.append({
        "query": sym, "gene_id": gid, "symbol": g.get("name"),
        "description": g.get("description"),
        "organism": g.get("organism", {}).get("scientificname"),
        "chromosome": g.get("chromosome"), "map_location": g.get("maplocation"),
        "aliases": g.get("otheraliases"),
    })
json.dump(rows, open("annotations.json", "w"), indent=2)
```

For a *richer* report (RefSeq transcripts, protein accessions, Ensembl IDs) pull
the same IDs from Datasets instead of `esummary`:

```bash
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/672,7157,1956,3845"
# reports[].gene.transcripts[], .swiss_prot_accessions, .ensembl_gene_ids
```

Uses: annotation tables for papers, validating gene panels before analysis,
building a local reference. Prefer the integer **Gene ID** as the join key —
symbols are ambiguous across species and change over time.

---

## 3. Cross-species orthologs

Two reliable paths; pick by how authoritative you need the ortholog call to be.

**A. Per-species symbol lookup (quick, exact IDs).** The same symbol in each
organism — good enough when the symbol is conserved:

```bash
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/TP53/taxon/human"
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/Trp53/taxon/mouse"
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/symbol/tp53/taxon/zebrafish"
```

Note casing conventions differ (human `TP53`, mouse `Trp53`) — symbol equality
is *not* a substitute for a real ortholog relationship.

**B. Curated ortholog group.** `elink` to HomoloGene gives a curated group:

```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=gene&db=homologene&id=7157&retmode=json"
```

Caveat: **HomoloGene is a legacy resource NCBI no longer updates.** For current,
comprehensive orthology use the sibling `ensembl-database` homology endpoint
(`GET /homology/id/{ensembl_id}`) or `gget ortholog` — get the Ensembl gene ID
from the Datasets report's `ensembl_gene_ids`, then hand off.

Applications: comparative genomics, model-organism design, evolutionary studies.

---

## 4. Function / GO search

Search by Gene Ontology **term name**, not GO ID — the `[Gene Ontology]` field is
indexed by name, so `GO:0006915[biological process]` matches nothing useful.

```python
ids, qt = esearch("apoptosis[Gene Ontology] AND human[Organism]", retmax=100)
print(qt)                                    # confirm "apoptosis[Gene Ontology]"
```

**NCBI Gene has no pathway field.** `insulin signaling pathway[pathway]` silently
free-text matches. For real pathway membership, either search loosely with
`[Text Word]` and post-filter, or use a dedicated pathway resource — the sibling
`kegg-database` or `reactome-database` skills. To fetch details for a known set
of pathway member genes, feed their IDs straight to Datasets or `esummary`:

```bash
curl "https://api.ncbi.nlm.nih.gov/datasets/v2/gene/id/5594,5595,5604,5605"  # MAPK members
```

Restrict to protein-coding via the controlled `[Properties]` value:

```python
ids, _ = esearch("apoptosis[Gene Ontology] AND genetype protein coding[Properties] AND human[Organism]")
```

---

## 5. Variant linkage (gene → ClinVar / dbSNP)

Gene is the hub; jump to variant databases with `elink`. Interpret pathogenicity
in `clinvar-database`, not here.

```bash
# Clinical variants for BRCA1 (Gene ID 672)
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=gene&db=clinvar&id=672&retmode=json"

# dbSNP variants for the same gene
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=gene&db=snp&id=672&retmode=json"
```

Extract the linked UIDs (same JSON shape as recipe 6), then query the target
database. `elink` finds the *set* of related records; it does not classify them —
significance, review-status stars, and ACMG calls live in ClinVar.

---

## 6. Publication mining (gene → PubMed)

Link a gene to its literature, then hand the PMIDs to `citation-management` for
formatted references.

```python
raw = eget("elink", dbfrom="gene", db="pubmed", id="672", retmode="json")
data = json.loads(raw)
pmids = []
for ls in data.get("linksets", []):
    for lsdb in ls.get("linksetdbs", []):
        pmids.extend(lsdb.get("links", []))
print(f"BRCA1: {len(pmids)} linked PubMed records")
```

To go the other way — genes mentioned in a body of literature — search the gene
DB by `[Text Word]` (a token in the gene's annotation), understanding it is a
weaker signal than a curated link:

```python
ids, _ = esearch("CRISPR[Text Word] AND human[Organism]", retmax=100)
```

---

## Advanced patterns

### Multi-criteria intersection

Compose independent searches and intersect the ID sets — cheaper and clearer than
one giant boolean term:

```python
disease, _ = esearch("diabetes[Disease/Phenotype] AND human[Organism]", retmax=500)
onchr11, _ = esearch("11[Chromosome] AND human[Organism]", retmax=1000)
coding, _  = esearch("genetype protein coding[Properties] AND human[Organism]", retmax=100000)
candidates = set(disease) & set(onchr11) & set(coding)
```

### Rate-limited batch summaries

Chunk large ID lists (esummary caps at ~500 per call) and pause between chunks:

```python
def batched_summaries(ids, chunk=200, delay=0.34):
    out = {}
    for i in range(0, len(ids), chunk):
        out.update(esummary(ids[i:i + chunk]))
        time.sleep(delay)
    return out
```

For very large sets, prefer `usehistory=y` on the esearch and page through the
server-side result with `WebEnv` + `query_key` (see `eutils-api.md`) rather than
posting a huge `id=` list.

### Robust single fetch

The `eget` helper already retries `429`/`5xx`/timeouts with exponential back-off.
Also guard against E-utilities' **HTTP-200-with-error-body**: a malformed term can
return `200` with `{"error": ...}` (JSON) or `<ERROR>...</ERROR>` (XML). Check the
body, not just the status code.

---

## Tips

1. Start specific, broaden only if empty. A wrong tag over-returns; a right tag
   that returns nothing is genuine absence.
2. Always filter by organism for symbol searches — symbols collide across taxa.
3. Carry the integer Gene ID through your whole pipeline; symbols drift.
4. Cache stable lookups; Gene annotations change only on reannotation.
5. Search with E-utilities, fetch structured reports with Datasets — combine, do
   not pick one for everything.
