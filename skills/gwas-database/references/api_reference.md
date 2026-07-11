# GWAS Catalog API Reference

Endpoint specifications, query parameters, response layouts, and error handling
for the two GWAS Catalog REST services. Endpoint paths follow the long-standing
patterns; the Catalog REST API was re-versioned (v2) in 2024, so verify the exact
path and response field names against the live interactive docs at
`https://www.ebi.ac.uk/gwas/rest/docs/api` before hard-coding them.

## Contents

- [Overview and base URLs](#overview-and-base-urls)
- [Authentication and rate limiting](#authentication-and-rate-limiting)
- [Catalog REST API](#catalog-rest-api)
- [Summary Statistics API](#summary-statistics-api)
- [Response format (HAL) and pagination](#response-format-hal-and-pagination)
- [Error handling](#error-handling)
- [Advanced and cross-API patterns](#advanced-and-cross-api-patterns)

## Overview and base URLs

Two complementary services, both returning JSON:

```
Catalog REST API:        https://www.ebi.ac.uk/gwas/rest/api
Summary Statistics API:  https://www.ebi.ac.uk/gwas/summary-statistics/api
```

- **Catalog REST API** — curated SNP-trait associations, studies, variants,
  traits, genes, publications. Responses use HAL (`_embedded`, `_links`, `page`).
- **Summary Statistics API** — full summary statistics (every tested variant) for
  studies that deposited complete data; filter by trait, chromosome, region, and
  p-value.

Send `Content-Type: application/json` on Catalog API requests.

## Authentication and rate limiting

No authentication — both APIs are open, no key, no registration. No hard rate
limit is published, but be considerate: add a 0.1–0.5 s delay between calls,
paginate large result sets, cache locally, and prefer FTP for genome-wide data.

```python
import requests
from time import sleep

def get_json(url, params=None, delay=0.1):
    r = requests.get(url, params=params,
                     headers={"Content-Type": "application/json"}, timeout=30)
    sleep(delay)
    return r
```

## Catalog REST API

### Studies

```
GET /studies                                          # all studies (paginated)
GET /studies/{accessionId}                            # one study, e.g. GCST001795
GET /studies/search/findByPublicationIdPubmedId?pubmedId={pmid}
GET /studies/search/findByDiseaseTrait?diseaseTrait={trait}
```

Common study fields: `accessionId`, `title`, `publicationInfo` (contains
`pubmedId`, author, date), `initialSampleSize`, `replicationSampleSize`,
`ancestries`, `genotypingTechnologies`, `_links`.

### Associations

```
GET /associations                                     # all associations
GET /associations/{associationId}                     # one association
GET /efoTraits/{efoId}/associations                   # associations for a trait
GET /singleNucleotidePolymorphisms/{rsId}/associations# associations for a variant
```

Useful params: `projection=associationBySnp` (flattens per-SNP view), plus
`page` / `size` / `sort`.

Association fields: `rsId`, `strongestAllele`, `pvalue`, `pvalueText` (as
reported, may include an inequality), `pvalueMantissa`, `pvalueExponent`,
`orPerCopyNum` (odds ratio per allele copy), `betaNum` + `betaUnit` (quantitative
effect), `range` (CI), `standardError`, `efoTrait`, `mappedLabel` (EFO term),
`studyId`.

### Variants (SNPs)

```
GET /singleNucleotidePolymorphisms/{rsId}
GET /singleNucleotidePolymorphisms/search/findByRsId?rsId={rsId}
GET /singleNucleotidePolymorphisms/search/findByChromBpLocationRange?chrom={c}&bpStart={s}&bpEnd={e}
GET /singleNucleotidePolymorphisms/search/findByGene?geneName={symbol}
```

Variant fields: `rsId`, `merged`, `functionalClass` (consequence), `locations[]`
(each with `chromosomeName`, `chromosomePosition`, `region`), `genomicContexts`
(nearby genes), `lastUpdateDate`.

### Traits (EFO)

```
GET /efoTraits/{efoId}                                # e.g. EFO_0001360
GET /efoTraits/search/findByEfoUri?uri={efoUri}
GET /efoTraits/search/findByTraitIgnoreCase?trait={traitName}
```

Trait fields: `trait` (label), `uri` (EFO URI), `shortForm`.

### Publications and Genes

```
GET /publications
GET /publications/{publicationId}
GET /publications/search/findByPubmedId?pubmedId={pmid}

GET /genes
GET /genes/{geneId}
GET /genes/search/findByGeneName?geneName={symbol}
```

### Following HAL links

Responses embed `_links` to related resources; follow them instead of
re-constructing URLs:

```python
study = get_json("https://www.ebi.ac.uk/gwas/rest/api/studies/GCST001795").json()
assoc = requests.get(study["_links"]["associations"]["href"]).json()
```

## Summary Statistics API

### Studies

```
GET /studies                    # studies that have summary statistics
GET /studies/{gcstId}
```

### Traits

```
GET /traits/{efoId}
GET /traits/{efoId}/associations
```

Params: `p_lower`, `p_upper` (p-value bounds, pass as decimal strings, e.g.
`"0.00000005"` for 5×10⁻⁸), `size`, `page`.

### Chromosomes / regions

```
GET /chromosomes/{chromosome}/associations
GET /chromosomes/{chromosome}/associations?start={start}&end={end}
```

### Variants

```
GET /variants/{variantId}
GET /variants/{variantId}/associations
```

Summary Statistics fields (snake_case): `variant_id`, `chromosome`,
`base_pair_location`, `effect_allele`, `other_allele`,
`effect_allele_frequency`, `beta`, `standard_error`, `p_value`, `ci_lower`,
`ci_upper`, `odds_ratio`, `study_accession`.

## Response format (HAL) and pagination

Catalog list endpoints return HAL:

```json
{
  "_embedded": { "associations": [ { "rsId": "rs7903146", "pvalue": 1.2e-30,
                                     "efoTrait": "type 2 diabetes" } ] },
  "_links": {
    "self": { "href": ".../efoTraits/EFO_0001360/associations?page=0" },
    "next": { "href": ".../efoTraits/EFO_0001360/associations?page=1" }
  },
  "page": { "size": 20, "totalElements": 1523, "totalPages": 77, "number": 0 }
}
```

`page` gives `size`, `totalElements`, `totalPages`, `number` (0-indexed). Default
page size is 20; raise it with `size` (e.g. 100) and loop `page` until
`_embedded` is empty or `number == totalPages - 1`.

```python
def get_all(url, key, size=100):
    out, page = [], 0
    while True:
        r = requests.get(url, params={"page": page, "size": size},
                         headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            break
        items = r.json().get("_embedded", {}).get(key, [])
        if not items:
            break
        out.extend(items)
        page += 1
    return out
```

## Error handling

HTTP status codes: `200` OK, `400` bad parameters, `404` not found, `500` server
error. Error body:

```json
{ "timestamp": "2025-10-19T12:00:00.000+00:00", "status": 404,
  "error": "Not Found", "message": "No association found with id: 12345",
  "path": "/gwas/rest/api/associations/12345" }
```

```python
def safe_get(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP {r.status_code}: {e} — {r.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("Connection error")
    except requests.exceptions.Timeout:
        print("Timed out")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    return None
```

## Advanced and cross-API patterns

### Variant pleiotropy (all traits for a SNP)

```python
def variant_pleiotropy(rs_id):
    base = "https://www.ebi.ac.uk/gwas/rest/api"
    data = requests.get(f"{base}/singleNucleotidePolymorphisms/{rs_id}/associations",
                        params={"projection": "associationBySnp"},
                        headers={"Content-Type": "application/json"}).json()
    best = {}
    for a in data.get("_embedded", {}).get("associations", []):
        trait, p = a.get("efoTrait"), a.get("pvalue")
        if trait and (trait not in best or float(p) < float(best[trait])):
            best[trait] = p
    return best
```

### Filter a trait's associations by p-value

```python
def significant_for_trait(efo_id, p_threshold=5e-8):
    url = f"https://www.ebi.ac.uk/gwas/rest/api/efoTraits/{efo_id}/associations"
    return [a for a in get_all(url, "associations")
            if a.get("pvalue") and float(a["pvalue"]) <= p_threshold]
```

### Region query across both APIs

```python
def query_region(chrom, start, end, p_upper=None):
    cat = requests.get(
        "https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/"
        "search/findByChromBpLocationRange",
        params={"chrom": chrom, "bpStart": start, "bpEnd": end, "size": 1000},
        headers={"Content-Type": "application/json"}).json()
    ss_params = {"start": start, "end": end, "size": 1000}
    if p_upper:
        ss_params["p_upper"] = str(p_upper)
    ss = requests.get(
        f"https://www.ebi.ac.uk/gwas/summary-statistics/api/chromosomes/{chrom}/associations",
        params=ss_params).json()
    return {"catalog_variants": cat, "summary_stats": ss}
```

## External resources

- Interactive API docs — https://www.ebi.ac.uk/gwas/rest/docs/api
- Summary Statistics API docs — https://www.ebi.ac.uk/gwas/summary-statistics/docs/
- REST API v2 release notes — https://ebispot.github.io/gwas-blog/rest-api-v2-release/
- Workshop materials — https://github.com/EBISPOT/GWAS_Catalog-workshop
- `gwasrapidd` R package — https://cran.r-project.org/package=gwasrapidd
