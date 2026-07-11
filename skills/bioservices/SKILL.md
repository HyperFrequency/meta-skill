---
name: bioservices
version: 0.1.0
description: >-
  Unified Python client (`bioservices`) over ~40 bioinformatics web services —
  UniProt, KEGG, ChEMBL, ChEBI, Reactome, Ensembl, QuickGO, PSICQUIC, NCBI BLAST
  and more — behind one consistent API that hides each service's REST or
  SOAP/WSDL transport. Use when a workflow spans multiple biological databases:
  retrieving protein/gene records, mining metabolic and signaling pathways,
  searching compound databases, mapping identifiers across services
  (UniProtKB↔KEGG↔Ensembl↔PDB and compound cross-refs via UniChem), running
  remote BLAST or alignments, or querying GO terms and protein-protein
  interactions. NOT for quick single-database one-liners (prefer `gget`), local
  sequence and file parsing/manipulation (prefer `biopython`), or offline
  cheminformatics on molecules already in hand (prefer `rdkit`) — reach for it
  specifically when you need consistent cross-database integration over live web
  services.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "GPLv3 (bioservices)"
---

# BioServices

## Overview

BioServices is a Python package that wraps roughly 40 bioinformatics web
services behind one uniform, object-per-service API. Each database (UniProt,
KEGG, ChEMBL, PSICQUIC, ...) becomes a Python class whose methods return raw
text, tab/TSV, XML, or parsed dictionaries. It transparently handles both REST
and SOAP/WSDL endpoints, so you write the same style of call regardless of the
underlying protocol. Its value is *integration*: chaining several databases in
one script — retrieve, map identifiers, cross-reference, and analyze — without
learning each service's bespoke API.

This SKILL.md is a **router**. It gives you the trigger boundaries and a
minimal call for each capability, then delegates full method tables, the
identifier-code catalogue, and end-to-end pipelines to `references/`.

## When to Use This Skill

Use BioServices when your task **spans multiple biological databases** or needs
a service whose native API you would otherwise hand-roll:

- Retrieve protein sequences, annotations, or features from UniProt (and cross
  to PDB, Pfam, InterPro).
- Mine metabolic or signaling pathways via KEGG or Reactome, and extract
  protein-protein relations / SIF networks from KGML.
- Search compound databases (ChEBI, ChEMBL, PubChem) and cross-reference their
  IDs with UniChem.
- Map identifiers across services — UniProtKB↔KEGG↔Ensembl↔RefSeq↔PDB,
  gene symbol → many DB IDs, compound cross-refs.
- Run remote sequence-similarity searches (NCBI BLAST) or alignments.
- Query Gene Ontology terms/annotations (QuickGO) or protein-protein
  interactions federated across 30+ databases (PSICQUIC).
- Combine several of the above in a single reproducible pipeline.

## When NOT to Use This Skill

- **Quick, single-database lookups.** For a one-line gene/sequence fetch,
  `gget` is lighter and faster.
- **Local sequence or file manipulation.** Parsing FASTA/GenBank, translating,
  building alignments in-process → use `biopython`.
- **Offline cheminformatics on molecules you already hold.** Descriptors,
  fingerprints, substructure search → use `rdkit`. BioServices only *fetches*
  compound records; it does not compute chemistry.
- **Bulk genomics dumps.** For whole-dataset downloads, hit the provider's bulk
  FTP/S3 or a dedicated client — BioServices is for targeted queries.
- **Anything offline.** Every call is a live HTTP request; expect latency, rate
  limits, and occasional service outages.

## Setup

```bash
uv pip install bioservices    # tested on Python 3.9–3.12
```

Instantiate one client per service; pass `verbose=False` to silence HTTP logs.
Clients expose `TIMEOUT` (seconds) and, for many services, response caching.

```python
from bioservices import UniProt, KEGG
u = UniProt(verbose=False)
u.TIMEOUT = 30
```

## Core Capabilities

Each block below is the minimal call. Full method signatures, parameters, and
return shapes live in `references/services_reference.md`.

### Protein & gene records — UniProt

```python
u = UniProt(verbose=False)
u.search("ZAP70_HUMAN", frmt="tsv", columns="accession,gene_names,organism_name")
seq = u.retrieve("P43403", "fasta")          # also "txt", "xml", "gff"
```

### Pathways — KEGG / Reactome

