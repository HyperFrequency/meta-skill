# RCSB Data API — reference

The Data API answers "given these identifiers, what is the metadata?" It is a
GraphQL-backed service; the `rcsbapi.data.DataQuery` client builds and runs the
GraphQL for you, or you can hit REST/GraphQL endpoints directly.

## DataQuery (recommended)

```python
from rcsbapi.data import DataQuery as Query

q = Query(
    input_type="entries",                # object type to query (plural)
    input_ids=["4HHB", "1MBN", "1GZX"],  # one or many ids
    return_data_list=[                   # exact GraphQL dot-paths to return
        "struct.title",
        "exptl.method",
        "rcsb_entry_info.resolution_combined",
        "rcsb_entity_source_organism.scientific_name",
        "rcsb_accession_info.initial_release_date",
    ],
)
data = q.exec()          # equivalent: q.get_response()
```

`exec()` returns a nested dict shaped like the GraphQL response, e.g.
`data["data"]["entries"][i]["struct"]["title"]`. Only the fields you named in
`return_data_list` are populated — request exactly what you need to keep responses
small.

### `input_type` values

Plural object type matched to the id form you pass:

| `input_type` | Id form | Contents |
| --- | --- | --- |
| `entries` | `4HHB` | Whole PDB entry / CSM |
| `polymer_entities` | `4HHB_1` | Protein / DNA / RNA entity |
| `nonpolymer_entities` | `4HHB_3` | Ligand / cofactor / ion |
| `branched_entities` | `4HHB_2` | Oligosaccharide |
| `assemblies` | `4HHB-1` | Biological assembly |
| `polymer_entity_instances` | `4HHB.A` | One chain (instance) |
| `chem_comps` | `HEM` | Chemical-component dictionary entry |

## Core object hierarchy

Data is organized top-down; pick the input type at the level whose fields you need:

- **entry** → experiment, resolution, dates, atom counts, title.
- **polymer_entity** → sequence, molecular weight, source organism, cross-refs.
- **nonpolymer_entity / branched_entity** → ligands, sugars.
- **assembly** → oligomeric/biological form composition and symmetry.
- **polymer_entity_instance** → per-chain (instance) annotations.
- **chem_comp** → standalone chemical component definitions.

## Common field paths

**Entry level**

| Path | Meaning |
| --- | --- |
| `struct.title` | Title / description |
| `exptl.method` | Experimental method |
| `rcsb_entry_info.resolution_combined` | Resolution (Å) |
| `rcsb_entry_info.deposited_atom_count` | Atom count |
| `rcsb_entry_info.polymer_entity_count` | Number of polymer entities |
| `rcsb_accession_info.deposit_date` | Deposition date |
| `rcsb_accession_info.initial_release_date` | Release date |

**Polymer-entity level**

| Path | Meaning |
| --- | --- |
| `entity_poly.pdbx_seq_one_letter_code` | One-letter sequence |
| `entity_poly.pdbx_strand_id` | Chain ids for the entity |
| `rcsb_polymer_entity.formula_weight` | Molecular weight (kDa) |
| `rcsb_entity_source_organism.scientific_name` | Source organism |
| `rcsb_entity_source_organism.ncbi_taxonomy_id` | NCBI taxonomy id |

## Raw REST endpoints

Base: `https://data.rcsb.org/rest/v1/` — one object per call, full record returned.

```bash
curl https://data.rcsb.org/rest/v1/core/entry/4HHB
curl https://data.rcsb.org/rest/v1/core/polymer_entity/4HHB_1
curl https://data.rcsb.org/rest/v1/core/assembly/4HHB/1
```

Interactive schema / Redoc: https://data.rcsb.org/redoc/index.html

## Raw GraphQL endpoint

`POST https://data.rcsb.org/graphql` — grab fields from any level of the hierarchy
in a single request; the most efficient path for complex, multi-level pulls.

```python
import requests

query = """
{
  entry(entry_id: "4HHB") {
    struct { title }
    exptl { method }
    rcsb_entry_info { resolution_combined deposited_atom_count }
    rcsb_accession_info { deposit_date initial_release_date }
  }
}
"""
resp = requests.post("https://data.rcsb.org/graphql", json={"query": query})
data = resp.json()
```

Browse the live schema at https://data.rcsb.org/graphql (GraphiQL).

## Batch metadata retrieval

`DataQuery` accepts many ids at once — one request instead of a loop. For very
large sets, chunk `input_ids` (e.g. 100–500 per call) and add a short delay
between calls; see [files-and-ops.md](files-and-ops.md) for rate-limit handling.
Typical pipeline: run a Search query (see [search-api.md](search-api.md)) to get
ids, then pass them straight into `DataQuery`.
