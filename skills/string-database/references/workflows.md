# STRING Workflows and Helper Module

A self-contained `requests` helper plus five end-to-end analysis recipes, the
evidence-channel interpretation, troubleshooting, and integration notes. Pair
this with `rest-api.md` for exact parameters and output columns.

## Helper Module

No package to install beyond `requests` (and `pandas` for parsing TSV). Copy
this into your project and set `CALLER` to your own app/project name. It joins
identifiers with a carriage return and lets `requests` handle encoding — do not
pre-encode to `%0d`, which double-encodes.

```python
import io
import requests
import pandas as pd

BASE = "https://string-db.org/api"            # or a pinned version-12-0.string-db.org/api
CALLER = "my_project"                          # identify yourself to STRING


def _ids(identifiers):
    if isinstance(identifiers, (list, tuple, set)):
        return "\r".join(map(str, identifiers))
    return str(identifiers)


def _post(fmt, method, **params):
    params.setdefault("caller_identity", CALLER)
    params["identifiers"] = _ids(params["identifiers"])
    r = requests.post(f"{BASE}/{fmt}/{method}", data=params, timeout=60)
    r.raise_for_status()
    return r


def map_ids(identifiers, species=9606, limit=1):
    r = _post("tsv", "get_string_ids", identifiers=identifiers,
              species=species, limit=limit, echo_query=1)
    return pd.read_csv(io.StringIO(r.text), sep="\t")


def network(identifiers, species=9606, required_score=400,
            network_type="functional", add_nodes=0):
    r = _post("tsv", "network", identifiers=identifiers, species=species,
              required_score=required_score, network_type=network_type,
              add_nodes=add_nodes)
    return pd.read_csv(io.StringIO(r.text), sep="\t")


def partners(identifiers, species=9606, required_score=400, limit=10):
    r = _post("tsv", "interaction_partners", identifiers=identifiers,
              species=species, required_score=required_score, limit=limit)
    return pd.read_csv(io.StringIO(r.text), sep="\t")


def ppi_enrichment(identifiers, species=9606, required_score=400):
    r = _post("json", "ppi_enrichment", identifiers=identifiers,
              species=species, required_score=required_score)
    return r.json()[0]        # single-object list


def enrichment(identifiers, species=9606):
    r = _post("tsv", "enrichment", identifiers=identifiers, species=species)
    return pd.read_csv(io.StringIO(r.text), sep="\t")


def network_image(identifiers, species=9606, required_score=400,
                  network_flavor="evidence", add_nodes=0, path="network.png"):
    r = _post("image", "network", identifiers=identifiers, species=species,
              required_score=required_score, network_flavor=network_flavor,
              add_nodes=add_nodes)
    with open(path, "wb") as fh:
        fh.write(r.content)
    return path


def version():
    return requests.get(f"{BASE}/tsv/version", timeout=30).text
```

An empty DataFrame from `network`/`enrichment` almost always means the score
threshold was too high or the species is wrong — not a network error.

## Workflow 1 — Standard protein-list analysis

Analyze a hit list from an experiment (differential expression, proteomics).

```python
genes = ["TP53", "BRCA1", "ATM", "CHEK2", "MDM2", "ATR", "BRCA2"]

mapping = map_ids(genes, species=9606)               # validate names
net = network(genes, species=9606, required_score=400)
conn = ppi_enrichment(genes, species=9606)           # module test
enr = enrichment(genes, species=9606)
network_image(genes, species=9606, network_flavor="evidence",
              required_score=400, path="protein_network.png")

if conn["p_value"] < 0.05:
    print("Set is more connected than chance — likely a functional module.")
sig = enr[enr["fdr"] < 0.05].sort_values("fdr")      # significant terms
```

## Workflow 2 — Single-protein deep dive

```python
p = "TP53"
map_ids(p, species=9606)
top = partners(p, species=9606, limit=20, required_score=700)  # strongest 20
network_image(p, species=9606, add_nodes=15, network_flavor="confidence",
              required_score=700, path="tp53_network.png")
```

## Workflow 3 — Pathway-centric analysis

Start from known pathway members, widen slightly, confirm the annotation.

