---
name: drugbank-database
version: 0.1.0
description: >-
  Access and analyze DrugBank — a curated pharmacology/cheminformatics database
  of drugs and drug targets (properties, indication, mechanism, ADME, chemical
  structures, drug-drug interactions, targets/enzymes/transporters/carriers,
  SMPDB pathways) — from its downloaded XML via Python (drugbank-downloader,
  ElementTree/lxml, RDKit). Use to look up a drug's pharmacology or identifiers,
  screen a polypharmacy regimen for interactions, map drugs to protein targets
  or pathways for mechanism and repurposing, run structure similarity or
  substructure searches over the corpus, or apply Lipinski/Veber drug-likeness
  filters. Not for measured bioactivity/IC50 datasets (use chembl-database),
  cheminformatics on your own molecules (rdkit, datamol, deepchem), docking
  (molecular-docking), de-novo generation (denovo-design), trained ADMET models
  (admet-prediction), or UniProt/PubChem/PDB lookups (database-lookup,
  bioservices). Requires a free DrugBank academic account; data is
  non-commercial (CC BY-NC).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: >-
    drugbank-downloader is MIT; DrugBank data itself is released under a
    non-commercial academic license (CC BY-NC 4.0) and requires registration and
    acceptance of DrugBank's license agreement.
---

# DrugBank Database

## Overview

DrugBank is a manually curated bioinformatics/cheminformatics database pairing
detailed drug data with drug-target information. Each entry carries 200+ fields:
identifiers and names, chemical structure (SMILES/InChI), pharmacology
(indication, mechanism of action, pharmacodynamics), pharmacokinetics (ADME),
toxicity, drug-drug interactions, protein targets/enzymes/transporters/carriers,
and SMPDB pathways. Recent releases hold on the order of 15,000 drug entries
(thousands of FDA-approved small molecules and biologics, plus experimental and
investigational compounds); **exact counts are version-dependent — download a
specific version and count, do not quote a fixed number.**

Work against the **bulk XML release**, not the live web API. Download it once
with the `drugbank-downloader` package, parse it with `xml.etree.ElementTree`
(or `lxml` for speed), and query the in-memory tree. This skill covers loading
the data, drug lookups, interaction analysis, target/pathway mapping, and
structure-based cheminformatics.

## When to Use This Skill

- **Drug profiling** — pull a drug's indication, mechanism, pharmacodynamics,
  ADME, toxicity, and external identifiers (PubChem, ChEMBL, UniProt, KEGG).
- **Polypharmacy safety** — check every pairwise drug-drug interaction in a
  regimen and score overall risk.
- **Mechanism / repurposing** — map drugs to their protein targets, enzymes,
  transporters, and pathways; find drugs with shared targets.
- **Structure search** — RDKit Tanimoto similarity, fingerprints, or SMARTS
  substructure queries over DrugBank SMILES.
- **Drug-likeness screening** — apply Lipinski Rule-of-Five and Veber rules, or
  coarse absorption/BBB heuristics, across the corpus.
- **Dataset building** — export drugs, interactions, drug-target edges, or
  chemical properties to pandas/CSV.

## When NOT to Use This Skill

- **Measured bioactivity (IC50/Ki/EC50) datasets** — use `chembl-database`;
  DrugBank is drug-centric, not a bioassay repository.
- **Cheminformatics on your own molecules** — use `rdkit`, `datamol`, `molfeat`,
  or `deepchem`; only use this skill when the molecules come from DrugBank.
- **Docking / pose prediction** — use `molecular-docking`.
- **De-novo generation** — use `denovo-design` or `drug-design`.
- **Trained ADMET model predictions** — use `admet-prediction`; the heuristics
  here are rule-based screens, not learned models.
- **Other databases** (UniProt, PubChem, PDB, ChEMBL) — use `database-lookup`,
  `bioservices`, or their dedicated `*-database` skills.
- **Commercial use** — DrugBank's free data is non-commercial (CC BY-NC);
  confirm licensing before any commercial project.

## Setup

```bash
uv pip install drugbank-downloader   # core access
uv pip install bioversions           # auto-detect latest version (optional)
uv pip install lxml pandas           # faster parsing + tabular analysis
uv pip install rdkit                 # structure similarity / fingerprints
uv pip install networkx              # interaction-network analysis
uv pip install scikit-learn          # chemical-space PCA / clustering
```

**Account**: register at go.drugbank.com, accept the (free academic) license,
and note your username/password. Provide credentials via environment variables —
never hardcode them:

