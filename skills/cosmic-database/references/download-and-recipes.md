# COSMIC Download and Analysis Recipes

Extended download helper, a data-type shortcut table, load/filter recipes, and
troubleshooting. The main SKILL.md carries the minimal version; this file is the
depth.

## The two-step authenticated download

COSMIC file downloads are a **two-step** protocol, not a single authenticated
GET:

1. **Authenticated request** to the `file_download/` endpoint with your account
   credentials (HTTP Basic auth over `email:password`). The endpoint responds
   with JSON containing a short-lived, signed object-store URL — it does **not**
   stream the file.
2. **Unauthenticated GET** of that signed URL to stream the actual bytes.

The signed URL expires quickly (typically about an hour), so fetch and use it in
one run rather than caching it.

> Caveat: COSMIC has revised its access mechanism across releases (basic-auth
> tokens, license-acceptance gates, token headers). The two-step flow below is
> the long-documented form; if a request 401s or returns HTML, re-check the
> current download instructions on the COSMIC site.

```python
import os
import requests


def download_cosmic_file(email, password, filepath, output_filename=None, timeout=300):
    """Download one COSMIC data file via the two-step signed-URL protocol.

    Args:
        email:           registered COSMIC account email.
        password:        COSMIC account password.
        filepath:        release-relative path, e.g.
                         "GRCh38/cosmic/latest/CosmicMutantExport.tsv.gz".
        output_filename: local path to write (defaults to the file's basename).
        timeout:         seconds for the streaming download.

    Returns True on success, False on a handled failure.
    """
    endpoint = "https://cancer.sanger.ac.uk/cosmic/file_download/"
    output_filename = output_filename or os.path.basename(filepath)

    # Step 1: exchange credentials + path for a signed download URL.
    auth_response = requests.get(endpoint + filepath, auth=(email, password), timeout=30)
    if auth_response.status_code == 401:
        print("Authentication failed — check email/password and that the account is registered.")
        return False
    if auth_response.status_code == 404:
        print(f"File not found: {filepath} — verify the path, version, and assembly.")
        return False
    if auth_response.status_code != 200:
        print(f"Request failed ({auth_response.status_code}): {auth_response.text[:200]}")
        return False

    signed_url = auth_response.json().get("url")
    if not signed_url:
        print("No signed URL in the response — the access protocol may have changed.")
        return False

    # Step 2: stream the file from the signed URL (no auth on this leg).
    with requests.get(signed_url, stream=True, timeout=timeout) as file_response:
        if file_response.status_code != 200:
            print(f"Download failed ({file_response.status_code}).")
            return False
        total = int(file_response.headers.get("content-length", 0))
        written = 0
        with open(output_filename, "wb") as out:
            for chunk in file_response.iter_content(chunk_size=1 << 16):
                if not chunk:
                    continue
                out.write(chunk)
                written += len(chunk)
                if total:
                    print(f"\r{written / total:6.1%}", end="", flush=True)
        print(f"\nSaved {output_filename} ({written} bytes)")
    return True
```

Security notes:
- Never hard-code the password. Read it from an env var or `getpass.getpass()`.
- COSMIC files run to several GB — check free disk space and stream (as above),
  never `response.content` on the big files.

## Data-type shortcut table

Resolve a friendly name to a legacy file path. Verify the exact filename for your
target release (see the versioning caveat in `data-products.md`).

```python
def cosmic_path(data_type, assembly="GRCh38", version="latest"):
    prefix = f"{assembly}/cosmic/{version}"
    paths = {
        "mutations":            f"{prefix}/CosmicMutantExport.tsv.gz",
        "mutations_census":     f"{prefix}/CosmicMutantExportCensus.tsv.gz",
        "mutations_vcf":        f"{prefix}/VCF/CosmicCodingMuts.vcf.gz",
        "noncoding_vcf":        f"{prefix}/VCF/CosmicNonCodingVariants.vcf.gz",
        "gene_census":          f"{prefix}/cancer_gene_census.csv",
        "structural_variants":  f"{prefix}/CosmicStructExport.tsv.gz",
        "fusion_genes":         f"{prefix}/CosmicFusionExport.tsv.gz",
        "copy_number":          f"{prefix}/CosmicCompleteCNA.tsv.gz",
        "gene_expression":      f"{prefix}/CosmicCompleteGeneExpression.tsv.gz",
        "resistance_mutations": f"{prefix}/CosmicResistanceMutations.tsv.gz",
        "sample_info":          f"{prefix}/CosmicSample.tsv.gz",
        "signatures":           "signatures/signatures.tsv",
    }
    return paths.get(data_type)
```

## Loading and filtering recipes

Read tabular products with pandas (they are gzip-compressed):

```python
import pandas as pd

mutations   = pd.read_csv("CosmicMutantExport.tsv.gz", sep="\t", compression="gzip")
gene_census = pd.read_csv("cancer_gene_census.csv")
```

For files too large to hold in memory, filter in chunks:

```python
tp53 = pd.concat(
    chunk[chunk["Gene name"] == "TP53"]
    for chunk in pd.read_csv("CosmicMutantExport.tsv.gz", sep="\t",
                             compression="gzip", chunksize=500_000)
)
```

**Filter mutations by gene:**
```python
tp53_mutations = mutations[mutations["Gene name"] == "TP53"]
```

**Split the Census by gene role:**
```python
oncogenes         = gene_census[gene_census["Role in Cancer"].str.contains("oncogene", na=False)]
tumor_suppressors = gene_census[gene_census["Role in Cancer"].str.contains("TSG",      na=False)]
tier1             = gene_census[gene_census["Tier"] == 1]
```

**Prioritize a variant table against the Census** (keep only known cancer genes):
```python
known = set(gene_census["Gene Symbol"])
mutations_in_cancer_genes = mutations[mutations["Gene name"].isin(known)]
```

**Slice mutations by cancer type:**
```python
lung = mutations[mutations["Primary site"] == "lung"]
```

**Region query over the VCF** (needs the tabix `.tbi` index):
```python
import pysam

vcf = pysam.VariantFile("CosmicCodingMuts.vcf.gz")
for record in vcf.fetch("17", 7_668_400, 7_687_500):   # TP53 locus, GRCh38
    print(record.id, record.ref, record.alts, dict(record.info))
```

## Troubleshooting

- **401 / authentication failed** — wrong email/password, unregistered account,
  or a commercial-use account without a license. Confirm you can log in on the
  website first.
- **404 / file not found** — path, version, or assembly wrong. Filenames change
  per release; use `latest` and re-check the current download page. Confirm
  GRCh37 vs GRCh38.
- **Response is HTML, not JSON** — the access protocol changed or a license gate
  is blocking you; re-read the site's download instructions.
- **Signed URL 403 / expired** — you cached the URL too long; re-run step 1 to
  mint a fresh one.
- **Download stalls or truncates on big files** — always stream to disk, raise
  the timeout, and verify the final byte count against `content-length`.
- **Commercial use** — academic access is free with registration; commercial use
  must be licensed through QIAGEN (`cosmic-translation@sanger.ac.uk`).