```python
dna_repair = ["TP53", "ATM", "ATR", "CHEK1", "CHEK2",
              "BRCA1", "BRCA2", "RAD51", "XRCC1"]
net = network(dna_repair, species=9606, required_score=700, add_nodes=5)
enr = enrichment(dna_repair, species=9606)
hits = enr[enr["description"].str.contains("DNA repair", case=False, na=False)]
```

## Workflow 4 — Cross-species comparison

Re-run the same query per species with the ortholog's local symbol.

```python
human = network("TP53",  species=9606,  required_score=700)   # human
mouse = network("Trp53", species=10090, required_score=700)   # mouse ortholog
```

Compare `preferredName_A/B` sets or combined `score` distributions. STRING does
not align networks for you — map orthologs first (via `homology`,
`ensembl-database`, or `gget`) if you need node-to-node correspondence.

## Workflow 5 — Seed-and-expand discovery

Grow a functional neighborhood from a seed, then characterize it.

```python
seed = ["TP53"]
pt = partners(seed, species=9606, limit=30, required_score=700)
expanded = sorted(set(pt["preferredName_A"]) | set(pt["preferredName_B"]))
enr = enrichment(expanded[:50], species=9606)         # cap to keep it fast
modules = enr[enr["fdr"] < 0.001]                     # tight modules only
```

## Reading Evidence Channels

Each interaction row carries seven subscores in addition to the combined
`score`. They are independent evidence types (0-1 in TSV output):

| Column | Channel | Signal |
|---|---|---|
| `nscore` | Neighborhood | genes repeatedly close on the chromosome across genomes |
| `fscore` | Fusion | the two genes are fused into one ORF in some genome |
| `pscore` | Phylogenetic co-occurrence | genes present/absent together across species |
| `ascore` | Co-expression | correlated mRNA/array/RNA-seq expression |
| `escore` | Experiments | biochemical/genetic interaction assays |
| `dscore` | Database | curated pathway/complex membership (KEGG, Reactome, ...) |
| `tscore` | Text-mining | co-mention in abstracts/full text |

Practical reading:
- High `escore`/`dscore` = strong, curated/experimental support — trust it.
- High `tscore` only = literature co-mention; can be indirect or a naming
  artifact. Corroborate before drawing conclusions.
- `nscore`/`fscore`/`pscore` are genomic-context signals, strongest for
  prokaryotes; often near-zero for human pairs.

The combined `score` is a noisy-OR-style fusion of the channels against a
random-background model — it is not their sum, and a single strong channel can
carry a high combined score.

## Choosing a Threshold

`required_score` filters on the 0-1000 combined scale. Start at 400; move to
700 for figures and claims, 900 for stringent experiment-weighted sets, 150
only for exploration. Raising the threshold monotonically drops edges (higher
precision, lower recall). For `physical` networks, the same numeric threshold
is generally stricter because fewer channels contribute.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty result | Threshold too high or species mismatch | Lower `required_score`; confirm taxon ID; map IDs first |
| "no proteins found" | Bad names / wrong species | Run `map_ids` and use the returned STRING IDs |
| `species required` error | >10 identifiers without `species` | Always pass `species` |
| Slow / timeout | Too many inputs | Reduce input, use STRING IDs, split into batches, pause ~1s |
| Results differ from last month | New DB release | Pin `version-12-0.string-db.org/api`; record `version()` |
| Unexpected edges | `functional` includes non-physical evidence | Switch to `network_type="physical"` |

## Integration

- **`bioservices`** — provides a `STRING` Python class wrapping these same
  endpoints if you want one client across many databases.
- **R `STRINGdb`** (Bioconductor): `STRINGdb$new(version="12", species=9606)`
  for mapping, enrichment, and plotting inside R.
- **Cytoscape stringApp** — import the TSV network or query STRING directly for
  interactive layout and styling.
- **`networkx`** — load the `network()` DataFrame edges to compute centrality,
  detect communities, or find shortest paths locally.

## License and Citation

STRING data is CC BY 4.0 (free for academic and commercial use with
attribution). Cite the latest STRING publication from
`https://string-db.org/cgi/about`. This skill is adapted from openscience
(Synthetic Sciences, Apache-2.0).
