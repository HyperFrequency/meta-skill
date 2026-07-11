# RCSB Search API — reference

The Search API answers "which structures match these criteria?" and returns
identifiers. Use the `rcsbapi.search` module of the `rcsb-api` client, or POST
JSON to `https://search.rcsb.org/rcsbsearch/v2/query`.

## Execution model

Build a **query** from one or more **terminal** query objects (optionally combined
with boolean operators), then execute it:

```python
results = list(query())                 # iterate identifiers (return_type="entry" default)
results = query(return_type="assembly") # different granularity
count   = query(return_counts=True)     # just the number of hits
```

`query()` and `query.exec()` are equivalent ways to run it. Iterating streams all
pages transparently; wrap in `list(...)` to materialize.

## Query types (terminals)

| Class | Purpose |
| --- | --- |
| `TextQuery` | Full-text search over names, keywords, descriptions |
| `AttributeQuery` | Match a specific structured field (organism, resolution, ...) |
| `SequenceQuery` | Sequence-similarity search (MMseqs2) |
| `SequenceMotifQuery` | Short sequence-motif / PROSITE-style pattern |
| `StructSimilarityQuery` | 3D shape similarity (BioZernike) |
| `StructMotifQuery` | Geometric arrangement of residues (e.g. catalytic triad) |
| `ChemSimilarityQuery` | Small-molecule / ligand chemical similarity |

```python
from rcsbapi.search import (
    TextQuery, AttributeQuery, SequenceQuery,
    StructSimilarityQuery,
)
from rcsbapi.search import search_attributes as attrs
```

## AttributeQuery

Two equivalent forms:

```python
# Explicit
q = AttributeQuery(
    attribute="rcsb_entity_source_organism.scientific_name",
    operator="exact_match",
    value="Homo sapiens",
)

# Operator overload (attrs.<dot.path> <op> value)
q = attrs.rcsb_entity_source_organism.scientific_name == "Homo sapiens"
```

### Operators

| Operator | Meaning |
| --- | --- |
| `exact_match` | Exact string match |
| `contains_words` | Contains all of the given words (any order) |
| `contains_phrase` | Contains the exact phrase |
| `equals` | Numeric equality |
| `greater` / `greater_or_equal` | Numeric `>` / `>=` |
| `less` / `less_or_equal` | Numeric `<` / `<=` |
| `range` | Closed numeric or date interval, `value=(lo, hi)` |
| `exists` | Field is present |
| `in` | Value is in a provided list |

Overloaded comparisons map to these: `==` → `exact_match`/`equals`, `<` → `less`,
`>=` → `greater_or_equal`, etc.

### Frequently used attribute paths

| Path | Meaning |
| --- | --- |
| `rcsb_entry_info.resolution_combined` | Resolution (Å) |
| `exptl.method` | `X-RAY DIFFRACTION`, `SOLUTION NMR`, `ELECTRON MICROSCOPY`, ... |
| `rcsb_entity_source_organism.scientific_name` | Source organism |
| `rcsb_entity_source_organism.ncbi_taxonomy_id` | NCBI taxonomy id |
| `rcsb_polymer_entity.formula_weight` | Entity molecular weight (kDa) |
| `rcsb_accession_info.initial_release_date` | Release date (ISO) |
| `refine.ls_R_factor_R_free` | Crystallographic R-free |
| `rcsb_nonpolymer_entity_instance_container_identifiers.comp_id` | Bound ligand code (e.g. `ATP`) |
| `rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession` | Cross-ref accession (e.g. UniProt) |
| `drugbank_info.drug_groups` | `approved`, `investigational`, `experimental`, ... |

Discover any attribute name in the interactive schema at
https://search.rcsb.org/#attributes or via `attrs.<tab>` autocompletion.

## Sequence similarity

```python
q = SequenceQuery(
    value="MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRK...",
    evalue_cutoff=0.1,
    identity_cutoff=0.9,        # 0.0-1.0 fractional identity
    sequence_type="protein",   # "protein" | "dna" | "rna"
)
results = list(q())
```

## Structure similarity

```python
# By whole entry (structure_search_type defaults to "entry_id")
q = StructSimilarityQuery(entry_id="4HHB")

# By a specific chain (instance) or assembly — select the granularity with
# structure_input_type ("chain_id" | "assembly_id"), not structure_search_type
q = StructSimilarityQuery(entry_id="4HHB", structure_input_type="chain_id", chain_id="A")
q = StructSimilarityQuery(entry_id="4HHB", structure_input_type="assembly_id", assembly_id="1")
```

`structure_search_type` selects the *source* of the query shape (`"entry_id"` for an
existing structure, default; `"file_upload"`/`"file_url"` for your own coordinates),
while `structure_input_type` selects entry vs chain vs assembly granularity.

## Combining queries

Standard Python bitwise operators build boolean logic; group with parentheses:

```python
q1 = TextQuery("kinase")
q2 = attrs.rcsb_entity_source_organism.scientific_name == "Homo sapiens"
q3 = attrs.rcsb_entry_info.resolution_combined < 2.5

high_res_human_kinases = q1 & q2 & q3      # AND
either_organism        = (q2 | (attrs.rcsb_entity_source_organism.scientific_name == "Mus musculus"))
not_low_res            = q1 & ~(attrs.rcsb_entry_info.resolution_combined > 3.0)  # NOT
```

`&` = AND, `|` = OR, `~` = NOT.

## Return types

Pass `return_type=` to change identifier granularity:

| `return_type` | Identifier form |
| --- | --- |
| `entry` (default) | `4HHB` |
| `assembly` | `4HHB-1` |
| `polymer_entity` | `4HHB_1` |
| `polymer_instance` | `4HHB.A` |
| `non_polymer_entity` | ligand entity ids |
| `mol_definition` | chemical component ids |

Feed the returned ids straight into `DataQuery` (see
[data-api.md](data-api.md)) to fetch metadata.

## Notes

- Results are ranked by relevance/score; scores are available via the client's
  scored-result options when needed.
- An empty result usually means an over-restrictive query or a mistyped attribute
  path — verify the path against the schema and loosen operators.
