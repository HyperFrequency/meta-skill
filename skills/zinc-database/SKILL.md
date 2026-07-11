---
name: zinc-database
version: 0.1.0
description: >-
  Query ZINC22 — the free UCSF Irwin/Shoichet-lab catalog of billions of make-on-demand
  and hundreds of millions of in-stock purchasable compounds — through the CartBlanche22
  API and the files.docking.org repository. Look up substances by ZINC ID, run SMILES
  exact/similarity/analog searches, resolve supplier catalog codes, pull random
  property-filtered samples, and download 3D-ready structures (db2/mol2/sdf) for
  molecular docking and virtual screening. Use when building a docking library, finding
  purchasable analogs of a hit compound, or sampling chemical space for lead discovery.
  NOT for bioactivity/assay data (use ChEMBL or PubChem), experimental protein structures
  (use the PDB), de novo molecule generation, or ADMET/property prediction — ZINC is a
  purchasability-and-structure catalog, not an activity or modeling database.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# ZINC Database (ZINC22 / CartBlanche22)

## Overview

ZINC is a free catalog of commercially available compounds maintained by the Irwin and
Shoichet labs at UCSF, built for ligand discovery and structure-based virtual screening.
The current release, **ZINC22**, spans billions of make-on-demand molecules plus hundreds
of millions of in-stock compounds, each annotated with supplier catalogs and available as
3D-ready structures for docking.

Use this skill to reach ZINC22 programmatically: resolve ZINC IDs to SMILES and vendors,
search by structure, sample chemical space, and stage 3D files for a docking campaign.
For the exact endpoint grammar, output-field lists, and tranche encoding, see
`references/api_reference.md`. For end-to-end recipes (docking-library prep, analog hunts,
RDKit post-processing, DOCK6/Vina wiring), see `references/workflows.md`.

## When to Use This Skill

- **Building a docking library** — assembling a property-filtered set of 3D structures
  for AutoDock Vina, DOCK6, Glide, or similar.
- **Analog discovery** — finding purchasable compounds structurally similar to a hit or
  lead via SMILES similarity search.
- **Purchasability checks** — confirming a molecule is buyable and identifying which
  vendors carry it, by ZINC ID or supplier catalog code.
- **Chemical-space sampling** — drawing random fragment/lead-like/drug-like sets for
  benchmarking, decoy generation, or diversity analysis.
- **Batch ID resolution** — mapping large lists of ZINC IDs to SMILES and catalog info.

## When NOT to Use This Skill

- **Bioactivity, assay, or IC50/Ki data** — ZINC has none; use ChEMBL or PubChem BioAssay.
- **Experimental 3D protein/complex structures** — use the PDB; ZINC covers small-molecule
  ligands only.
- **De novo generation or property/ADMET prediction** — ZINC is a lookup catalog, not a
  generative or predictive model. Pair it with a cheminformatics toolkit downstream.
- **Guaranteed availability or pricing** — ZINC explicitly disclaims compound quality and
  availability; verify with the vendor before ordering (see Data Quality below).
- **Generic named-database lookups** where you don't need chemistry-specific search — use
  `database-lookup`.

## The ZINC22 Service Ecosystem

ZINC22 is not a single API. Different query types route to different docking.org services.
Pick the service that matches the search:

| Service | Host | Best for |
|---|---|---|
| **CartBlanche22** | `cartblanche22.docking.org` | ZINC-ID lookup, exact/analog SMILES, supplier codes, random sampling |
| **SmallWorld** | `sw.docking.org` | Fast nearest-neighbor **similarity** search across billions of compounds |
| **Arthor** | `arthor.docking.org` | **Substructure** and SMARTS pattern search |
| **File repository** | `files.docking.org` / `files22.docking.org` | Bulk 3D structure downloads (db2/mol2/sdf), organized by tranche |

CartBlanche22 covers the everyday programmatic queries below. For very large similarity or
substructure sweeps, prefer SmallWorld / Arthor — their exact query syntax is documented at
`wiki.docking.org`.

## Core Query Capabilities (CartBlanche22)

CartBlanche22 returns TSV (`.txt`) or JSON (`.json`) with a customizable `output_fields`
list. Four query types cover most use:

1. **By ZINC ID** — resolve one or many IDs to SMILES, supplier codes, catalogs, tranche.
2. **By SMILES** — exact match, or analog search via a Tanimoto `dist` / `adist` threshold.
3. **By supplier code** — map a vendor catalog number to ZINC IDs and structures.
4. **Random sample** — draw N compounds, optionally filtered to a named `subset`.

One example per type (exact URL grammar and all parameters are in
`references/api_reference.md`):

