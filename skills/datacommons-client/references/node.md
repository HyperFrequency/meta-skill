# Node Endpoint — Knowledge Graph Structure

The Node API reads the **shape** of the graph: the directed properties (edges)
connecting nodes, their values, entity names, and place hierarchies. Use it to
discover what an entity has, to look up human-readable names, and to walk
containment relationships.

## `fetch(node_dcids, expression, all_pages=True, next_token=None)`

Retrieve properties with **arrow-notation** relation expressions.

| Arrow | Meaning |
| --- | --- |
| `->` | Outgoing property (node → value) |
| `<-` | Incoming property (value → node) |
| `<-*` | Multi-hop incoming traversal |

```python
client.node.fetch(node_dcids=["geoId/06"], expression="->name")            # outgoing
client.node.fetch(node_dcids=["geoId/06"], expression="<-containedInPlace") # incoming
```

## Property discovery

### `fetch_property_labels(node_dcids, out=True)`

List property *labels* without values — the fastest way to see what exists.
`out=True` for outgoing edges, `out=False` for incoming.

```python
client.node.fetch_property_labels(node_dcids=["geoId/06"], out=True)   # name, latitude, ...
```

### `fetch_property_values(node_dcids, property, out=True, limit=None)`

Fetch the values of a specific property.

```python
client.node.fetch_property_values(node_dcids=["geoId/06"], property="name", out=True)
```

## Names and classes

### `fetch_entity_names(node_dcids, language="en")`

DCID → display name, in the requested language. Returns a plain dict.

```python
client.node.fetch_entity_names(node_dcids=["geoId/06", "country/USA"])
# {"geoId/06": "California", "country/USA": "United States"}
```

### `fetch_all_classes()`

List every entity type (Class node) in the graph.

## Place hierarchy

These return dictionaries (not `NodeResponse` objects):

| Method | Returns |
| --- | --- |
| `fetch_place_children(node_dcids)` | Direct child places |
| `fetch_place_descendants(node_dcids)` | Full recursive child hierarchy |
| `fetch_place_parents(node_dcids)` | Direct parent places |
| `fetch_place_ancestors(node_dcids)` | Full recursive parent lineage |

```python
children = client.node.fetch_place_children(node_dcids=["country/USA"])   # all states
counties = [c for c in client.node.fetch_place_children(node_dcids=["geoId/06"])["geoId/06"]
            if "County" in c]
```

### `fetch_statvar_constraints(node_dcids)`

Constraint properties of a statistical variable — how it is scoped/defined.

```python
client.node.fetch_statvar_constraints(node_dcids=["Count_Person"])
```

## Response format and pagination

- `fetch`, `fetch_property_labels`, `fetch_property_values`, `fetch_statvar_constraints`
  return `NodeResponse` objects with `.to_dict()`, `.to_json()`, and a
  `nextToken`.
- `fetch_entity_names` and the place-hierarchy methods return plain dicts.

Large responses are paginated. Set `all_pages=False` to receive one chunk plus a
`nextToken`, then re-query with `next_token` to continue:

```python
page = client.node.fetch(node_dcids=["country/USA"], expression="<-containedInPlace", all_pages=False)
while page.nextToken:
    page = client.node.fetch(node_dcids=["country/USA"], expression="<-containedInPlace",
                             next_token=page.nextToken)
```

## Notes

- Start with `fetch_property_labels()` to learn what is queryable before pulling
  values.
- The Node API handles simple expressions; for complex multi-arc traversals,
  break the query into steps or combine with the Observation API.
