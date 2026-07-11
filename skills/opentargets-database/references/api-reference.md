# Open Targets Platform — GraphQL API Reference

Field names below are verified against the current live `api/v4` schema. Open
Targets restructures its schema between releases, so if a field errors, confirm
it in the GraphQL browser against the active release.

## Endpoint

```
https://api.platform.opentargets.org/api/v4/graphql
```

Interactive schema explorer / playground:

```
https://api.platform.opentargets.org/api/v4/graphql/browser
```

No authentication is required; all data is free to access.

## Access methods (pick the right one)

| Method | Best for |
| --- | --- |
| **GraphQL API** (this skill) | Single-entity and small-batch, flexible field selection, exploratory queries |
| **Web interface** — `https://platform.opentargets.org` | Manual browsing and sanity checks |
| **FTP downloads** — `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/` | Bulk / systematic analyses across all targets or diseases |
| **Google BigQuery** | Large-scale SQL joins over the full dataset |

Rule of thumb: if you would issue more than a few dozen API calls in a loop,
switch to BigQuery or the downloads instead.

## Request shape

POST JSON `{"query": <string>, "variables": <object>}`. GraphQL returns **HTTP
200 even for errors**, so always check the `errors` key before trusting `data`.

```python
import requests

URL = "https://api.platform.opentargets.org/api/v4/graphql"

def run(query: str, variables: dict | None = None) -> dict:
    resp = requests.post(URL, json={"query": query, "variables": variables or {}}, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload.get("data", {})
```

Best practices:

- Request only the fields you need — response size and latency scale with the
  selection set.
- Use variables (`$ensemblId`, `$efoId`, ...) rather than string interpolation.
- Paginate list fields with `page: {index: M, size: N}`. The `Pagination` input
  requires **both** `index` and `size` (both `Int!`); `page: {size: N}` alone
  raises *"Field 'Pagination.index' of required type 'Int!' was not provided"*.
  Omit `page` entirely to accept server defaults.
- Cache results locally; the dataset only changes on quarterly releases.

## Identifiers

- **Target** → Ensembl gene ID (`ENSG...`), argument `ensemblId`.
- **Disease** → EFO-ontology ID; in the current release most are **MONDO** terms
  (e.g. `MONDO_0004975` = Alzheimer disease). The argument is still `efoId`, but
  pass the ID that `search` returns — many legacy `EFO_...` codes no longer
  resolve and return `null`.
- **Drug** → ChEMBL ID (`CHEMBL...`), argument `chemblId`.

## Primary query roots

### `target(ensemblId: String!)`

Gene annotations, tractability, safety, and disease associations. Common fields:
`id`, `approvedSymbol`, `approvedName`, `biotype`, `functionDescriptions`,
`tractability`, `safetyLiabilities`, `geneticConstraint`, `baselineExpression`,
`chemicalProbes`, `pathways`, `drugAndClinicalCandidates`, `associatedDiseases`.
(There is no `target.knownDrugs` or `target.expressions` in the current schema —
use `drugAndClinicalCandidates` and `baselineExpression`.)

### `disease(efoId: String!)`

Disease/phenotype data, associated targets, and clinical drugs. Common fields:
`id`, `name`, `description`, `therapeuticAreas`, `synonyms`, `associatedTargets`,
`drugAndClinicalCandidates`, `evidences`. (No `disease.knownDrugs` — use
`drugAndClinicalCandidates`.)

### `drug(chemblId: String!)`

Compound details and pharmacology. Common fields: `id`, `name`, `synonyms`,
`tradeNames`, `drugType`, `maximumClinicalStage`, `mechanismsOfAction`,
`indications`, `drugWarnings`, `adverseEvents`. Note `synonyms` and `tradeNames`
are lists of `DrugLabelAndSource { label source }` and need a sub-selection;
`maximumClinicalStage` is a **string** (e.g. `"APPROVAL"`, `"PHASE_2"`), not a
number. There is no `maximumClinicalTrialPhase`, `hasBeenWithdrawn`, or
`withdrawnNotice` — withdrawal / black-box data lives in `drugWarnings`.

### `search(queryString: String!, entityNames: [String!], page: Pagination)`

Free-text search across targets, diseases, and drugs. Returns
`hits { id, entity, name, description }`. Filter `entityNames` to
`["target"]`, `["disease"]`, and/or `["drug"]`.

## Example queries

### 1. Resolve a name to an ID

```graphql
query search($queryString: String!, $entityNames: [String!]) {
  search(queryString: $queryString, entityNames: $entityNames, page: {index: 0, size: 10}) {
    hits { id entity name description }
  }
}
```

Variables: `{"queryString": "alzheimer disease", "entityNames": ["disease"]}`
→ `MONDO_0004975`. For targets you get `ENSG...`; for drugs, `CHEMBL...`.

