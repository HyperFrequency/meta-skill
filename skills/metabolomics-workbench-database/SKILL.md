---
name: metabolomics-workbench-database
version: 0.1.0
description: >-
  Query the NIH Metabolomics Workbench REST API (hosted at UCSD; 4,200+
  processed studies, most public) over plain HTTPS GETs — no key, no install.
  Look up metabolites/structures by identifier (PubChem CID, InChIKey,
  KEGG/HMDB/ChEBI/LIPID MAPS ID, formula, regno), standardize names and pull
  classification via RefMet, search studies by metabolite/investigator/disease,
  retrieve study metadata and data tables (mwTab/JSON/txt), run precursor m/z
  searches against MB/LIPIDS/RefMet with adducts and tolerance, and fetch
  gene/protein records. Use when you need public metabolomics study data, a
  RefMet-standardized name, or MS m/z-to-compound candidates. NOT for enzyme
  kinetics (`brenda-database`), drug bioactivity (`chembl-database`,
  `drugbank-database`), flux modeling (`cobrapy`), cheminformatics on returned
  MOL/SMILES (`rdkit`, `datamol`), a federated multi-database client
  (`bioservices`), or formatting a study's literature refs
  (`citation-management`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Metabolomics Workbench Database

## Overview

The Metabolomics Workbench (MW) is the NIH Common Fund repository for
metabolomics data, hosted at UC San Diego. It holds 4,200+ processed studies
(the large majority public) across GC-MS, LC-MS, and NMR platforms, plus
**RefMet** — a standardized metabolite nomenclature with a four-level chemical
classification.

Access is a simple, unauthenticated **REST API**: every query is one HTTPS GET
built from a fixed URL grammar, returning JSON (default) or tab-delimited text.
No API key, no SDK, no rate-limit ceremony. The skill is knowing the URL grammar,
the seven contexts, and the response shapes — not writing a client.

## When to Use This Skill

- You have a metabolite identifier (PubChem CID, InChIKey, KEGG/HMDB/ChEBI/LIPID
  MAPS ID, formula, or MW `regno`) and want its structure, cross-references, or
  MOL/PNG image.
- You need to **standardize a metabolite name** or get its super/main/sub class
  via RefMet before joining datasets.
- You want to **find public studies** measuring a metabolite, run by an
  investigator/institute, or matching a disease + platform filter.
- You need a study's **metadata or experimental data table** (summary, factors,
  analysis, metabolites, data, or full mwTab).
- You have an MS **m/z peak** and want candidate compounds for a given ion adduct
  and tolerance, or the exact mass of a known metabolite for a chosen adduct.
- You want **gene/protein records** (MGP database) tied to metabolic enzymes.

## When NOT to Use This Skill

- You need experimental **enzyme kinetics** (Km, kcat, inhibition) — use
  `brenda-database`.
- You want **drug bioactivity / targets / clinical drug data** — use
  `chembl-database` or `drugbank-database`.
- You have pathway/stoichiometry data and want **genome-scale flux / FBA** — use
  `cobrapy`.
- You want to **manipulate the returned structures** (parse MOL/SMILES, compute
  descriptors, standardize, draw) — use `rdkit` or `datamol`.
- You want **one Python API over many bio databases** (KEGG, ChEBI, UniProt,
  etc.) — use `bioservices`.
- You need to turn a study's **literature references into citations/BibTeX** —
  use `citation-management`.
- The datum lives natively elsewhere — protein sequences/structures in
  UniProt/PDB, full pathways in KEGG — MW only mirrors the identifiers. Follow
  the cross-reference out.

## API Shape

Every request follows one path grammar off a single base URL:

```
https://www.metabolomicsworkbench.org/rest/<context>/<input_item>/<input_value>/<output_item>/<format>
```

- `context` — one of `compound`, `study`, `refmet`, `metstat`, `moverz`,
  `gene`, `protein`.
- `input_item` / `input_value` — what you search by, and the value.
- `output_item` — what to return (`all`, `name`, `summary`, `data`, `png`, ...).
- `format` — `json` (default if omitted) or `txt` (tab-delimited).

`moverz` and `metstat` use their own positional grammars (below). URL-encode
values with spaces or slashes (`Fatty%20Acids`).

```python
import requests

BASE = "https://www.metabolomicsworkbench.org/rest"
r = requests.get(f"{BASE}/compound/pubchem_cid/5281365/all/json", timeout=30)
r.raise_for_status()
compound = r.json()
```

## The Seven Contexts

