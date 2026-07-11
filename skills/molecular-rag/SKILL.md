---
name: molecular-rag
version: 0.1.0
description: >-
  Retrieval-augmented grounding for molecular property prediction: given a query
  SMILES, retrieve structurally similar compounds that carry experimentally
  measured properties and bioactivities from ChEMBL, so an LLM's property claims
  are checked against real assay data instead of hallucinated. Uses ECFP4/Morgan
  fingerprints, Tanimoto similarity, and the ChEMBL similarity + activity REST
  endpoints; supports target-specific analog search (activity against a given
  CHEMBL target) and SAR-context retrieval. Use before predicting a property,
  during lead optimization (what modifications worked on a similar scaffold), for
  novelty checks, or to ground structure-activity reasoning in real data. Do NOT
  use to bulk-dump a database (use `bioservices` / `database-lookup`), to generate
  new chemistry de novo, as the property predictor itself (use `admet-prediction`),
  or when the query has no near-neighbors in ChEMBL — retrieval then returns
  nothing to ground on. After MolRAG (Xian et al., 2025).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "RDKit BSD-3-Clause; ChEMBL data CC BY-SA 3.0"
---

# Molecular RAG

## Overview

Language models confidently hallucinate molecular properties — "this amide should
have clean hERG," "this analog is novel," "IC50 is probably sub-micromolar" — with
no evidence behind the claim. This skill supplies the missing evidence. Given a
query SMILES, it retrieves structurally similar compounds that already have
**experimentally measured** properties and bioactivities in ChEMBL, so a
prediction can be checked against what actually happened to close neighbors in
real assays.

This is retrieval-augmented generation (RAG) for chemistry, following **MolRAG**
(Xian et al., 2025): instead of asking a model to recall a property, you retrieve
analogs with known values and let their measured data anchor the reasoning. The
retrieval pipeline is standard cheminformatics — ECFP4 (Morgan radius-2)
fingerprints, Tanimoto similarity, and ChEMBL's similarity + activity REST
services — not a black box.

**This file is a router.** Depth lives in `references/`:

- `references/retrieval-pipeline.md` — the fingerprint → similarity → activity
  flow, threshold semantics, target-specific and SAR-context modes, and the RAG
  prompt pattern that turns retrieved analogs into a grounded answer.
- `references/chembl-api.md` — the exact ChEMBL endpoints, query params, response
  fields, pagination, SMILES URL-encoding, rate limits, and error handling.
- `references/reference-implementation.md` — a runnable `retrieve_analogs.py`
  (RDKit + `requests`) with CLI, output JSON schema, and worked examples.

## When to Use This Skill

- **Before predicting a property.** Pull analogs with measured values first, then
  reason from real data rather than model priors.
- **Lead optimization.** Find what modifications worked on a similar scaffold —
  which substitutions improved potency or fixed a liability in analogous series.
- **Novelty assessment.** Check whether a generated or proposed molecule is truly
  new or already sits in ChEMBL (a near-identity hit means "known compound").
- **SAR grounding.** Anchor a structure-activity argument in retrieved
  bioactivity records instead of asserting a trend.
- **Target-specific triage.** Retrieve similar compounds with recorded activity
  **against a specific CHEMBL target** to estimate a plausible activity range.

## When NOT to Use This Skill

- **Bulk database export / systematic queries.** If you want every compound in a
  target class, a full assay table, or a large download, hit the source directly
  via `bioservices` (ChEMBL/UniChem clients) or `database-lookup`. This skill
  retrieves a small, similarity-ranked neighborhood, not a dump.
- **De novo generation.** This skill *retrieves* existing molecules; it does not
  invent new chemical matter. Use a generative cheminformatics tool for that.
- **As the property predictor itself.** Retrieval supplies evidence; it does not
  output a score. To compute ADMET/QSAR values use `admet-prediction`; to reason
  about a liability's mechanism use `admet-reasoning`.
- **When the query has no near-neighbors.** For a genuinely novel scaffold, a
  high threshold returns an empty set — there is nothing to ground on. Lower the
  threshold cautiously (see boundaries below) or accept that RAG cannot help here.