```bash
# 1. Resolve ZINC IDs -> SMILES + catalogs (TSV)
curl "https://cartblanche22.docking.org/substances.txt:zinc_id=ZINC000000000001,ZINC000000000002&output_fields=zinc_id,smiles,catalogs"

# 2. Analog search: compounds within Tanimoto distance 3 of ibuprofen
curl "https://cartblanche22.docking.org/smiles.txt:smiles=CC(C)Cc1ccc(cc1)C(C)C(=O)O&dist=3&output_fields=zinc_id,smiles,catalogs"

# 3. Supplier catalog code -> ZINC IDs
curl "https://cartblanche22.docking.org/catitems.txt:catitem_id=SUPPLIER-12345&output_fields=zinc_id,smiles,supplier_code"

# 4. Random 1000 lead-like molecules
curl "https://cartblanche22.docking.org/substance/random.txt:count=1000&subset=lead-like&output_fields=zinc_id,smiles,tranche"
```

> **Grammar caveat:** CartBlanche's URL grammar (the `endpoint.ext:param=value` form, and
> POST/file-upload for large batches) has shifted between releases. Treat the patterns here
> as a documented starting point and confirm against the live app and `wiki.docking.org`
> before scripting at scale. Capabilities are stable; the exact URL spelling may not be.

**Common `output_fields`:** `zinc_id`, `smiles`, `sub_id`, `supplier_code`, `catalogs`,
`tranche`. Request only what you need. Full field table in `references/api_reference.md`.

## Subsets and Tranches

**Named subsets** narrow a random draw to a drug-discovery regime:

- `fragment` — MW < 250; for fragment-based discovery.
- `lead-like` — MW 250–350, LogP ≤ 3.5; typical screening start.
- `drug-like` — MW 350–500; Lipinski-compliant.

**Tranches** are ZINC's physicochemical bins (roughly heavy-atom-count / molecular-weight ×
LogP), and the 3D file repository is laid out by tranche code so you can download exactly
the property window you want. The exact tranche-code encoding has changed across ZINC
versions — see `references/api_reference.md` for the documented parse and its caveat.

## 3D Structures for Docking

3D-ready files live under the file repository, organized by tranche, in DOCK (`.db2.gz`),
MOL2 (`.mol2.gz`), SDF (`.sdf.gz`), and SMILES (`.smi`) formats. Download single tranches
with `wget`, or many in parallel with `aria2c`. Full directory layout, format table, batch
download recipes, and docking-engine wiring (DOCK6, AutoDock Vina) are in
`references/workflows.md`.

Post-process retrieved SMILES with RDKit or OpenBabel to canonicalize, filter by computed
descriptors, embed 3D conformers, and write SDF — recipes in `references/workflows.md`.

## Data Quality and Etiquette

ZINC states plainly: *"We do not guarantee the quality of any molecule for any purpose and
take no responsibility for errors arising from the use of this database."* Practical
consequences:

- **Verify before ordering** — supplier catalogs change; confirm availability and pricing
  with the vendor, especially for make-on-demand compounds.
- **Validate structures** — SMILES may under-specify stereochemistry; re-perceive with
  RDKit/OpenBabel and cross-check against PubChem/ChEMBL where it matters.
- **Be a polite client** — space out requests (~1 s), prefer batch queries over many
  single lookups, cache locally, and run large bulk downloads off-peak. Retry with
  exponential backoff on timeouts (helper in `references/api_reference.md`).
- **Respect scope** — ZINC is aimed at academic/research use; check licensing and your
  institution's procurement rules before commercial use or ordering patented matter.

## References

- `references/api_reference.md` — endpoint grammar, parameter tables, output fields,
  tranche encoding, file-repository layout and formats, SmallWorld/Arthor pointers, rate
  limiting, retry/error handling, and ZINC22/20/15 version differences.
- `references/workflows.md` — worked recipes: docking-library prep, analog discovery,
  batch retrieval, chemical-space sampling, plus Python helpers and RDKit / OpenBabel /
  DOCK6 / AutoDock Vina integration.

Sibling skills: `database-lookup` for generic named-database access; `citation-management`
and `research-lookup` for the surrounding literature. For bioactivity or protein-structure
context, reach for the ChEMBL/PubChem and PDB skills.

## Citation

Cite the ZINC version you used:

- **ZINC22** — Tingle, B. I. *et al.* "ZINC-22 — A Free Multi-Billion-Scale Database of
  Tangible Compounds for Ligand Discovery." *J. Chem. Inf. Model.* 2023, 63, 1166–1176.
- **ZINC15** — Sterling, T.; Irwin, J. J. "ZINC 15 — Ligand Discovery for Everyone."
  *J. Chem. Inf. Model.* 2015, 55, 2324–2337.

Resources: `https://zinc.docking.org/` · `https://cartblanche22.docking.org/` ·
`https://wiki.docking.org/` · `https://github.com/docking-org/`
