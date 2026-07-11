---
name: datacommons-client
version: 0.1.0
description: >-
  Query public statistical data from Data Commons — a knowledge graph that
  aggregates census, health, economic, and environmental data from
  authoritative sources (US Census, BLS, FRED, CDC, WHO, World Bank, EPA, and
  more) — through the datacommons-client Python API v2. Use to fetch
  population, GDP, unemployment, income, disease-prevalence, or emissions time
  series for geographic entities; resolve place names, coordinates, or Wikidata
  IDs to Data Commons IDs (DCIDs); walk geographic hierarchies (every county in
  a state); and discover which statistical variables cover an entity — all
  Pandas-ready and keyed on standardized DCIDs that stay consistent across
  sources. Use when you want programmatic, cross-source statistical data for
  places. Do NOT use for a one-off single lookup spread across many unrelated
  database APIs (use `database-lookup`), general web search (use
  `research-lookup`), the user's own private/SQL data, or non-place entities —
  the Resolve endpoint currently covers places only.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (datacommons-client)"
---

# Data Commons Client

## Overview

Data Commons is a public knowledge graph that harmonizes statistical data from
census bureaus, labor and health agencies, environmental bodies, and
international organizations into one queryable schema. Every place, variable,
and observation carries a stable **DCID** (Data Commons ID), so a query for
"population of California" resolves the same way whether the number originated
at the US Census Bureau or the World Bank.

The `datacommons-client` Python package (API v2) exposes the graph through three
endpoints, all reachable from a single client:

- **`client.observation`** — statistical time series (the numbers).
- **`client.node`** — graph structure: properties, entity names, place
  hierarchies (the shape).
- **`client.resolve`** — turn names / coordinates / external IDs into DCIDs (the
  keys).

Because everything is keyed on DCIDs, real work almost always runs
**resolve → (discover) → observe**. This file is a router; deep per-endpoint
detail lives in `references/`.

## When to Use This Skill

- You need demographic, economic, health, or environmental statistics for one
  or more **geographic** entities (country, state, county, city, census tract).
- You want a **time series** for trend analysis, or the latest value across many
  places at once.
- You want data for an entire **hierarchy** — "median income for every county in
  California" — in a single call.
- You start from **place names, GPS coordinates, or Wikidata IDs** and need the
  DCIDs to query with.
- You want results as a **Pandas DataFrame**, and you value cross-source
  consistency over hitting each agency's bespoke API.

## When NOT to Use This Skill

- **One-off lookups across many unrelated databases** (PubChem, ChEMBL, a single
  FRED series, a patent) — use `database-lookup`, which is lighter and already
  wraps ~78 REST APIs (including a Data Commons entry).
- **General web questions or literature** — use `research-lookup` /
  `paper-lookup`.
- **The user's own data** — private datasets, SQL databases, uploaded CSVs. Use
  `data-analysis` / `polars` / `statistical-analysis`.
- **Non-place entities.** The Resolve endpoint supports places only. To key
  queries on a disease, drug, or other node you must obtain its DCID another way
  (Node-API exploration, the DC Browser).
- **Downstream modeling or plotting** — this skill fetches and shapes data; hand
  the DataFrame to `statistical-analysis`, `data-analysis`, or a plotting skill.

## Install and Authenticate

```bash
uv pip install "datacommons-client[pandas]"   # drop [pandas] for a lean install
```

The public `datacommons.org` instance requires an API key:

```bash
export DC_API_KEY="your_key"     # request one at https://apikeys.datacommons.org/
```

```python
from datacommons_client import DataCommonsClient

client = DataCommonsClient()                       # reads DC_API_KEY
client = DataCommonsClient(api_key="your_key")     # or pass explicitly
client = DataCommonsClient(url="https://custom.datacommons.org")  # custom instance; no key needed
```

## The Core Workflow: Resolve → Discover → Observe

