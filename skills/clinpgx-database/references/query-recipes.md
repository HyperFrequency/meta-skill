# ClinPGx Query Recipes

Reusable request helpers and end-to-end workflows for the ClinPGx v1 REST API.
Endpoint details are in [api-reference.md](api-reference.md). All examples use
`requests`; add `pandas` where noted.

## Rate-limited, retrying, cached request helper

The API caps at ~2 requests/second. Route every call through one wrapper so rate
limiting, backoff, and timeouts are consistent.

```python
import json
import time
from pathlib import Path
import requests

BASE_URL = "https://api.clinpgx.org/v1/"
RATE_LIMIT_DELAY = 0.5  # ~2 req/s

def api_get(path, params=None, max_retries=3):
    """GET {BASE_URL}{path} with rate limiting, 429 backoff, and 404 -> None.

    Returns parsed JSON, or None if the resource is absent or all retries fail.
    """
    url = f"{BASE_URL}{path}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                time.sleep(RATE_LIMIT_DELAY)   # be a good citizen after success
                return resp.json()
            if resp.status_code == 404:
                return None                     # absent, not an error
            if resp.status_code == 429:
                wait = 2 ** attempt             # 1s, 2s, 4s
                print(f"429 rate limited; waiting {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"attempt {attempt + 1}/{max_retries} failed: {exc}")
            if attempt == max_retries - 1:
                return None
            time.sleep(1)
    return None
```

### Disk cache

Allele functions and guidelines change slowly; cache them.

```python
def cached(cache_file, fetch, *args, **kwargs):
    path = Path(cache_file)
    if path.exists():
        return json.loads(path.read_text())
    result = fetch(*args, **kwargs)
    if result is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2))
    return result

cyp2d6 = cached("cache/cyp2d6.json", api_get, "gene/CYP2D6")
```

### Thin typed accessors

```python
def get_gene(symbol):            return api_get(f"gene/{symbol}")
def search_drug(name):           return api_get("chemical", {"name": name})
def gene_drug_pairs(gene=None, drug=None, cpic=None):
    params = {k: v for k, v in
              {"gene": gene, "drug": drug, "cpicLevel": cpic}.items() if v}
    return api_get("geneDrugPair", params)
def guidelines(gene=None, drug=None, source="CPIC"):
    params = {k: v for k, v in
              {"gene": gene, "drug": drug, "source": source}.items() if v}
    return api_get("guideline", params)
def alleles(gene):               return api_get("allele", {"gene": gene})
def clinical_annotations(gene=None, drug=None, level=None):
    params = {k: v for k, v in
              {"gene": gene, "drug": drug, "evidenceLevel": level}.items() if v}
    return api_get("clinicalAnnotation", params)
def drug_labels(drug, source=None):
    params = {"drug": drug}
    if source: params["source"] = source
    return api_get("drugLabel", params)
```

Guard every result — endpoints may return `None` (404), a dict, or a list.

## Workflow 1 — Clinical decision support for one prescription

Diplotype in hand, decide whether/how to prescribe.

```python
# 1. Allele functions for the patient's diplotype (e.g. CYP2C19 *1/*2)
star2 = api_get("allele/CYP2C19*2")   # 'no function' -> contributes to IM/PM

# 2. Is this gene-drug pair actionable?
pair = gene_drug_pairs(gene="CYP2C19", drug="clopidogrel")

# 3. CPIC recommendation for the resulting phenotype
gl = guidelines(gene="CYP2C19", drug="clopidogrel")
# e.g. IM/PM -> use an alternative antiplatelet (prasugrel/ticagrelor)

# 4. Cross-check regulatory labeling
label = drug_labels("clopidogrel", source="FDA")
```

Map the two allele activity scores to a phenotype, then read the guideline's
per-phenotype recommendation — do not read a recommendation off the allele
alone.

## Workflow 2 — PGx panel analysis

Which drugs does a patient's panel touch, at guideline strength?

```python
panel = ["CYP2C19", "CYP2D6", "CYP2C9", "TPMT", "DPYD", "SLCO1B1", "NUDT15"]

actionable = []
for gene in panel:
    for pair in (gene_drug_pairs(gene=gene) or []):
        if pair.get("cpicLevel") in {"A", "B"}:
            actionable.append((gene, pair.get("drug"), pair["cpicLevel"]))

for gene, drug, level in sorted(actionable):
    print(f"CPIC {level}: {gene} - {drug}")
```

To design the panel itself (rather than analyze one), enumerate all Level-A
pairs and take the union of genes:

```python
level_a = gene_drug_pairs(cpic="A") or []
must_cover = sorted({p["gene"] for p in level_a})
```

## Workflow 3 — Drug-safety / HLA screening

```python
# HLA-B*57:01 contraindicates abacavir
pair = (gene_drug_pairs(gene="HLA-B", drug="abacavir") or [{}])[0]
if pair.get("cpicLevel") == "A":
    print("Screen HLA-B*57:01; do NOT prescribe abacavir if positive")

# Toxicity-linked annotations for a drug
for ann in (clinical_annotations(drug="abacavir") or []):
    if "HLA" in "".join(ann.get("genes", []) or []):
        print(ann["phenotype"], ann["evidenceLevel"])
```

High-value safety pairs to know: `HLA-B*57:01`/abacavir,
`HLA-B*15:02`/carbamazepine, `DPYD`/fluoropyrimidines, `TPMT` & `NUDT15`/
thiopurines, `CYP2D6`/codeine (avoid in UM).

## Workflow 4 — Population frequency analysis

```python
data = alleles("CYP2D6") or []

# Sum 'no function' allele frequencies as a crude PM-allele burden per population
pm_burden = {}
for a in data:
    if a.get("function") == "No function":
        for pop, freq in (a.get("frequencies") or {}).items():
            pm_burden[pop] = pm_burden.get(pop, 0.0) + float(freq)

for pop, f in sorted(pm_burden.items(), key=lambda kv: -kv[1]):
    print(f"{pop}: no-function allele freq ~{f:.2f}")
```

This is an allele-frequency sum, not a Hardy-Weinberg phenotype prediction —
derive true diplotype/phenotype frequencies from paired allele frequencies, and
never transfer one population's distribution to another.

## Workflow 5 — Literature evidence review

```python
anns = clinical_annotations(gene="TPMT", drug="azathioprine") or []
strong = [a for a in anns if a.get("evidenceLevel") in {"1A", "1B", "2A"}]
pmids = sorted({a["pmid"] for a in strong if a.get("pmid")})
# Hand pmids to `citation-management` to format references.
```

## Export to a DataFrame

```python
import pandas as pd

pairs = gene_drug_pairs(gene="CYP2D6") or []
df = pd.DataFrame(pairs)
df.to_csv("cyp2d6_pairs.csv", index=False)
```

## Batch with backoff

```python
def batch_genes(symbols):
    out = {}
    for sym in symbols:
        data = api_get(f"gene/{sym}")   # already rate-limited internally
        if data:
            out[sym] = data
    return out
```

Keep batches small and cached; for whole-database work use the ClinPGx data
dumps rather than looping the API.
