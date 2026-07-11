# Ensembl REST — Reusable Client and Workflows

A small, dependency-light client (`requests` only) that enforces the ~15 req/s
anonymous rate limit and retries on 429/5xx with exponential back-off, plus
worked end-to-end workflows. Endpoint contract is in [rest-api.md](rest-api.md).

## Rate-limited client

```python
#!/usr/bin/env python3
"""Minimal Ensembl REST client with rate limiting and retries."""

import time
import requests

CURRENT_SERVER = "https://rest.ensembl.org"      # GRCh38 / all species
GRCH37_SERVER = "https://grch37.rest.ensembl.org"  # human hg19 only


class EnsemblClient:
    def __init__(self, server=CURRENT_SERVER, requests_per_second=15):
        self.server = server.rstrip("/")
        self.min_interval_seconds = 1.0 / requests_per_second
        self._last_request_time = 0.0
        self.session = requests.Session()

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_time = time.time()

    def request(self, endpoint, params=None, json_body=None,
                content_type="application/json", max_retries=3):
        """GET (or POST if json_body is given) with retry/back-off.

        Returns parsed JSON for application/json, else raw text (e.g. FASTA).
        Raises on 404/400 (caller's bug, not transient) and after exhausting retries.
        """
        url = f"{self.server}{endpoint}"
        headers = {"Content-Type": content_type}

        for attempt in range(max_retries):
            self._throttle()
            if json_body is not None:
                response = self.session.post(url, headers=headers, json=json_body)
            else:
                response = self.session.get(url, headers=headers, params=params)

            if response.status_code == 200:
                if content_type == "application/json":
                    return response.json()
                return response.text
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(retry_after)
                continue
            if response.status_code in (400, 404):
                response.raise_for_status()  # not transient — surface immediately
            # 5xx: exponential back-off, then retry
            time.sleep(2 ** attempt)

        response.raise_for_status()
        raise RuntimeError(f"Ensembl request failed after {max_retries} attempts: {endpoint}")

    # --- thin endpoint helpers -------------------------------------------

    def lookup_symbol(self, species, symbol, expand=True):
        return self.request(f"/lookup/symbol/{species}/{symbol}",
                            params={"expand": 1} if expand else None)

    def lookup_id(self, ensembl_id, expand=False):
        return self.request(f"/lookup/id/{ensembl_id}",
                            params={"expand": 1} if expand else None)

    def lookup_ids(self, ensembl_ids):  # batch POST
        return self.request("/lookup/id", json_body={"ids": ensembl_ids})

    def sequence_id(self, ensembl_id, seq_type="genomic", fasta=False):
        return self.request(
            f"/sequence/id/{ensembl_id}", params={"type": seq_type},
            content_type="text/x-fasta" if fasta else "application/json")

    def sequence_region(self, species, region, fasta=False):
        return self.request(
            f"/sequence/region/{species}/{region}",
            content_type="text/x-fasta" if fasta else "application/json")

    def variant(self, species, variant_id, populations=True):
        return self.request(f"/variation/{species}/{variant_id}",
                            params={"pops": 1} if populations else None)

    def vep_hgvs(self, species, hgvs_notation):
        return self.request(f"/vep/{species}/hgvs/{hgvs_notation}")

    def homology(self, ensembl_id, target_species=None, homology_type="orthologues"):
        params = {"type": homology_type}
        if target_species:
            params["target_species"] = target_species
        return self.request(f"/homology/id/{ensembl_id}", params=params)

    def overlap_region(self, species, region, feature="gene"):
        return self.request(f"/overlap/region/{species}/{region}",
                            params={"feature": feature})

    def map_assembly(self, species, asm_from, region, asm_to):
        return self.request(f"/map/{species}/{asm_from}/{region}/{asm_to}")

    def release(self):
        return self.request("/info/data")
```

### Choosing the server

```python
client = EnsemblClient()                          # GRCh38 / current
grch37 = EnsemblClient(server=GRCH37_SERVER)       # human hg19 coordinates
```

