---
name: opentargets-database
version: 0.1.0
description: >-
  Query the Open Targets Platform GraphQL API for therapeutic target-disease
  associations, drug-target discovery, and the typed evidence behind them (human
  genetics, somatic mutations, known drugs, pathways, RNA expression, animal
  models, literature). Use to find and rank candidate targets for a disease,
  assess a gene's tractability/druggability and safety liabilities, pull the
  evidence for a specific target-disease pair, look up known or clinical-stage
  drugs and their mechanisms for an indication, or surface drug-repurposing
  leads. Resolve names to Ensembl gene IDs, EFO disease IDs, and ChEMBL drug IDs
  via the search endpoint first. NOT for bulk/systematic scans over many targets
  or diseases (use Open Targets BigQuery or FTP downloads), compound
  bioactivity/SAR (use chembl-database), clinical variant curation
  (clinvar-database), pharmacogenomic dosing (clinpgx-database), or protein
  structures (alphafold-database).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Open Targets Database

## Overview

The Open Targets Platform systematically identifies and prioritizes potential
drug targets by integrating human genetics, omics, chemical, and literature data
into scored **target-disease associations**. Every association is backed by
typed evidence, and every target and disease carries a rich annotation layer
(tractability, safety, genetic constraint, expression, known drugs).

This skill drives the platform's public **GraphQL API** for programmatic,
exploratory queries. The API needs no authentication and is best for single-
entity and small-batch lookups. Three ID namespaces run through everything:

- **Targets** → Ensembl gene IDs (e.g. `ENSG00000157764` for BRAF)
- **Diseases** → EFO-ontology IDs; most are now **MONDO** terms
  (e.g. `MONDO_0004975` for Alzheimer disease). The query argument is still
  named `efoId`, but pass whatever ID `search` returns — many legacy `EFO_...`
  codes have been remapped and no longer resolve.
- **Drugs** → ChEMBL IDs (e.g. `CHEMBL25` for aspirin)

Almost every task starts by resolving a human name to one of these IDs via the
`search` endpoint, then querying `target`, `disease`, or `drug`. Never guess an
ID from memory — the current release's IDs differ from older ones.

## When to Use This Skill

- **Target discovery** — find and rank candidate targets for a disease by
  association score, then drill into the evidence.
- **Target assessment** — evaluate a gene's tractability across modalities
  (small molecule, antibody, PROTAC), safety liabilities, and genetic constraint.
- **Evidence gathering** — pull the typed evidence records (with source, score,
  study, and literature) supporting a target-disease association.
- **Known-drug / clinical-precedence lookup** — list drugs indicated for a
  disease with their targets, mechanism of action, and clinical trial phase.
- **Drug intelligence** — retrieve a drug's mechanisms, indications, max clinical
  phase, and withdrawal notices.
- **Drug repurposing** — traverse disease → known drugs → mechanisms → related
  indications to surface repurposing hypotheses.

## When NOT to Use This Skill

- **Systematic analyses over many targets/diseases** — the API is tuned for
  exploratory single-entity queries; for whole-dataset work use Open Targets
  **BigQuery** or the **FTP data downloads**, not repeated API calls.
- **Compound bioactivity, SAR, or drug-likeness** — use `chembl-database`; Open
  Targets links drugs to targets but is not a bioactivity store.
- **Clinical variant interpretation** — use `clinvar-database` for pathogenicity
  curation; Open Targets summarizes ClinVar as one evidence source, not the
  primary record.
- **Pharmacogenomic dosing guidance** — use `clinpgx-database`.
- **Gene sequences / genomic coordinates** — use `ensembl-database` or `gget`.
- **Protein structures** — use `alphafold-database` or a PDB skill.
- **Trial registry detail** — use `clinicaltrials-database` for full trial
  records; Open Targets carries phase/status summaries only.

## Endpoint and Quickstart

- **GraphQL endpoint:** `https://api.platform.opentargets.org/api/v4/graphql`
- **Interactive browser (schema explorer):**
  `https://api.platform.opentargets.org/api/v4/graphql/browser`
- **No authentication.** POST `{query, variables}` as JSON.

GraphQL returns **HTTP 200 even on errors** — always inspect the `errors` key.

```python
import requests

URL = "https://api.platform.opentargets.org/api/v4/graphql"

def run(query: str, variables: dict) -> dict:
    resp = requests.post(URL, json={"query": query, "variables": variables}, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]

# Resolve a gene symbol to an Ensembl ID
hits = run(
    """query ($q: String!) {
         search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 5}) {
           hits { id entity name }
         }
       }""",
    {"q": "BRAF"},
)["search"]["hits"]
```

Request **only the fields you need** and paginate list fields with
`page: {index: M, size: N}` — the `Pagination` input requires **both** `index`
and `size`; passing `{size: N}` alone raises a GraphQL error. Full, copy-ready
queries for every capability below live in `references/api-reference.md`.

## Core Capabilities

Each maps to one GraphQL query; see `references/api-reference.md` for the exact
field selections and Python wrappers.