### 2. Target profile with top disease associations

```graphql
query targetInfo($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    biotype
    tractability { label modality value }
    safetyLiabilities {
      event
      effects { direction dosing }
      biosamples { tissueLabel cellLabel }
    }
    geneticConstraint { constraintType score exp obs }
    associatedDiseases(page: {index: 0, size: 10}) {
      count
      rows {
        disease { id name }
        score
        datatypeScores { id score }
      }
    }
  }
}
```

`datatypeScores` items are `ScoredComponent { id score }` — use `id`, not
`componentId`.

### 3. Disease profile with top target associations

```graphql
query diseaseInfo($efoId: String!) {
  disease(efoId: $efoId) {
    id
    name
    description
    therapeuticAreas { id name }
    synonyms { relation terms }
    associatedTargets(page: {index: 0, size: 10}) {
      count
      rows {
        target { id approvedSymbol approvedName }
        score
        datatypeScores { id score }
      }
    }
  }
}
```

### 4. Evidence for a target-disease pair (optionally filtered by data source)

```graphql
query evidences($ensemblId: String!, $efoId: String!, $datasourceIds: [String!]) {
  disease(efoId: $efoId) {
    evidences(ensemblIds: [$ensemblId], datasourceIds: $datasourceIds, size: 100) {
      count
      rows {
        datasourceId
        datatypeId
        score
        targetFromSourceId
        studyId
        literature
        cohortPhenotypes
      }
    }
  }
}
```

Variables: `{"ensemblId": "ENSG00000157764", "efoId": "MONDO_0004975",
"datasourceIds": ["eva", "gwas_credible_sets"]}`. The `evidences` argument is
`datasourceIds` (data **source** IDs such as `eva`, `gwas_credible_sets`,
`gene_burden`, `chembl`, `europepmc`, `impc`, `expression_atlas`) — there is **no
`datatypes` argument**. To narrow by *data type* (`genetic_association`,
`known_drug`, ...), either pass all the source IDs belonging to that type or omit
the filter and group on the returned `datatypeId` client-side. Omit
`datasourceIds` (pass `null`) for all evidence.

### 5. Clinical drugs & candidates for a disease

```graphql
query diseaseDrugs($efoId: String!) {
  disease(efoId: $efoId) {
    drugAndClinicalCandidates {
      count
      rows {
        maxClinicalStage
        drug { id name drugType }
        clinicalReports { trialPhase trialOverallStatus }
      }
    }
  }
}
```

Replaces the removed `disease.knownDrugs`. `maxClinicalStage` /
`clinicalReports.trialPhase` map to clinical stage: `PHASE4`/`APPROVAL` =
approved, `PHASE3` = late-stage, `PHASE2` = mid-stage, `PHASE1` = early safety.
The mirror field `target(ensemblId).drugAndClinicalCandidates` adds a `diseases`
list per row.

### 6. Drug profile

```graphql
query drugInfo($chemblId: String!) {
  drug(chemblId: $chemblId) {
    id
    name
    synonyms { label source }
    tradeNames { label source }
    drugType
    maximumClinicalStage
    drugWarnings {
      warningType
      description
      toxicityClass
      country
      year
    }
    mechanismsOfAction {
      uniqueActionTypes
      rows {
        actionType
        mechanismOfAction
        targetName
        targets { id approvedSymbol }
      }
    }
    indications {
      count
      rows {
        disease { id name }
        maxClinicalStage
      }
    }
  }
}
```

`mechanismsOfAction` and `indications` both wrap their records in `rows`.
Withdrawal and black-box signals come from `drugWarnings` (a
`warningType` of `"Withdrawn"` or `"Black Box Warning"`).

### 7. All associations for a target (filter by score client-side)

```graphql
query targetAssociations($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    associatedDiseases(page: {index: 0, size: 100}) {
      count
      rows {
        disease { id name }
        score
        datatypeScores { id score }
      }
    }
  }
}
```

Then keep rows where `score >= min_score` in your own code.

## Error handling

```python
data = run(query, variables)          # raises on the "errors" key
target = data.get("target")           # None if the ID did not resolve
if target is None:
    ...                               # handle unknown/mistyped ID
```

A `null` root entity (e.g. `data["target"] is None`) usually means the
identifier did not resolve — re-check it with `search`. Legacy `EFO_...` disease
IDs frequently return `null` after being remapped to MONDO, so always resolve
disease IDs fresh. A populated `errors` array indicates a malformed query or
unknown/renamed field; use the GraphQL browser to confirm field names against
the active release schema.

## Licensing and citation

All Open Targets Platform data is freely available. Cite:

Ochoa, D. et al. (2025) *Open Targets Platform: facilitating therapeutic
hypotheses building in drug discovery.* Nucleic Acids Research, 53(D1):D1467–D1477.
