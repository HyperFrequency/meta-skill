---
name: alphafold-database
version: 0.1.1
description: >-
  Retrieve and analyze AI-predicted protein structures from the AlphaFold
  Protein Structure Database (200M+ models, DeepMind + EMBL-EBI). Use when you
  have a UniProt accession (or can map to one) and need the predicted 3D
  structure, its confidence metrics (per-residue pLDDT, inter-residue PAE), or
  bulk proteome downloads — for structural biology, drug-target modeling,
  protein engineering, or feeding structures into docking/pocket-finding.
  Covers the REST API, direct mmCIF/PDB/bCIF/JSON file URLs, the Biopython
  Bio.PDB.alphafold_db convenience layer, Google Cloud (gsutil) + BigQuery bulk
  access, and reading pLDDT out of B-factors. Do NOT use to PREDICT structures
  absent from the DB (use structure-prediction / ESMFold), for protein
  embeddings or generative design (use esm), for experimental structures from
  the wwPDB, or for multi-chain complexes / bound ligands — AlphaFold DB stores
  single-chain apo monomer models only.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: Biopython License Agreement (BSD-3-Clause); AlphaFold DB data CC-BY-4.0
---

# AlphaFold Structure Database

## Overview

The AlphaFold Protein Structure Database (AlphaFold DB) is a public repository of
AI-predicted 3D protein structures covering 200M+ UniProt sequences, produced by
DeepMind and hosted by EMBL-EBI. Every prediction ships with confidence estimates:
**pLDDT** (per-residue reliability, 0–100) and **PAE** (predicted aligned error
between residue pairs). Access is free and unauthenticated.

This skill routes you to the right access path — one structure by ID, a filtered
metadata query, or a whole proteome — and to the confidence interpretation you
need before trusting a model downstream.

## When to Use This Skill

- You have a **UniProt accession** (e.g. `P00520`) and want its predicted structure.
- You need **confidence metrics** (pLDDT, PAE) to decide whether a region is reliable.
- You want to **bulk-download** a proteome or filter models by quality at scale.
- You are feeding predicted structures into docking (`molecular-docking`), pocket
  finding (`pocket-detection`), or comparative/structural analysis.
- You need to **map** a gene name, PDB ID, or protein name to a UniProt accession
  first (via UniProt), then pull the AlphaFold model.

## When NOT to Use This Skill

- **The protein is not in AlphaFold DB** (novel sequence, engineered variant,
  designed protein) — predict it instead with `structure-prediction` (ESMFold).
- **You want embeddings, inverse folding, or generative design** — use `esm`.
- **You need an experimental structure** (X-ray, cryo-EM, NMR) — query the wwPDB,
  not AlphaFold DB. AlphaFold models are computational, not deposited experiments.
- **You need a multi-chain complex, bound ligand, cofactor, or PTM** — AlphaFold DB
  stores only single-chain apo monomers. Use AlphaFold-Multimer / AlphaFold 3
  tooling for complexes.
- **General cross-database lookups** with no structural target — use `database-lookup`.

## Core Concepts

- **UniProt accession** — the query key (e.g. `P00520`). Everything is indexed by it.
- **AlphaFold entry ID** — format `AF-<accession>-F<fragment>` (e.g. `AF-P00520-F1`).
  Large proteins (>2700 residues) are split into overlapping fragments `F1, F2, …`.
- **Version** — the current per-entry release is `v6` (models dated 2025-08); the
  suffix appears in every file URL (`…-model_v6.cif`). Don't hard-code it — read
  `latestVersion` from the API and prefer its `*Url` fields. Note the **bulk
  GCS/BigQuery snapshot still lags at `v4`** (see `references/bulk-access.md`).
- **pLDDT** lives in the **B-factor column** of the coordinate file, so standard
  viewers color by confidence automatically.

## Fetch One Structure

Two equivalent paths. The REST + direct-file path has no dependencies and is the
most robust; the Biopython path is a convenience wrapper (see `biopython`).

**REST metadata, then direct file download:**

```python
import requests

acc = "P00520"
meta = requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{acc}").json()
entry = meta[0]["entryId"]            # "AF-P00520-F1"
cif_url = meta[0]["cifUrl"]           # canonical mmCIF URL from the API response

open(f"{entry}.cif", "wb").write(requests.get(cif_url).content)
```

Prefer the `cifUrl` / `pdbUrl` fields returned by the API over hand-building URLs —
they always point at the latest version. The deterministic URL pattern (for when
you already know the entry ID) and every file type are in
[references/api-reference.md](references/api-reference.md).

**Biopython convenience layer** (`Bio.PDB.alphafold_db`):