- **Search / ID resolution** — `search(queryString, entityNames, page)` →
  `hits { id, entity, name, description }`. Filter `entityNames` to
  `["target"]`, `["disease"]`, or `["drug"]`.
- **Target profile** — `target(ensemblId)` → `approvedSymbol`, `approvedName`,
  `biotype`, `tractability`, `safetyLiabilities`, `geneticConstraint`,
  `baselineExpression`, `chemicalProbes`, `pathways`,
  `drugAndClinicalCandidates`, `associatedDiseases`.
- **Disease profile** — `disease(efoId)` → `name`, `description`,
  `therapeuticAreas`, `synonyms`, `associatedTargets`,
  `drugAndClinicalCandidates`.
- **Target-disease evidence** — `disease(efoId).evidences(ensemblIds,
  datasourceIds, size)` → per-record `datasourceId`, `datatypeId`, `score`,
  `studyId`, `literature`. Filter server-side by `datasourceIds` (e.g.
  `["eva", "gwas_credible_sets"]`); group by the returned `datatypeId`
  client-side. There is **no `datatypes` argument**.
- **Clinical drugs & candidates** — `disease(efoId).drugAndClinicalCandidates`
  (or `target(ensemblId).drugAndClinicalCandidates`) → `count` and rows with
  `drug`, `maxClinicalStage`, and `clinicalReports { trialPhase,
  trialOverallStatus }`; target rows also carry `diseases`. Replaces the
  removed `knownDrugs` field.
- **Drug profile** — `drug(chemblId)` → `drugType`, `maximumClinicalStage`
  (string, e.g. `"APPROVAL"`, `"PHASE_2"`), `mechanismsOfAction { rows { ... } }`,
  `indications { rows { ... } }`, and `drugWarnings` (withdrawal / black-box
  safety; replaces the removed `hasBeenWithdrawn`/`withdrawnNotice`).
- **All associations for a target** — `target(ensemblId).associatedDiseases(page)`
  → rows with `disease`, overall `score`, and `datatypeScores { id, score }`
  breakdown; filter by `min_score` client-side.

## Interpreting Scores and Evidence

Association scores run **0–1** and aggregate all evidence for a pair via a
**harmonic sum** across data types. They rank *relative* evidence strength — they
are **not** confidence levels or probabilities of clinical success, and
under-studied diseases can score low despite valid biology. Always read the
`datatypeScores` breakdown, not just the headline number.

Weight **human genetic** and **expert-curated** evidence (GWAS with high L2G,
ClinVar pathogenic, ClinGen, Gene2Phenotype) above computational predictions or
sole text-mining hits. Treat single-source or text-mining-only signals as
exploratory. See `references/evidence-types.md` for the seven evidence data
types, their sources, scoring methods, and per-type strengths and caveats.

## Target Prioritization Workflow

1. `search` the disease → EFO ID; query `disease(efoId)` with `associatedTargets`.
2. Rank targets by association `score`, then inspect each target's `datatypeScores`.
3. For promising targets, pull the full `target(ensemblId)` profile.
4. Check **tractability** (clinical precedence ≫ discovery precedence ≫
   predicted) for the modality you intend to pursue.
5. Screen **safety**: `safetyLiabilities`, tissue expression, and
   `geneticConstraint` (high pLI / low LOEUF flags essential genes — a poor
   therapeutic window).
6. Use `drugAndClinicalCandidates` for clinical precedence and mechanism insight.
7. For critical calls, open the primary `studyId` / `literature` behind the
   evidence.

Detailed annotation semantics, red-flag / green-flag heuristics, and the full
target-profile query are in `references/target-annotations.md`.

## Boundaries and Gotchas

- The platform ships a **new data release ~quarterly**; field availability and
  scores shift between releases. Note the release when caching results.
- GraphQL 200-on-error means silent failures unless you check `errors`.
- `evidences` can return large result sets — bound with `size` / pagination.
- IDs are case- and format-sensitive: `MONDO_0004975` / `EFO_...` (underscore),
  `ENSG...`, `CHEMBL...`. Resolve via `search` rather than guessing — legacy
  disease IDs have been remapped between releases.
- For anything touching hundreds of entities, switch to BigQuery / downloads
  (see `references/api-reference.md`) to avoid rate issues and partial data.

## References

- `references/api-reference.md` — endpoint, access methods (GraphQL / web /
  BigQuery / FTP), query structure, full example queries for every capability,
  pagination, error handling, and citation/licensing.
- `references/evidence-types.md` — the seven evidence data types, their data
  sources, scoring methodologies, and interpretation guidelines.
- `references/target-annotations.md` — the twelve target annotation categories
  (tractability, safety, constraint, expression, essentiality, cancer, etc.),
  the comprehensive target-profile query, and prioritization red/green flags.

## Citation

Cite the current platform paper when using Open Targets data:
Ochoa, D. et al. (2025) *Open Targets Platform: facilitating therapeutic
hypotheses building in drug discovery.* Nucleic Acids Research, 53(D1):D1467–D1477.
Data is freely available; check <https://platform-docs.opentargets.org/release-notes>
for the active release.
