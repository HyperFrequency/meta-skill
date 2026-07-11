---
name: kegg-database
version: 0.1.0
description: >-
  Query the KEGG REST API (rest.kegg.jp) for biological pathways, genes,
  compounds, enzymes, reactions, glycans, diseases, and drugs across thousands
  of organisms. Use when mapping genes to pathways, building pathway-enrichment
  context, tracing metabolic reactions, converting IDs between KEGG and
  NCBI/UniProt/PubChem/ChEBI, retrieving sequences or pathway maps
  (KGML/JSON/PNG), or checking drug-drug interactions. Covers the seven REST
  operations (info, list, find, get, conv, link, ddi), identifier formats, and
  the 10-entry batch limit. Academic use only; commercial use requires a KEGG
  license. NOT for general web or literature search (use research-lookup),
  DOI/citation metadata (use citation-management), other named databases you
  can hit directly (UniProt, PubChem, NCBI), or large multi-database Python
  pipelines where the bioservices library fits better.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# KEGG Database

## Overview

KEGG (Kyoto Encyclopedia of Genes and Genomes) is a manually curated collection
of pathway maps, molecular interaction networks, and reference databases for
genomes, chemistry, and health. This skill drives its public REST interface at
`https://rest.kegg.jp` directly over HTTP — no API key, no SDK required.

Responses are plain text: most operations return **tab-delimited** rows; `get`
can also return FASTA, MOL, KCF, KGML (XML), JSON, or a PNG image depending on
the requested format. There are seven operations — `info`, `list`, `find`,
`get`, `conv`, `link`, `ddi` — each a URL template you fill in and fetch.

**License constraint (load-bearing):** the KEGG API is provided for *academic
use by academic users only*. Commercial or high-volume programmatic use
requires a separate KEGG subscription/license (KEGG FTP or a licensed mirror).
Surface this to the user before scripting bulk pulls.

## When to Use This Skill

- Map genes to pathways (or pathways to their member genes) for enrichment context.
- Trace metabolic routes: compound → reaction → pathway, or enzyme → reaction.
- Convert identifiers between KEGG and NCBI Gene/Protein, UniProt, PubChem, ChEBI.
- Retrieve a full entry: pathway, gene, compound, drug, enzyme (EC), or KO group.
- Pull sequences (`aaseq`/`ntseq`), chemical structures (`mol`/`kcf`), or a
  pathway map as KGML/JSON/PNG.
- Compare the same reference pathway across organisms (human vs mouse vs yeast).
- Check drug-drug interactions with the `ddi` operation.

## When NOT to Use This Skill

- General web questions or recent literature → use `research-lookup`.
- DOI-to-BibTeX, PubMed/Scholar citation metadata → use `citation-management`.
- Structured lookups in a *different* named database (UniProt, PubChem, NCBI,
  ChEBI) where you can query that service directly → use `database-lookup`.
- Commercial or bulk analytics over KEGG data — the public API forbids it;
  obtain a KEGG license and use the FTP release instead.
- A Python project that already juggles many bio databases — the `bioservices`
  library wraps KEGG plus dozens of others with parsing and caching built in;
  reach for the raw REST calls here only when you need HTTP-level control.

## The Seven Operations

| Operation | URL pattern | Returns | Use for |
|-----------|-------------|---------|---------|
| `info` | `/info/<db>` | release stats | database metadata, entry counts, version |
| `list` | `/list/<db>[/<org>]` | id + name rows | enumerate pathways, genes, compounds |
| `find` | `/find/<db>/<query>[/<option>]` | matching id + name rows | keyword / formula / mass search |
| `get`  | `/get/<id>[+<id>…][/<format>]` | full entry or formatted data | fetch entries, sequences, maps |
| `conv` | `/conv/<target_db>/<source>` | id ↔ id table | cross-database ID mapping |
| `link` | `/link/<target_db>/<source>` | related-id pairs | relationships (gene↔pathway, etc.) |
| `ddi`  | `/ddi/<drug>[+<drug>…]` | interaction rows | drug-drug interactions |

