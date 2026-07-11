---
name: hmdb-database
version: 0.1.0
description: >-
  Access the Human Metabolome Database (HMDB 5.0): ~220,945 small-molecule
  metabolites with chemical structures, physicochemical properties,
  normal/abnormal biofluid concentrations, disease and biomarker associations,
  metabolic pathways, enzyme/transporter links, and reference NMR/MS/MS-MS
  spectra. Use when identifying metabolites from untargeted LC-MS, GC-MS, or NMR
  data, mining disease biomarkers, mapping metabolites to pathways, or
  cross-referencing to KEGG/PubChem/ChEBI/DrugBank. Covers web/ChemQuery search,
  bulk XML/SDF/CSV downloads, memory-safe streaming XML parsing, and the R
  `hmdbQuery` package (HMDB exposes no public REST API). NOT for building the
  spectral-processing pipeline itself (use `matchms` or `pyopenms`),
  cheminformatics on the structures (use `rdkit`), or non-human, food, or toxin
  compounds — reach for FooDB, T3DB, or a general `database-lookup` instead.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# HMDB Database

## Overview

The Human Metabolome Database (HMDB) is a freely available, expert-curated
reference for small-molecule metabolites found in the human body. It couples
each compound to its chemical identity, physiological context (where it occurs
and at what concentration), clinical associations, metabolic pathways, and
experimental/predicted reference spectra. HMDB is the canonical annotation
source for human metabolomics and clinical chemistry.

This skill routes you to the right access method for a task, names the exact
identifiers and fields you will encounter, and delegates deep field definitions
and parsing recipes to `references/`.

Current release: **HMDB 5.0** (~220,945 metabolite entries, ~8,610 protein
sequences, 130+ fields per entry). Cite Wishart et al., "HMDB 5.0: the Human
Metabolome Database for 2022," *Nucleic Acids Research* 50:D622–D631 (2022).

## When to Use This Skill

- Annotating or identifying metabolites from untargeted **LC-MS, GC-MS, or NMR**
  experiments (match m/z, MS-MS fragments, or chemical shifts to references).
- Discovering **biomarkers**: finding metabolites associated with a disease and
  their normal vs. abnormal concentration ranges in a given biofluid.
- **Pathway analysis**: mapping a metabolite list to metabolic pathways,
  enzymes, transporters, and reactions (via linked SMPDB/KEGG).
- **Cross-referencing** an HMDB accession, InChIKey, or SMILES to external IDs
  (KEGG, PubChem, ChEBI, ChemSpider, DrugBank, MetaCyc, METLIN).
- Building a **local metabolite reference table** from bulk downloads for a
  data pipeline.

## When NOT to Use This Skill

- You need to run the **spectral-processing pipeline** (peak picking, alignment,
  spectral similarity scoring) — use `matchms` or `pyopenms`; HMDB only supplies
  the reference spectra and metadata.
- You need **cheminformatics** on the structures themselves (fingerprints,
  substructure search, standardization) — parse HMDB's SMILES/InChI/SDF with
  `rdkit`, or validate strings with `smiles-validation`.
- The compound is a **food component, drug, or toxin** outside the human
  metabolome — use FooDB, DrugBank (`drugbank-database`), or T3DB. HMDB includes
  drug metabolites but is not a drug database.
- You want **bioactivity/assay data** for a target — use `chembl-database`.
- You just need a quick fact from any named scientific database with no HMDB
  specifics — use the general `database-lookup` skill.

## HMDB Identifiers

| ID form | Example | Notes |
| --- | --- | --- |
| Metabolite accession | `HMDB0000001` | 7-digit, zero-padded (HMDB 4.0+). |
| Legacy accession | `HMDB00001` | 5-digit pre-4.0 form; still resolves as a secondary accession. |
| Protein accession | `HMDBP00001` | Enzymes/transporters. |
| InChIKey | `BRMWTNUJHUMWMS-UHFFFAOYSA-N` | Best key for structure-based lookup and dedup. |

Always record the exact HMDB IDs and the HMDB version in any analysis you
publish; accessions can be merged across releases (old IDs survive as
`secondary_accessions`).

## Accessing HMDB

HMDB has **no public REST API**. There are three practical access paths; pick by
scale.

### 1. Web interface — interactive, low volume

Browse and search at `https://www.hmdb.ca/`:

- **Text search** by name, synonym, HMDB ID, disease, or pathway.
- **ChemQuery** for structure/substructure search and molecular-weight ranges;
  accepts SMILES or InChI.