```bash
export DRUGBANK_USERNAME="your_username"
export DRUGBANK_PASSWORD="your_password"
```

See `references/data-access.md` for the config-file alternative, CLI usage,
caching, and troubleshooting.

## Loading the Data

```python
from drugbank_downloader import download_drugbank, get_drugbank_root

# Pin the version for reproducibility (bioversions auto-detects latest if omitted)
path = download_drugbank(version="5.1.10")   # cached under ~/.data/drugbank/
root = get_drugbank_root()                    # parsed <drugbank> element tree

# DrugBank XML uses a default namespace — you MUST bind it in every query
ns = {"db": "http://www.drugbank.ca"}
first = root.find("db:drug", ns)
print(first.find("db:name", ns).text)
```

The uncompressed XML is large (well over 1 GB) and `get_drugbank_root` loads it
fully into memory. For repeated lookups, build an index once rather than
re-scanning the tree per query (see `references/drug-queries.md`).

Full detail — auth, download methods, custom storage, caching, version history,
error handling: **`references/data-access.md`**.

## Drug Information Queries

Look up drugs by DrugBank ID, name, synonym, or CAS number, and extract basic
info, chemical properties, pharmacology, and cross-database identifiers. Build
searchable dictionaries or pandas DataFrames, filter by drug type, and search
free-text fields by keyword.

Detail — XML schema, namespace handling, per-field extractors, index building,
DataFrame export: **`references/drug-queries.md`**.

## Drug-Drug Interactions

Extract all interactions for a drug, check specific pairs (always
bidirectionally), classify severity and mechanism from the description text,
build interaction matrices and `networkx` graphs, run community detection, and
score polypharmacy risk.

Detail — extraction, classification heuristics, matrices, network analysis,
polypharmacy scoring: **`references/interactions.md`**.

## Targets, Enzymes, and Pathways

Access drug-protein relationships: therapeutic **targets** (with actions like
inhibitor/agonist/antagonist), metabolic **enzymes** (CYP450 and Phase II),
**transporters** (efflux/uptake), and plasma **carriers** — plus SMPDB
**pathways**. Find drugs hitting a given protein, drugs with shared targets (for
repurposing), and GO/UniProt annotations.

Detail — target/enzyme/transporter/carrier extraction, drug-target matrices,
shared-target repurposing, CYP450 profiling, pathway networks, GO terms:
**`references/targets-pathways.md`**.

## Chemical Structure and Similarity

Extract SMILES/InChI/InChIKey and calculated/experimental physicochemical
properties. With RDKit: compute Tanimoto similarity, generate Morgan/MACCS/
topological fingerprints, run SMARTS substructure searches, apply Lipinski/Veber
filters, screen absorption/BBB with simple rules, and explore chemical space via
PCA/clustering.

Detail — structure extraction, similarity, fingerprints, drug-likeness, ADMET
heuristics, chemical-space analysis: **`references/chemical-analysis.md`**.

## Reproducibility and Gotchas

- **Pin the version.** Always pass `version=` to `download_drugbank` and record
  it in publications/scripts — DrugBank content changes release to release.
- **Bind the namespace** on every `find`/`findall`; queries silently return
  `None`/`[]` if you forget the `http://www.drugbank.ca` namespace.
- **Index, don't rescan.** Naive helpers loop over all drugs per query (O(n));
  build ID/name/CAS indexes once for repeated lookups.
- **Memory.** The tree is large; on constrained machines use `lxml` and consider
  `iterparse` streaming, or subset to approved drugs before heavy work.
- **Interactions are directional in the file** — check both A→B and B→A.
- **Validate structures** with RDKit (`Chem.MolFromSmiles`) before similarity;
  some SMILES fail to parse and return `None`.
- **License** — DrugBank data is CC BY-NC; the `drugbank-downloader` code is MIT.

## Reference Files

- **`references/data-access.md`** — authentication, download, parsing, caching,
  a reusable `DrugBankHelper` class, troubleshooting.
- **`references/drug-queries.md`** — XML navigation, ID/name/CAS queries, field
  extractors, indexing, DataFrame export.
- **`references/interactions.md`** — DDI extraction, severity/mechanism
  classification, matrices, network analysis, polypharmacy risk.
- **`references/targets-pathways.md`** — targets/enzymes/transporters/carriers,
  drug-target matrices, shared-target repurposing, CYP450, pathways, GO terms.
- **`references/chemical-analysis.md`** — structures, properties, similarity,
  fingerprints, Lipinski/Veber, ADMET heuristics, chemical space.