```python
# 1. Resolve names to DCIDs (skip if you already have them)
resolved = client.resolve.fetch_dcids_by_name(names=["California", "Texas"])
dcids = [c[0]["dcid"]
         for r in resolved.to_dict().values()
         if (c := r["candidates"])]        # always guard: candidates may be empty

# 2. (Optional) Discover which variables actually have data for these entities
available = client.observation.fetch_available_statistical_variables(entity_dcids=dcids)

# 3. Fetch the observations
response = client.observation.fetch(
    variable_dcids=["Count_Person", "UnemploymentRate_Person"],
    entity_dcids=dcids,
    date="latest",                          # "latest" | "all" | ISO date like "2020"
)

# 4. Shape the result
import pandas as pd
df = pd.DataFrame(response.to_observation_records())   # date, entity, variable, value
```

Query a whole hierarchy in one call with a **relation expression** instead of an
explicit DCID list:

```python
response = client.observation.fetch(
    variable_dcids=["Median_Income_Household"],
    entity_expression="geoId/06<-containedInPlace+{typeOf:County}",  # all CA counties
    date="2020",
)
```

Full parameter tables, response-object methods, and every endpoint variant are
documented per endpoint:

- **`references/resolve.md`** — names, coordinates, Wikidata IDs → DCIDs;
  ambiguity handling; place-only limitation.
- **`references/observation.md`** — `fetch()`, `fetch_observations_by_entity_type()`,
  availability checks, facet (source) filtering, response reshaping.
- **`references/node.md`** — property discovery, entity names, place
  hierarchies, arrow-notation traversal, pagination.
- **`references/workflows.md`** — end-to-end recipes (time-series plotting,
  multi-variable comparison, coordinate lookup, batch cities, CSV export).

## Finding Statistical Variables

Variables use structured DCIDs like `Count_Person`, `Count_Person_Female`,
`UnemploymentRate_Person`, `Median_Income_Household`, `Median_Age_Person`,
`Count_Death`. Two ways to find the right one:

- Programmatically: `client.observation.fetch_available_statistical_variables(entity_dcids=[dcid])`
  returns exactly what is queryable for that entity — filter before you fetch.
- Interactively: the Statistical Variable Explorer at
  <https://datacommons.org/tools/statvar>.

Do not guess variable DCIDs. A wrong or non-existent variable returns no
observations rather than an error, which reads as "no data" — confirm
availability first.

## Working with Pandas

`response.to_observation_records()` flattens the nested response into one row
per observation (fields: `date`, `entity`, `variable`, `value`, plus source
metadata). Wrap it in `pd.DataFrame(...)` — this is robust whether the method
returns records or an already-tabular structure — then pivot for analysis:

```python
df = pd.DataFrame(response.to_observation_records())
pivot = df.pivot_table(values="value", index="date", columns="entity")
```

## Common Failure Modes

- **Empty `candidates`** — the name did not resolve. Add context
  ("Springfield, IL"), pass `entity_type=`, or handle the miss. See
  `references/resolve.md`.
- **Ambiguous names** — many places share a name; Resolve returns *all*
  candidates. Disambiguate on `dominantType` or a more specific query; do not
  blindly take `candidates[0]`.
- **Silent "no data"** — an invalid variable/entity/date combination returns an
  empty result, not an exception. Verify with
  `fetch_available_statistical_variables()` or `select=["entity", "variable"]`.
- **Mixed sources** — a variable may carry observations from several providers
  (facets). For a consistent series, filter with `filter_facet_domains=[...]`
  (see `references/observation.md`).
- **Large graph responses** — Node queries paginate. Use `all_pages` /
  `next_token` rather than assuming one page (see `references/node.md`).

## External Resources

- Python API v2 docs: <https://docs.datacommons.org/api/python/v2/>
- Statistical Variable Explorer: <https://datacommons.org/tools/statvar>
- Knowledge Graph Browser: <https://datacommons.org/browser/>
- Source repository: <https://github.com/datacommonsorg/api-python>