| Context | Purpose | Representative call |
| --- | --- | --- |
| `compound` | Metabolite structure/IDs; cross-reference between databases; MOL/PNG | `/compound/regno/11/all/json` |
| `study` | Study metadata + experimental data; list, search, download mwTab | `/study/study_id/ST000001/summary/json` |
| `refmet` | Standardize names; query by formula/mass/InChIKey; class hierarchy | `/refmet/match/citrate/name/json` |
| `metstat` | Filter studies by analysis type, polarity, chromatography, species, source, disease, metabolite | `/metstat/LCMS;POSITIVE;HILIC;Human;Blood;Diabetes/json` |
| `moverz` | Precursor m/z search (MB/LIPIDS/REFMET) with adduct + tolerance; exact-mass calc | `/moverz/MB/635.52/M+H/0.5/json` |
| `gene` | MGP gene records by symbol/ID/name | `/gene/gene_symbol/ACACA/all/json` |
| `protein` | MGP protein records + sequences by UniProt/RefSeq/symbol | `/protein/uniprot_id/Q13085/all/json` |

Full input-item / output-item tables per context, the `metstat` eight-position
layout, the complete ion-adduct list, and error/rate-limit notes are in
[references/api-reference.md](references/api-reference.md).

## Common Workflows

**Find studies for a metabolite** — standardize first, then search, then pull
data. Skipping RefMet is the top cause of empty study results.

```python
name = requests.get(f"{BASE}/refmet/match/glucose/name/json").json()["name"]      # -> "Glucose"
studies = requests.get(f"{BASE}/study/refmet_name/{name}/summary/json").json()
data = requests.get(f"{BASE}/study/study_id/ST000001/data/json").json()
```

**Identify a compound from an m/z peak** — match, then inspect candidates by
`regno`, then confirm structure. Use the adduct matching your ionization mode.

```python
hits = requests.get(f"{BASE}/moverz/MB/180.0634/M+H/0.01/json").json()            # high-res tolerance
info = requests.get(f"{BASE}/compound/regno/{regno}/all/json").json()
png  = requests.get(f"{BASE}/compound/regno/{regno}/png").content                 # bytes, not JSON
```

**Explore disease-specific metabolomics** — filter with `metstat`, then drill in.
Empty positions (consecutive `;`) skip a parameter; all are optional.

```python
matches = requests.get(f"{BASE}/metstat/LCMS;POSITIVE;;Human;;Cancer/json").json()
```

More recipes (batch identifier lookup, RefMet class enumeration, mwTab download
and parsing) are in [references/api-reference.md](references/api-reference.md).

## Failure Modes and Gotchas

- **No key, but be polite.** MW does not enforce strict rate limits, but throttle
  bulk loops (`time.sleep(~0.2-0.5)`) and **cache** the big reference pulls
  (`/refmet/all`, `/study/study_id/ST/available`) locally.
- **Response shape varies.** Single-result endpoints return a flat object;
  multi-result endpoints often return a JSON object **keyed by row-number
  strings** (`"1"`, `"2"`, ...), not a list. Normalize before iterating —
  `list(payload.values())` if the top-level keys are numeric strings.
- **Empty result is not an HTTP error.** Missing data typically returns an empty
  `[]`/`{}` with status 200, not a 404. Check for emptiness explicitly rather
  than trusting `raise_for_status()`.
- **Non-JSON outputs.** `png` returns image **bytes** and `molfile`/`mwtab`
  return **text** — read `.content` / `.text`, not `.json()`.
- **`regno` is MW-internal.** The registry number is only valid within MW and
  is not stable across releases; resolve from a durable ID (InChIKey, PubChem
  CID) when persisting references.
- **Adduct and tolerance must match the assay.** Use `M+H`/`M+Na`/`M+NH4` for
  positive ESI, `M-H`/`M+FA-H` for negative; ~0.5 Da tolerance for low-res,
  ~0.01 Da for high-res. See the adduct table in the reference.
- **RefMet class names are exact.** Filtering by `main_class`/`sub_class`
  requires the canonical, URL-encoded class string (`Fatty%20Acids`); enumerate
  from `/refmet/all` if unsure.

## References

- [references/api-reference.md](references/api-reference.md) — per-context input
  and output item tables (`compound`, `study`, `refmet`, `gene`, `protein`), the
  `metstat` eight-position filter layout, the `moverz` m/z-search and
  exact-mass grammars with the full positive/negative/uncharged ion-adduct
  tables, output formats, HTTP error handling, rate-limit guidance, response-shape
  normalization, worked multi-step recipes, and pointers to the official
  MW REST spec and the `mwtab` (Python) / `metabolomicsWorkbenchR` (Bioconductor)
  / `MetabolomicsWorkbenchAPI.jl` client libraries.
