# KEGG REST API Reference

- **Base URL:** `https://rest.kegg.jp`
- **Official docs:** https://www.kegg.jp/kegg/rest/keggapi.html
- **Auth:** none (no key). **Terms:** academic use only; commercial or bulk use
  requires a KEGG license (use the licensed FTP release, not this endpoint).

All responses are text. Most operations return tab-delimited rows; `get`
supports several structured formats (below).

## The 16 KEGG databases

Group these when picking a `<db>` argument.

**Systems information**
- `pathway` — curated pathway maps (metabolism, signaling, disease, drug dev.)
- `module` — reusable functional units / building blocks of pathways
- `brite` — hierarchical classifications and ontologies

**Genomic information**
- `genome` — complete annotated genomes
- `genes` — gene catalogs across organisms (query per-organism as `<org>`)
- `orthology` / `ko` — KEGG Orthology groups (cross-organism functional units)
- (SSDB — sequence-similarity data, surfaced via entry cross-links)

**Chemical information**
- `compound` — metabolites and other small molecules
- `glycan` — glycan structures
- `reaction` — biochemical reactions
- `rclass` — reaction classes (structure-transformation patterns)
- `enzyme` — enzyme nomenclature (EC numbers)
- `network` — network variation elements

**Health information**
- `disease` — human diseases with genetic/environmental factors
- `drug` — approved drugs, structures, targets
- `dgroup` — drug groups

**External cross-reference targets** (used by `conv`/`link`): `ncbi-geneid`,
`ncbi-proteinid`, `uniprot`, `pubchem`, `chebi`, plus literature via `pubmed`.

## Operations in detail

### info — `/info/<db>`
Release metadata and entry counts.
- `/info/kegg` — whole-system release
- `/info/pathway` — pathway database stats
- `/info/hsa` — the human genome database

### list — `/list/<db>[/<org>]`
Enumerate identifiers with names.
- `/list/pathway` — all reference pathways (`map#####`)
- `/list/pathway/hsa` — human-specific pathways (`hsa#####`)
- `/list/organism` — every organism code
- `/list/hsa:10458+hsa:10459` — names for specific entries (≤10)

### find — `/find/<db>/<query>[/<option>]`
Search by keyword or molecular property. URL-encode the query.
- `/find/genes/shiga%20toxin` — keyword search
- `/find/compound/C7H10N4O2/formula` — **exact** chemical-formula match
- `/find/compound/174.05-174.15/exact_mass` — exact-mass **range** (Da)
- `/find/drug/300-310/mol_weight` — molecular-weight range

`option` ∈ `{formula, exact_mass, mol_weight}`. Without an option the query runs
against text fields (ENTRY, NAME, SYMBOL, DEFINITION, etc., database-dependent).

### get — `/get/<id>[+<id>…][/<format>]`
Fetch full entries or a specific data format. Up to **10** ids joined by `+`.

| `format` | Meaning | Multi-entry? |
|----------|---------|--------------|
| *(none)* | full flat-file entry | yes (≤10) |
| `aaseq` | amino-acid FASTA | yes |
| `ntseq` | nucleotide FASTA | yes |
| `mol` | MOL structure (compound/drug) | yes |
| `kcf` | KEGG Chemical Function structure | yes |
| `image` | PNG pathway map | **single only** |
| `kgml` | KGML pathway XML | **single only** |
| `json` | pathway graph JSON | **single only** |

Examples:
- `/get/hsa00010` — glycolysis entry (human)
- `/get/hsa:10458/aaseq` — protein sequence
- `/get/cpd:C00002` — ATP entry; `/get/cpd:C00002/mol` — its structure
- `/get/hsa05130/json` — Pathogenic *E. coli* infection map as JSON
- `/get/hsa05130/image` — same map as PNG (bytes, not UTF-8 text)

Note: `image` returns binary PNG data — read `response.read()` as bytes and
write to a file; do **not** `.decode("utf-8")`.

### conv — `/conv/<target_db>/<source>`
Bidirectional ID mapping. `source` may be a database name (whole-set) or a
single entry.
- `/conv/ncbi-geneid/hsa` — every human gene → NCBI Gene ID
- `/conv/hsa/ncbi-geneid` — reverse direction
- `/conv/uniprot/hsa:10458` — one gene → UniProt
- `/conv/pubchem/compound` — all compounds → PubChem
Supported targets: `ncbi-geneid`, `ncbi-proteinid`, `uniprot` (genes);
`pubchem`, `chebi` (compounds/drugs/glycans).

### link — `/link/<target_db>/<source>`
Relationships within and across databases.
- `/link/pathway/hsa` — pathways linked to any human gene
- `/link/genes/hsa00010` — genes in the glycolysis pathway
- `/link/pathway/hsa:10458` — pathways containing one gene
- `/link/compound/hsa00010` — compounds in a pathway
- `/link/ko/hsa:10458` — KO group(s) for a gene
Common pairs: genes↔pathway, pathway↔compound, pathway↔enzyme, genes↔ko,
compound↔reaction, reaction↔pathway.

### ddi — `/ddi/<drug>[+<drug>…]`
Drug-drug interactions (from Japanese drug labels). ≤10 drugs joined with `+`.
- `/ddi/D00001` — interactions for one drug
- `/ddi/D00564+D00100` — interactions among a set

## HTTP status codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | success (may be empty body) | parse; empty = valid query, no match |
| 400 | bad request — syntax error | check operation/argument formatting |
| 404 | not found — unknown id/db | verify the id and organism code |

`urllib.request.urlopen` raises `urllib.error.HTTPError` for 4xx. Catch it so a
real "no matches" (200 + empty) is distinguishable from a malformed call.

## Robust Python helper

Standard-library only; adds batching, encoding, binary handling, and error
messages. Extend with local caching for repeated pulls.

```python
import urllib.request, urllib.parse, urllib.error

BASE = "https://rest.kegg.jp"

def _fetch(url, binary=False):
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            return data if binary else data.decode("utf-8")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"KEGG {error.code} {error.reason} for {url}") from error

def kegg_get(entries, fmt=None):
    """entries: str or list (<=10). fmt in aaseq/ntseq/mol/kcf/image/kgml/json.

    image/kgml/json accept only ONE entry. image returns bytes.
    """
    if isinstance(entries, (list, tuple)):
        if fmt in {"image", "kgml", "json"} and len(entries) > 1:
            raise ValueError(f"{fmt} accepts a single entry only")
        entries = "+".join(entries[:10])
    url = f"{BASE}/get/{entries}" + (f"/{fmt}" if fmt else "")
    return _fetch(url, binary=(fmt == "image"))

def kegg_find(db, query, option=None):
    """Free-text or property search. option in formula/exact_mass/mol_weight."""
    q = urllib.parse.quote(query)
    url = f"{BASE}/find/{db}/{q}" + (f"/{option}" if option else "")
    return _fetch(url)

def kegg_link(target_db, source):
    return _fetch(f"{BASE}/link/{target_db}/{source}")

def kegg_conv(target_db, source):
    return _fetch(f"{BASE}/conv/{target_db}/{source}")

def parse_tsv(text):
    """Rows of tab-delimited KEGG output -> list of tuples (blank line dropped)."""
    return [tuple(line.split("\t")) for line in text.splitlines() if line]
```