- **Absolute quantitative claims.** Retrieved analog activity is context (assay,
  species, conditions vary); it bounds a plausible range, it is not a measurement
  of *your* compound.

## How Retrieval Works

For a query SMILES the pipeline:

1. **Parses and canonicalizes** the query with RDKit (`Chem.MolFromSmiles` →
   `Chem.MolToSmiles`); an invalid SMILES stops here with an error.
2. **Similarity search.** Calls the ChEMBL similarity endpoint at the requested
   threshold (a Tanimoto percentage, minimum 40%) to get candidate molecules with
   their `molecule_properties` (MW, ALogP, HBA, HBD, PSA).
3. **Local re-scoring.** Recomputes ECFP4 Tanimoto between query and each hit so
   similarities are self-consistent and rankable, independent of server rounding.
4. **Activity retrieval (optional).** For each analog, fetches ChEMBL
   `activity` records — `standard_type` / `standard_value` / `standard_units` /
   `standard_relation` / `pchembl_value` / target — to attach measured data.
5. **Target mode (optional).** Filters retrieved analogs to those with activity
   against a given `target_chembl_id`, returning an activity range for that target.

The output is a similarity-ranked JSON list of analogs with properties and,
optionally, bioactivities. The full flow, threshold semantics, and the RAG prompt
pattern (how to feed analogs back to a model to ground its answer) are in
`references/retrieval-pipeline.md`.

## Quick Start

Reference implementation (full source and output schema in
`references/reference-implementation.md`):

```bash
pip install rdkit requests            # modern wheels ship as `rdkit`, not `rdkit-pypi`

# 1. similar compounds with known physchem properties
python retrieve_analogs.py \
    --smiles "O=C(Nc1ccccc1)c1ccccc1Cl" \
    --similarity-threshold 0.6 --max-results 20 --output analogs.json

# 2. attach measured bioactivities to each analog (SAR context)
python retrieve_analogs.py --smiles "O=C(Nc1ccccc1)c1ccccc1Cl" \
    --include-activities --output sar_context.json

# 3. analogs with recorded activity against a specific target
python retrieve_analogs.py --smiles "O=C(Nc1ccccc1)c1ccccc1Cl" \
    --target CHEMBL25 --output target_analogs.json
```

`--similarity-threshold` is a Tanimoto fraction in `[0.4, 1.0]` (it maps to
ChEMBL's integer percentage; anything below 0.4 is rejected by the service).

## Failure Modes & Boundaries

- **Empty result set.** High threshold + novel scaffold → no hits. This is a
  correct answer ("no close analogs"), not a bug — do not silently drop the
  threshold to force results; a distant analog grounds nothing.
- **Threshold floor.** ChEMBL similarity search **requires threshold ≥ 40%**.
  Requests below that error; the script clamps and warns.
- **SMILES must be URL-encoded.** Characters like `#`, `+`, `/`, and `\` in a
  SMILES break a naive path-interpolated URL. Encode the query, or use the POST
  form for long/complex structures (see `references/chembl-api.md`).
- **Rate limits.** ChEMBL is a shared public service. Batch activity lookups pace
  requests (short sleeps) and should retry with backoff on HTTP 429/5xx; fetching
  activities for many analogs is the slow path.
- **Activity is heterogeneous.** `standard_type`/`units` vary across assays;
  compare like-for-like (e.g. only `IC50` in `nM`) and prefer `pchembl_value` for
  a normalized potency. Watch `standard_relation` (`>`, `<`) — a censored value is
  not an equality.
- **Data licensing.** ChEMBL records are CC BY-SA 3.0; attribute if you
  redistribute retrieved data.

## Related Skills

- `admet-prediction` — compute the ADMET/property scores this skill grounds.
- `admet-reasoning` — interpret the mechanism behind a retrieved analog's liability.
- `binding-affinity` — rank/rescore poses once analogs point at a target.
- `bioservices` / `database-lookup` — direct, bulk ChEMBL/PubChem/UniChem access
  when you need full tables rather than a similarity neighborhood.
- `rdkit` / `datamol` — the cheminformatics engines behind fingerprints and SMILES.
- `deepchem` — ML cheminformatics if you move from retrieval to learned predictors.