## Batch queries

Always prefer the POST batch endpoints over a Python loop of GETs — one round
trip, one rate-limit charge:

```python
records = client.lookup_ids(["ENSG00000139618", "ENSG00000157764"])
seqs    = client.request("/sequence/id", json_body={"ids": ["ENSG00000139618"]})
vep     = client.request("/vep/human/hgvs",
                         json_body={"hgvs_notations": ["ENST00000366667:c.803C>T"]})
```

## Workflow: gene → annotation → orthologs

```python
client = EnsemblClient()

gene = client.lookup_symbol("homo_sapiens", "BRCA2", expand=True)
gene_id = gene["id"]
transcript_ids = [t["id"] for t in gene.get("Transcript", [])]

protein_fasta = client.sequence_id(gene_id, seq_type="protein", fasta=True)

mouse_orthologs = client.homology(gene_id, target_species="mouse",
                                  homology_type="orthologues")
```

## Workflow: variant analysis

```python
record = client.variant("human", "rs699", populations=True)      # frequencies
consequences = client.vep_hgvs("human", "ENST00000366667:c.803C>T")
# Inspect consequence terms, SIFT/PolyPhen scores, affected transcripts in the result.
```

## Workflow: region scan + assembly lift

```python
genes = client.overlap_region("human", "7:140424943..140624564", feature="gene")

# Lift a GRCh37 position to GRCh38
lifted = client.map_assembly("human", "GRCh37",
                             "7:140453136..140453136", "GRCh38")
```

## Minimal CLI

```python
import argparse, json, sys

def main():
    parser = argparse.ArgumentParser(description="Query the Ensembl REST API")
    parser.add_argument("--species", default="human")
    parser.add_argument("--gene", help="gene symbol")
    parser.add_argument("--ensembl-id")
    parser.add_argument("--variant", help="e.g. rs699")
    parser.add_argument("--region", help="chr:start-end")
    parser.add_argument("--orthologs", help="Ensembl gene ID")
    parser.add_argument("--target-species")
    parser.add_argument("--grch37", action="store_true", help="use the GRCh37 server")
    args = parser.parse_args()

    client = EnsemblClient(server=GRCH37_SERVER if args.grch37 else CURRENT_SERVER)
    try:
        if args.gene:
            out = client.lookup_symbol(args.species, args.gene)
        elif args.ensembl_id:
            out = client.lookup_id(args.ensembl_id, expand=True)
        elif args.variant:
            out = client.variant(args.species, args.variant)
        elif args.region:
            out = client.overlap_region(args.species, args.region)
        elif args.orthologs:
            out = client.homology(args.orthologs, target_species=args.target_species)
        else:
            parser.print_help(); return 0
        print(json.dumps(out, indent=2))
        return 0
    except requests.HTTPError as error:
        print(f"HTTP error: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

```bash
python ensembl_query.py --gene BRCA2 --species human
python ensembl_query.py --variant rs699
python ensembl_query.py --region "7:140424943-140624564"
python ensembl_query.py --orthologs ENSG00000139618 --target-species mouse
python ensembl_query.py --gene BRCA2 --grch37     # hg19 coordinates
```

## Edge cases to handle

- **Empty / 404 for valid-looking IDs** — the ID may belong to a different
  species or a retired release; check `/archive/id/:id` for retired IDs.
- **Assembly mismatch** — GRCh37 coordinates against the default server return
  wrong or empty results silently. Route hg19 queries to the GRCh37 server.
- **FASTA vs JSON** — request FASTA with `Content-Type: text/x-fasta` and read
  `response.text`; do not call `.json()` on it.
- **Large `overlap` / `sequence` regions** — Ensembl caps region size for some
  feature types; split very large intervals or use the FTP dumps for
  chromosome-scale extraction.
- **Free-text params** — URL-encode ontology and phenotype terms and any HGVS
  notation containing `>` or spaces.
