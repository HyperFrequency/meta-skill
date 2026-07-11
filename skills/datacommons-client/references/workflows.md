# Workflows — End-to-End Recipes

Runnable patterns that chain Resolve, Node, and Observation. Each assumes:

```python
import pandas as pd
from datacommons_client import DataCommonsClient
client = DataCommonsClient()   # DC_API_KEY in the environment
```

## The four query shapes

| Shape | Chain |
| --- | --- |
| Name → data | resolve names → `observation.fetch` |
| Coordinates → data | `resolve.fetch_dcid_by_coordinates` → `observation.fetch` |
| Parent → children → data | `node.fetch_place_children` (or `entity_expression`) → `observation.fetch` |
| Explore → select → query | `fetch_available_statistical_variables` → filter → `observation.fetch` |

## 1. Name → population

```python
resolved = client.resolve.fetch_dcids_by_name(names=["California", "Texas", "New York"], entity_type="State")
dcids, name_of = [], {}
for name, result in resolved.to_dict().items():
    if result["candidates"]:
        dcid = result["candidates"][0]["dcid"]
        dcids.append(dcid); name_of[dcid] = name

resp = client.observation.fetch(variable_dcids=["Count_Person"], entity_dcids=dcids, date="latest")
df = pd.DataFrame(resp.to_observation_records())
df["place"] = df["entity"].map(name_of)
```

## 2. Time series

```python
resp = client.observation.fetch(
    variable_dcids=["UnemploymentRate_Person"], entity_dcids=["country/USA"], date="all",
)
series = pd.DataFrame(resp.to_observation_records()).sort_values("date")
# series[["date", "value"]] is ready to plot
```

## 3. Every county in a state

```python
resp = client.observation.fetch(
    variable_dcids=["Median_Income_Household"],
    entity_expression="geoId/06<-containedInPlace+{typeOf:County}",
    date="2020",
)
df = pd.DataFrame(resp.to_observation_records())
names = client.node.fetch_entity_names(node_dcids=df["entity"].unique().tolist())
df["name"] = df["entity"].map(names)
top10 = df.nlargest(10, "value")[["name", "value"]]
```

## 4. Multi-variable comparison

```python
places = ["California", "Texas", "Florida", "New York"]
resolved = client.resolve.fetch_dcids_by_name(names=places)
name_of = {r["candidates"][0]["dcid"]: n
           for n, r in resolved.to_dict().items() if r["candidates"]}

resp = client.observation.fetch(
    variable_dcids=["Count_Person", "Median_Income_Household",
                    "UnemploymentRate_Person", "Median_Age_Person"],
    entity_dcids=list(name_of), date="latest",
)
df = pd.DataFrame(resp.to_observation_records())
df["state"] = df["entity"].map(name_of)
comparison = df.pivot_table(values="value", index="state", columns="variable")
```

## 5. Coordinates → nearest place → data

```python
dcid = client.resolve.fetch_dcid_by_coordinates(latitude=37.7749, longitude=-122.4194)
name = client.node.fetch_entity_names(node_dcids=[dcid])[dcid]

available = client.observation.fetch_available_statistical_variables(entity_dcids=[dcid])
resp = client.observation.fetch(
    variable_dcids=["Count_Person", "Median_Income_Household"], entity_dcids=[dcid], date="latest",
)
```

## 6. Single-source consistency (facet filtering)

```python
census = client.observation.fetch(
    variable_dcids=["Count_Person"], entity_dcids=["country/USA"], date="all",
    filter_facet_domains=["census.gov"],
)
```

## 7. Batch cities → CSV

```python
cities = ["San Francisco, CA", "Los Angeles, CA", "San Diego, CA", "Sacramento, CA", "San Jose, CA"]
resolved = client.resolve.fetch_dcids_by_name(names=cities, entity_type="City")
name_of = {r["candidates"][0]["dcid"]: n
           for n, r in resolved.to_dict().items() if r["candidates"]}

resp = client.observation.fetch(
    variable_dcids=["Count_Person", "Median_Income_Household", "UnemploymentRate_Person"],
    entity_dcids=list(name_of), date="latest",
)
df = pd.DataFrame(resp.to_observation_records())
df["city"] = df["entity"].map(name_of)
df.pivot_table(values="value", index="city", columns="variable", aggfunc="first").to_csv("cities.csv")
```

## 8. Explore the graph around an entity

```python
entity = "geoId/06"  # California
out_props = client.node.fetch_property_labels(node_dcids=[entity], out=True)[entity]
in_props  = client.node.fetch_property_labels(node_dcids=[entity], out=False)[entity]
children  = client.node.fetch_place_children(node_dcids=[entity])[entity]
sample    = client.node.fetch_entity_names(node_dcids=children[:5])
```

## Robustness checklist

- **Guard `candidates`** before indexing — a name may not resolve.
- **Flag ambiguity** — inspect `dominantType` when several candidates return
  (see `references/resolve.md`).
- **Confirm availability** — an empty result means the variable/entity/date
  combination has no data, not that the call failed. Check with
  `fetch_available_statistical_variables()` or `select=["entity", "variable"]`.
- **Cache** name → DCID mappings across repeated queries.
- **Paginate** large Node responses (`all_pages` / `next_token`).