Batch limit: at most **10 entries** per `get`/`ddi` call, joined with `+`. The
`image`, `kgml`, and `json` formats accept **only one entry** at a time.

See `references/rest-api.md` for every parameter, output format, organism code,
identifier scheme, and HTTP status code.

## Quick Start

One generic helper covers all seven operations. Standard-library only:

```python
import urllib.request, urllib.parse

BASE = "https://rest.kegg.jp"

def kegg(operation, *args, encode=None):
    """Call a KEGG REST operation and return the raw text body.

    operation: one of info, list, find, get, conv, link, ddi
    args:      the path segments after the operation, in order
    encode:    index into args to URL-encode (use for free-text `find` queries)
    """
    parts = list(args)
    if encode is not None:
        parts[encode] = urllib.parse.quote(parts[encode])
    url = f"{BASE}/{operation}/" + "/".join(parts)
    with urllib.request.urlopen(url) as response:  # raises HTTPError on 400/404
        return response.read().decode("utf-8")

kegg("list", "pathway", "hsa")               # all human pathways
kegg("get", "hsa00010")                      # glycolysis entry (human)
kegg("link", "pathway", "hsa:7157")          # pathways containing TP53
kegg("conv", "uniprot", "hsa:10458")         # KEGG gene -> UniProt
kegg("find", "genes", "shiga toxin", encode=0)  # keyword search (space encoded)
```

For batched `get`, join up to 10 ids with `+`:
`kegg("get", "hsa:10458+hsa:10459")`. A production-grade helper (batching,
retries, image handling, tab parsing) is in `references/rest-api.md`.

## Identifier Cheatsheet

| Kind | Format | Example |
|------|--------|---------|
| Reference pathway | `map#####` | `map00010` (glycolysis) |
| Organism pathway | `<org>#####` | `hsa00010`, `mmu00010` |
| Gene | `<org>:<number>` | `hsa:10458` |
| Compound | `cpd:C#####` | `cpd:C00002` (ATP) |
| Drug | `dr:D#####` | `dr:D00001` |
| Enzyme | `ec:<EC>` | `ec:1.1.1.1` |
| KEGG Orthology | `ko:K#####` | `ko:K00001` |

Common organism codes: `hsa` (human), `mmu` (mouse), `rno` (rat), `dme` (fly),
`cel` (worm), `sce` (yeast), `eco` (E. coli). Full list via `kegg("list", "organism")`.

## Constraints and Failure Modes

- **10-entry cap** on `get`/`ddi`; `image`/`kgml`/`json` are single-entry only.
- **HTTP status codes:** `200` success, `400` malformed request (bad syntax),
  `404` unknown entry/database. The helper's `urlopen` raises `HTTPError` on
  4xx — wrap calls in `try/except urllib.error.HTTPError` to distinguish a
  genuine empty result from a bad request.
- **Empty body, status 200** means the query was valid but matched nothing —
  broaden the keyword or verify the organism code.
- **URL-encode free-text `find` queries** (spaces, `/`, `+`). ID-based paths use
  literal `+` as the batch separator, so never encode those.
- **No documented rate limit**, but throttle bulk loops and cache locally;
  hammering the endpoint is both impolite and a license concern.
- **Tab-delimited parsing:** split each line on `\t`; the first field is the
  queried id, the second is the name or linked id. Trailing blank line is normal.

## References

- `references/rest-api.md` — full operation syntax, all `get` output formats,
  the 16 KEGG databases, `conv`/`link` target vocabularies, organism codes, HTTP
  status handling, and a robust batching Python helper.
- `references/workflows.md` — end-to-end analysis recipes (gene→pathway,
  enrichment context, compound→reaction→pathway, cross-database integration,
  cross-organism comparison), the seven pathway categories, and integration with
  Biopython (`Bio.KEGG.REST`), R `KEGGREST`, and `bioservices`.