```python
from Bio.PDB import alphafold_db

predictions = list(alphafold_db.get_predictions("P00520"))
for pred in predictions:
    cif_path = alphafold_db.download_cif_for(pred, directory="./structures")

# Parsed Structure objects in one step:
structures = list(alphafold_db.get_structural_models_for("P00520"))
```

## Assess Confidence Before Trusting a Model

Never analyze an AlphaFold model without reading its confidence first. Quick thresholds:

| pLDDT   | Meaning                    | Use it for                          |
| ------- | -------------------------- | ----------------------------------- |
| > 90    | Very high                  | Detailed / atomistic analysis       |
| 70–90   | Confident backbone         | Fold, domain topology               |
| 50–70   | Low                        | Caution; often flexible             |
| < 50    | Very low                   | Likely disordered; do not trust     |

| PAE (Å) | Meaning                                             |
| ------- | --------------------------------------------------- |
| < 5     | Confident *relative* positioning of the two residues |
| 5–15    | Moderate                                            |
| > 15    | Uncertain relative placement; domains may be mobile |

pLDDT rates *local* correctness; PAE rates *relative* domain placement — a protein
can have high pLDDT everywhere yet high inter-domain PAE (well-folded domains,
uncertain hinge). The PAE JSON is a one-element list — read the matrix as
`resp[0]["predicted_aligned_error"]`, not a `distance` key. For loading
`confidence_v6.json` / `predicted_aligned_error_v6.json`,
plotting the PAE matrix, extracting pLDDT from B-factors, and batch statistics, see
[references/confidence-and-analysis.md](references/confidence-and-analysis.md).

## Bulk and Filtered Access

For more than a few dozen proteins, do **not** loop the REST API — use Google Cloud:

- **gsutil** — whole proteomes by NCBI taxonomy ID from
  `gs://public-datasets-deepmind-alphafold-v4/`.
- **BigQuery** — SQL over `bigquery-public-data.deepmind_alphafold.metadata` to
  filter by organism, `fractionPlddtVeryHigh`, reviewed status, etc., before you
  download anything.

Bucket layout, proteome download commands (with a subprocess-injection safety note),
and the full BigQuery schema + example queries are in
[references/bulk-access.md](references/bulk-access.md).

## Parse Downloaded Structures

Use Biopython's `MMCIFParser` (see `biopython`). pLDDT is in the B-factor field:

```python
from Bio.PDB import MMCIFParser

structure = MMCIFParser(QUIET=True).get_structure("p", "AF-P00520-F1-model_v6.cif")
plddt = [res["CA"].get_bfactor() for res in structure.get_residues() if "CA" in res]
```

Contact maps, coordinate extraction, and per-protein summary DataFrames are in
[references/confidence-and-analysis.md](references/confidence-and-analysis.md).

## Failure Modes and Gotchas

- **404 from the API** → no AlphaFold prediction exists for that accession. Confirm
  the accession is valid and reviewed; predict with `structure-prediction` instead.
- **Not every UniProt entry is covered.** Very long proteins, some viral/obsolete
  entries, and non-reference isoforms may be absent or fragmented.
- **Fragmented large proteins** return multiple entries (`F1, F2, …`) with overlaps —
  handle all fragments, don't assume `F1` is the whole chain.
- **Single-chain only.** No complexes, ligands, ions, or PTMs in these models.
- **Rate limits.** Cap REST usage (~10 concurrent, add delay); switch to GCS/BigQuery
  for bulk. HTTP 429/503 → back off and retry.
- **prefer bCIF for size** (~70% smaller) but it needs a binary CIF parser; use mmCIF
  for maximum tool compatibility, PDB only for legacy tools (99,999-atom cap).

## References

- [references/api-reference.md](references/api-reference.md) — REST endpoints, full
  response schema, file URL patterns, all file types, confidence/PAE JSON schemas,
  3D-Beacons federated access, HTTP status codes, rate limiting.
- [references/bulk-access.md](references/bulk-access.md) — Google Cloud Storage bucket
  layout, `gsutil` proteome downloads, BigQuery table schema and example queries.
- [references/confidence-and-analysis.md](references/confidence-and-analysis.md) —
  pLDDT/PAE interpretation in depth, PAE visualization, Biopython parsing (contacts,
  B-factor pLDDT), and batch multi-protein processing.

## Attribution and Citation

AlphaFold DB data is released under **CC-BY-4.0**. When you use it in published work, cite:

- Jumper, J. et al. *Highly accurate protein structure prediction with AlphaFold.*
  Nature 596, 583–589 (2021). https://doi.org/10.1038/s41586-021-03819-2
- Varadi, M. et al. *AlphaFold Protein Structure Database in 2024…* Nucleic Acids
  Research 52, D368–D375 (2024). https://doi.org/10.1093/nar/gkad1011

Website: https://alphafold.ebi.ac.uk/ · API docs: https://alphafold.ebi.ac.uk/api-docs
