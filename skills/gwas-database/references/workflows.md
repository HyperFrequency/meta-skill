# GWAS Catalog Workflows

End-to-end recipes for the common GWAS Catalog tasks, with complete paginated
Python. For raw endpoint specs and field tables see
[api_reference.md](api_reference.md). All examples use the open REST APIs — no
key required.

## Contents

- [Reusable query class](#reusable-query-class)
- [Workflow 1 — disease to variant list](#workflow-1--disease-to-variant-list)
- [Workflow 2 — variant to pleiotropy](#workflow-2--variant-to-pleiotropy)
- [Workflow 3 — gene-centric analysis](#workflow-3--gene-centric-analysis)
- [Workflow 4 — systematic review](#workflow-4--systematic-review)
- [Workflow 5 — summary statistics](#workflow-5--summary-statistics)

## Reusable query class

A small client that handles pagination, p-value filtering, and rate limiting.
Reuse it across the workflows below.

```python
import requests
import pandas as pd
from time import sleep

class GWASCatalog:
    def __init__(self):
        self.base = "https://www.ebi.ac.uk/gwas/rest/api"
        self.headers = {"Content-Type": "application/json"}

    def trait_associations(self, efo_id, p_threshold=5e-8, delay=0.1):
        """All associations for a trait, filtered to p <= p_threshold."""
        url = f"{self.base}/efoTraits/{efo_id}/associations"
        rows, page = [], 0
        while True:
            r = requests.get(url, params={"page": page, "size": 100},
                             headers=self.headers)
            if r.status_code != 200:
                break
            items = r.json().get("_embedded", {}).get("associations", [])
            if not items:
                break
            for a in items:
                p = a.get("pvalue")
                if p and float(p) <= p_threshold:
                    rows.append({
                        "rs_id": a.get("rsId"),
                        "pvalue": float(p),
                        "risk_allele": a.get("strongestAllele"),
                        "or_beta": a.get("orPerCopyNum") or a.get("betaNum"),
                        "trait": a.get("efoTrait"),
                        "study": a.get("studyId"),
                        "pubmed_id": a.get("pubmedId"),
                    })
            page += 1
            sleep(delay)
        return pd.DataFrame(rows)

    def variant(self, rs_id):
        r = requests.get(f"{self.base}/singleNucleotidePolymorphisms/{rs_id}",
                         headers=self.headers)
        return r.json() if r.status_code == 200 else None

    def gene_variants(self, gene_name):
        r = requests.get(
            f"{self.base}/singleNucleotidePolymorphisms/search/findByGene",
            params={"geneName": gene_name}, headers=self.headers)
        return r.json() if r.status_code == 200 else None
```

## Workflow 1 — disease to variant list

Goal: every genome-wide-significant variant for a disease, ready for downstream
annotation or a PRS candidate list.

1. **Resolve the EFO term.** Search the web interface or
   `efoTraits/search/findByTraitIgnoreCase` to turn "type 2 diabetes" into
   `EFO_0001360`. Do this first — free text is ambiguous.
2. **Page through associations** and filter to p ≤ 5×10⁻⁸.
3. **Extract** rs IDs, effect alleles, effect sizes (OR or beta).
4. **Cross-reference** consequences in Ensembl (VEP) and allele frequencies in
   gnomAD; hand off to the PGS Catalog for pre-built polygenic scores.

```python
gwas = GWASCatalog()
df = gwas.trait_associations("EFO_0001360")
print(f"{len(df)} associations, {df['rs_id'].nunique()} unique variants")
print(df.nsmallest(10, "pvalue")[["rs_id", "pvalue", "risk_allele"]])
```

## Workflow 2 — variant to pleiotropy

Goal: understand what one SNP does across phenotypes.

1. **Get variant details** — location, nearby genes, functional class.
2. **Get all trait associations** with `projection=associationBySnp`.
3. **Summarize pleiotropy** — collapse to the best p-value per trait; look for
   shared biology and effect-direction consistency.

```python
rs = "rs7903146"
info = gwas.variant(rs)
loc = (info.get("locations") or [{}])[0]
print(f"{rs}: chr{loc.get('chromosomeName')}:{loc.get('chromosomePosition')}")

base = "https://www.ebi.ac.uk/gwas/rest/api"
data = requests.get(f"{base}/singleNucleotidePolymorphisms/{rs}/associations",
                    params={"projection": "associationBySnp"}).json()
best = {}
for a in data.get("_embedded", {}).get("associations", []):
    t, p = a.get("efoTrait"), a.get("pvalue")
    if t and (t not in best or float(p) < float(best[t])):
        best[t] = p
for t, p in sorted(best.items(), key=lambda kv: float(kv[1])):
    print(f"{t}: p={p}")
```

## Workflow 3 — gene-centric analysis

Goal: the association landscape around a gene.

1. **Find variants for the gene** via `findByGene`, or get the gene's
   coordinates and use `findByChromBpLocationRange` — extend the window to
   include promoter / regulatory regions.
2. **Aggregate** which traits the variants hit and how consistently across
   studies.
3. **Interpret functionally** — consequence class, eQTL evidence (external),
   pathway context.

```python
variants = gwas.gene_variants("TCF7L2")
# then, for coordinate-based queries, extend boundaries and use:
# GET /singleNucleotidePolymorphisms/search/findByChromBpLocationRange
```

## Workflow 4 — systematic review

Goal: a defensible, reproducible synthesis of the genetic evidence for a
phenotype.

1. **Define the question** — trait(s), populations, study-design constraints.
2. **Comprehensive extraction** — all associations for the trait at a stated
   threshold; record discovery vs. replication studies.
3. **Quality assessment** — sample sizes, ancestry diversity, replication,
   cross-study heterogeneity, potential biases (winner's curse, ascertainment,
   study overlap when combining).
4. **Synthesis** — aggregate across studies, meta-analyse where appropriate,
   build summary tables and Manhattan / forest plots.
5. **Document** — export full association data and any summary statistics, and
   **record the search strategy and access date** for reproducibility (the
   catalog updates continuously).

## Workflow 5 — summary statistics

Goal: full genome-wide data (all tested variants) for fine-mapping,
colocalization, LD score regression, or Mendelian randomization.

1. **Find deposited studies** — browse the summary-statistics portal, list the
   FTP tree, or query `GET /studies` on the Summary Statistics API.
2. **Bulk download via FTP** (preferred for whole-genome data) — the harmonised
   file is standardized across studies:

   ```bash
   wget http://ftp.ebi.ac.uk/pub/databases/gwas/summary_statistics/\
   GCSTXXXXXX/harmonised/GCSTXXXXXX-harmonised.tsv.gz
   ```

   Or in Python, streaming to disk with a fallback when no harmonised file
   exists:

   ```python
   from pathlib import Path

   def download_sumstats(gcst_id, out_dir="."):
       ftp = "http://ftp.ebi.ac.uk/pub/databases/gwas/summary_statistics"
       url = f"{ftp}/{gcst_id}/harmonised/{gcst_id}-harmonised.tsv.gz"
       dest = Path(out_dir) / f"{gcst_id}.tsv.gz"
       r = requests.get(url, stream=True)
       if r.status_code != 200:
           print(f"No harmonised file for {gcst_id} (HTTP {r.status_code})")
           return None
       with open(dest, "wb") as fh:
           for chunk in r.iter_content(chunk_size=8192):
               fh.write(chunk)
       return dest
   ```

3. **Query targeted slices via the API** instead of downloading, when you only
   need a region or a p-value tranche:

   ```python
   ss = "https://www.ebi.ac.uk/gwas/summary-statistics/api"
   r = requests.get(f"{ss}/chromosomes/10/associations",
                    params={"start": 114000000, "end": 115000000,
                            "p_upper": "0.00000005", "size": 1000})
   ```

4. **Analyze** — filter by p-value, extract `beta` / `standard_error` /
   `effect_allele_frequency`, then feed downstream tools (fine-mapping,
   colocalization, MR). Remember Summary Statistics fields are snake_case.
