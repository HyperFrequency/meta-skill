# Resolve Endpoint — Names / Coordinates / IDs → DCIDs

Almost every Data Commons query needs DCIDs. The Resolve endpoint turns
human-friendly identifiers into them. It is the first step in most workflows.

**Scope limit:** Resolve currently supports **place entities only** (countries,
states, counties, cities, etc.). For non-place nodes, obtain the DCID via the
Node API or the DC Browser.

## Methods

### `fetch_dcids_by_name(names, entity_type=None)`

The workhorse. Resolves a list of place names, optionally constrained by type.

- `names` — list of place-name strings (e.g. `["San Francisco, CA", "Los Angeles"]`).
- `entity_type` — optional filter such as `"City"`, `"State"`, `"County"`,
  `"Country"`.
- Returns a `ResolveResponse` with a candidate list per name.

```python
response = client.resolve.fetch_dcids_by_name(
    names=["San Francisco", "Los Angeles"],
    entity_type="City",
)
for name, result in response.to_dict().items():
    print(name, result["candidates"])
```

### `fetch_dcid_by_coordinates(latitude, longitude)`

Finds the place at a point. Returns a single DCID string (not a `ResolveResponse`).

```python
dcid = client.resolve.fetch_dcid_by_coordinates(latitude=37.7749, longitude=-122.4194)
```

### `fetch_dcids_by_wikidata_id(wikidata_ids)`

Maps external Wikidata identifiers to DCIDs — useful when integrating a dataset
that already keys on Wikidata.

```python
response = client.resolve.fetch_dcids_by_wikidata_id(wikidata_ids=["Q30", "Q99"])  # USA, California
```

### `fetch(nodes, property)`

The general form. Resolves via a relation/property expression — the most
flexible entry point when the convenience methods above do not fit.

```python
response = client.resolve.fetch(nodes=["California", "Texas"], property="name")
```

## Response Structure

`ResolveResponse` (returned by every method except `fetch_dcid_by_coordinates`)
holds, per queried term:

- `node` — the search term you passed.
- `candidates` — a list of matches; each is a dict with a `dcid` and often a
  `dominantType` for disambiguation.

Helper methods:

- `to_dict()` — full nested dictionary.
- `to_json()` — JSON string.
- `to_flat_dict()` — simplified `{term: dcid}` when you just want the IDs.

An ambiguous name yields multiple candidates, e.g. several `Springfield`
cities, each with its own `dcid` and `dominantType`.

## Handling Ambiguity and Misses

```python
result = client.resolve.fetch_dcids_by_name(names=["Springfield"]).to_dict()["Springfield"]

if not result["candidates"]:
    ...  # no match: add context ("Springfield, Illinois") or an entity_type

cities = [c for c in result["candidates"] if c.get("dominantType") == "City"]
```

## Best Practices

- **Never hand-craft DCID strings.** Resolve them; internal formats change.
- **Guard `candidates`.** Always check the list is non-empty before indexing.
- **Do not blindly take `candidates[0]`** for common names — disambiguate on
  `dominantType` or narrow the query.
- **Cache** name → DCID mappings when querying the same places repeatedly.
- **Pick the right method:** names → `fetch_dcids_by_name`; a point →
  `fetch_dcid_by_coordinates`; external IDs → `fetch_dcids_by_wikidata_id`.

## Limitations

- **Places only** — no diseases, drugs, or other node types.
- **No relationship resolution** — for `containedInPlace`-style links, use the
  Node API (`references/node.md`).
- **Ambiguity is yours to resolve** — the API returns every match; your code
  decides which is correct.