```python
k = KEGG(); k.organism = "hsa"
k.find("pathway", "T cell")                   # search by name
pathways = k.get_pathway_by_gene("7535", "hsa")
kgml = k.parse_kgml_pathway("hsa04660")       # dict: 'entries', 'relations'
sif  = k.pathway2sif("hsa04660")              # activation/inhibition edges
```

### Compounds — KEGG / ChEBI / ChEMBL / UniChem / PubChem

```python
from bioservices import KEGG, UniChem, ChEBI
k = KEGG(); k.find("compound", "Geldanamycin")   # -> cpd:C11222
UniChem().get_compound_id_from_kegg("C11222")    # KEGG -> ChEMBL
ChEBI().getCompleteEntity("CHEBI:5292")          # formula, name, structure
```

### Identifier mapping

```python
u.mapping(fr="UniProtKB_AC-ID", to="KEGG", query="P43403")
# -> {'P43403': ['hsa:7535']}
```

`fr`/`to` accept 100+ database codes and `query` accepts comma-separated IDs
for batch conversion. See `references/identifier_mapping.md` for the code
catalogue, compound mapping via UniChem source-IDs, chunking, and multi-hop
patterns.

### Sequence similarity — NCBI BLAST (asynchronous)

```python
from bioservices import NCBIblast
s = NCBIblast(verbose=False)
job = s.run(program="blastp", sequence=seq, stype="protein",
            database="uniprotkb", email="you@example.com")   # email required
# poll s.getStatus(job) until "FINISHED", then s.getResult(job, "out")
```

### Gene Ontology & interactions — QuickGO / PSICQUIC

```python
from bioservices import QuickGO, PSICQUIC
QuickGO(verbose=False).Annotation(protein="P43403", format="tsv")
PSICQUIC(verbose=False).query("mint", "ZAP70 AND species:9606")
```

## Multi-Service Workflows

BioServices earns its keep when you chain services. `references/workflow_patterns.md`
walks full, runnable pipelines end to end:

- **Protein characterization**: UniProt → sequence → BLAST → KEGG pathways →
  PSICQUIC interactions → GO annotations.
- **Pathway network extraction**: all organism pathways → KGML parse → PPI
  filtering → SIF/NetworkX export.
- **Compound cross-reference**: name → KEGG → ChEBI + ChEMBL + properties.
- **Batch identifier conversion** with chunking, retry, and CSV export.

## Practical Guidance

- **Formats.** Load TSV/tab output straight into pandas via
  `pd.read_csv(StringIO(text), sep="\t")`; feed FASTA to `biopython`; parse XML
  from SOAP services with an XML/BeautifulSoup reader.
- **Async jobs.** BLAST and other submit-and-poll services return a job id —
  always poll `getStatus` until `FINISHED`/`ERROR` before `getResult`.
- **Rate limits & failures.** Every call is network I/O. Wrap calls in
  try/except, chunk large ID batches (50–100), add small `time.sleep` delays,
  and expect intermittent service outages. See troubleshooting in
  `references/identifier_mapping.md`.
- **Organism codes.** KEGG uses short codes — `hsa` (human), `mmu` (mouse),
  `dme` (fly), `sce` (yeast), `eco` (E. coli); list via `k.organismIds`.
- **Version drift.** Upstream databases change their APIs; some method names and
  ID codes vary across bioservices releases. When a call fails unexpectedly,
  confirm the current signature against the official docs
  (https://bioservices.readthedocs.io) before assuming your logic is wrong.

## References

- `references/services_reference.md` — per-service class catalogue: UniProt,
  KEGG, ChEBI, ChEMBL, UniChem, PubChem, NCBIblast, Reactome, PSICQUIC, QuickGO,
  BioMart, PDB, Pfam, ENA and more, with key methods and use cases.
- `references/identifier_mapping.md` — cross-database ID conversion: UniProt
  mapping codes, UniChem compound source-IDs, KEGG entry cross-refs, batch/
  multi-hop patterns, and troubleshooting.
- `references/workflow_patterns.md` — detailed multi-step pipelines and
  integration with `biopython`, pandas, and `networkx`.

**Sibling skills:** `gget` (fast single-database lookups), `biopython` (local
sequence/file work), `rdkit` (offline cheminformatics), `scikit-bio`
(phylogenetics/diversity).