- **Spectral search** (LC-MS, GC-MS, NMR) to match experimental spectra against
  references, and **MS/MS search** for fragmentation matching.
- Per-entry data is downloadable as XML at
  `https://www.hmdb.ca/metabolites/HMDB0000001.xml`.

### 2. Bulk downloads — the standard programmatic path

Download whole datasets from `https://www.hmdb.ca/downloads` and parse locally.
This is the recommended route for any large-scale or reproducible work — do not
scrape per-entry pages in a loop.

- **XML** — complete metabolite/protein/spectra data (multi-GB uncompressed;
  parse with a streaming parser, never load whole).
- **SDF** — structures for cheminformatics (`rdkit`).
- **CSV/TSV** — flat tables for pipelines.
- **FASTA** — protein/gene sequences. **TXT** — raw spectral peak lists.

See `references/access-and-parsing.md` for the memory-safe streaming XML recipe,
SDF/CSV handling, and cross-database ID-mapping notes.

### 3. R / Bioconductor — single-entry queries

The Bioconductor `hmdbQuery` package fetches and parses individual metabolite
XML records over HTTP. Install with `BiocManager::install("hmdbQuery")` and
retrieve an entry with `HmdbEntry()`. Suitable for tens of lookups, not bulk
harvesting. Details and caveats in `references/access-and-parsing.md`.

For sanctioned high-volume or commercial API access, HMDB directs users to
contact the maintainers (see the license section) — do not build a scraper as a
substitute.

## Data Available Per Metabolite

Each entry spans chemical, biological, clinical, spectroscopic, and
cross-reference fields. Highlights:

- **Chemical**: formula, average & monoisotopic mass, SMILES, InChI, InChIKey,
  IUPAC name, predicted properties (logP, pKa, TPSA, H-bond donors/acceptors),
  and ClassyFire chemical taxonomy.
- **Biological**: origin (endogenous/exogenous/drug/food), biofluid, tissue, and
  subcellular locations.
- **Clinical**: normal and abnormal concentrations per biofluid (with units, age,
  sex), disease associations (with OMIM IDs), and biomarker status.
- **Pathways & enzymes**: SMPDB/KEGG pathways, associated proteins with UniProt
  and gene names, reactions, and kinetics.
- **Spectra**: experimental and predicted NMR (¹H/¹³C, 2D), MS, MS-MS, GC-MS
  with peak lists.
- **Cross-references**: KEGG, PubChem CID/SID, ChEBI, ChemSpider, DrugBank,
  FooDB, MetaCyc, BiGG, METLIN, Wikipedia, and more.

Field completeness is uneven — core chemical fields are near-universal, while
experimental spectra and kinetic data are sparse. Full field-by-field
definitions, the XML schema shape, and completeness tiers are in
`references/data-fields.md`.

## Common Workflows

Condensed here; step-by-step versions with parsing tips are in
`references/access-and-parsing.md`.

- **Untargeted identification**: match experimental m/z (±ppm) or MS-MS/NMR peaks
  against HMDB reference spectra, then confirm candidates by molecular formula,
  biofluid plausibility, and pathway context.
- **Biomarker discovery**: query metabolites linked to the disease, compare
  normal vs. abnormal concentrations, rank by differential abundance, and read
  the pathway/mechanism context.
- **Pathway analysis**: resolve each metabolite to its HMDB entry, extract
  pathway and enzyme associations, and follow SMPDB links for diagrams.
- **Local integration**: bulk-download XML/CSV, extract the fields you need, key
  on InChIKey, and join to external IDs for cross-database queries.

## Related HMDB-Family Databases

HMDB shares structure and identifiers with sibling resources, enabling joined
queries: **DrugBank** (drugs; see `drugbank-database`), **T3DB** (toxins),
**SMPDB** (pathway diagrams), and **FooDB** (food components).

## Licensing and Citation

HMDB is free for academic and non-commercial research. **Commercial use or
redistribution requires explicit permission from the authors**, and downloading
significant portions obligates you to cite the HMDB paper in any resulting
publication. Contact the HMDB team (per the citing page on hmdb.ca) for
commercial licensing or sanctioned API access. Always cite HMDB 5.0 and record
the exact HMDB IDs and version used.

## References

- `references/data-fields.md` — full per-entry field catalogue (chemical,
  biological, clinical, spectral, cross-reference), the XML entry shape, and
  field-completeness tiers.
- `references/access-and-parsing.md` — bulk download formats, memory-safe
  streaming XML parsing, `hmdbQuery` usage, cross-database ID mapping, and
  detailed workflow steps.
