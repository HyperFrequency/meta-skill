# Observation Endpoint — Statistical Time Series

The Observation API returns **observations**: data points that bind an entity, a
statistical variable, and a date — for example "USA population in 2020" or
"unemployment rate for every county in California, all years."

## `fetch()` — the primary method

Retrieves observations with flexible entity specification.

| Parameter | Required | Notes |
| --- | --- | --- |
| `variable_dcids` | yes | List of statistical-variable DCIDs. |
| `entity_dcids` *or* `entity_expression` | yes | Explicit DCIDs, or a relation expression that expands to many entities. |
| `date` | no | `"latest"` (default), `"all"` (full series), or an ISO date: `"2020"`, `"2020-01"`, `"2020-01-15"`. |
| `select` | no | Fields to return. Default `["date", "entity", "variable", "value"]`. Use `["entity", "variable"]` to check availability without pulling values. |
| `filter_facet_domains` | no | Restrict to source domains, e.g. `["census.gov"]`. |
| `filter_facet_ids` | no | Restrict to specific facet (source) IDs. |

```python
# Latest value for several entities
client.observation.fetch(
    variable_dcids=["Count_Person"],
    entity_dcids=["geoId/06", "geoId/48"],   # California, Texas
    date="latest",
)

# Complete time series
client.observation.fetch(
    variable_dcids=["Count_Person"],
    entity_dcids=["country/USA"],
    date="all",
)

# Whole hierarchy via a relation expression
client.observation.fetch(
    variable_dcids=["Count_Person"],
    entity_expression="geoId/06<-containedInPlace+{typeOf:County}",  # all CA counties
    date="2020",
)
```

**Relation expression syntax** (`entity_expression`): `<-containedInPlace+`
walks *down* the containment hierarchy; `{typeOf:County}` filters expanded
entities by type. Reach for this instead of enumerating child DCIDs yourself.

## Other methods

### `fetch_available_statistical_variables(entity_dcids)`

Returns, per entity, the variables that actually have data. Call this before
`fetch()` to avoid querying variables that return nothing.

```python
available = client.observation.fetch_available_statistical_variables(entity_dcids=["geoId/06"])
```

### `fetch_observations_by_entity_type(parent_entity, entity_type, variable_dcids, date, ...)`

Convenience wrapper for "all children of a given type under a parent" — the
method-argument form of the `entity_expression` hierarchy query.

```python
client.observation.fetch_observations_by_entity_type(
    parent_entity="geoId/06",
    entity_type="County",
    variable_dcids=["Count_Person"],
    date="2020",
)
```

### `fetch_observations_by_entity_dcid(...)`

Explicit entity-by-DCID variant; functionally equivalent to `fetch()` with
`entity_dcids`.

## Response object

Observation responses expose:

- `to_dict()` — nested dict, organized variable → entity → observations.
- `to_json()` — JSON string.
- `to_observation_records()` — flatten to one record per observation
  (`date`, `entity`, `variable`, `value`, plus facet metadata). Wrap in
  `pd.DataFrame(...)` for analysis.
- `get_data_by_entity()` — re-key the response by entity instead of variable.

### Facets (data sources)

Each observation belongs to a **facet** describing its provenance —
`provenanceUrl`, measurement method, observation period, import name. When a
variable carries data from several providers, `orderedFacets` ranks them by
reliability/recency. For a single-source, apples-to-apples series, constrain
with `filter_facet_domains`.

## Common patterns

**Check availability without pulling values:**

```python
client.observation.fetch(
    variable_dcids=["Count_Person"], entity_dcids=["geoId/06"],
    select=["entity", "variable"],
)
```

**Single-source consistency:**

```python
client.observation.fetch(
    variable_dcids=["Count_Person"], entity_dcids=["country/USA"], date="all",
    filter_facet_domains=["census.gov"],
)
```

**To DataFrame and pivot:**

```python
import pandas as pd
df = pd.DataFrame(response.to_observation_records())
pivot = df.pivot_table(values="value", index="date", columns="entity")
```

## Notes

- An invalid variable/entity/date combination returns an **empty** result, not
  an error — verify availability first, and treat "no rows" as "check the query."
- `fetch()` is the most flexible call; prefer it unless a convenience method maps
  exactly to your need.
