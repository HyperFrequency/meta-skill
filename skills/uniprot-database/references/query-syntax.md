# UniProt Query Syntax

The `query=` parameter accepts a Lucene-style grammar of `field:value` terms
combined with boolean operators. This reference lists the fields you will use
most, the operators, and vetted patterns. Test any query live at
`https://rest.uniprot.org/uniprotkb/search?query=YOUR_QUERY&format=json&size=1`.

## Boolean operators and grouping

```
insulin AND diabetes                     # both terms
diabetes OR insulin                      # either term
kinase NOT organism_name:mouse           # exclude
(gene:BRCA1 OR gene:BRCA2) AND organism_id:9606   # grouped
```

Operators are case-sensitive uppercase (`AND`, `OR`, `NOT`). Quote multi-word
values: `organism_name:"Homo sapiens"`. Bare terms without a field search across
default text fields.

## Common search fields

### Identity
| Field | Meaning |
| --- | --- |
| `accession:P12345` | UniProt accession |
| `id:INSR_HUMAN` | Entry name |
| `gene:BRCA1` | Gene name (fuzzy) |
| `gene_exact:BRCA1` | Exact gene-name match |
| `protein_name:"insulin receptor"` | Protein name |

### Organism / taxonomy
| Field | Meaning |
| --- | --- |
| `organism_id:9606` | NCBI taxon id (9606 = human) |
| `organism_name:"Homo sapiens"` | Scientific name |
| `taxonomy_id:9606` | Alias for `organism_id` |
| `lineage:Primates` | Anywhere in the lineage |
| `virus_host_id:9606` | Viral proteins by host |

### Review status and sequence
| Field | Meaning |
| --- | --- |
| `reviewed:true` / `reviewed:false` | Swiss-Prot vs TrEMBL |
| `fragment:false` | Exclude fragment sequences |
| `length:[100 TO 500]` | Sequence-length range |
| `mass:[50000 TO 100000]` | Molecular mass (Da) range |
| `existence:"Evidence at protein level"` | Protein-existence level |

### Annotation, features, GO, cross-refs
| Field | Meaning |
| --- | --- |
| `go:0005515` | GO term id (0005515 = protein binding) |
| `keyword:"Protein kinase"` | Controlled keyword |
| `family:"protein kinase"` | Protein family |
| `cc_function:*` | Has a function comment |
| `cc_disease:cancer` | Disease comment mentions cancer |
| `ft_domain:*` | Has any domain feature |
| `ft_transmem:*` | Has a transmembrane region |
| `xref:pdb` | Has a PDB cross-reference |
| `database:(type:alphafolddb)` | Has an AlphaFold cross-reference |

## Ranges and dates

Ranges are inclusive; `*` is an open bound.

```
length:[100 TO 500]           # 100–500 inclusive
mass:[* TO 50000]             # up to 50 kDa
date_created:[2023-01-01 TO *]        # created on/after 2023-01-01
date_modified:[2024-01-01 TO 2024-12-31]
```

## Wildcards

```
gene:BRCA?          # single char: BRCA1, BRCA2, …
gene:BRCA*          # multi char: BRCA1, BRCA2, BRCA1P1, …
protein_name:kinase*
```

Avoid leading wildcards (`*kinase`) — they are slow and often disabled.

## Existence (has-annotation) queries

A bare `*` value asks "does this field exist at all":

```
cc_function:*        # any function annotation
ft_binding:*         # any binding-site feature
xref:pdb             # any PDB structure
go_f:*               # any molecular-function GO term
```

## Vetted patterns

```
# Human reviewed kinases that have a solved structure
(protein_name:kinase OR family:kinase) AND organism_id:9606 AND reviewed:true AND xref:pdb

# Disease-associated, experimentally evidenced human proteins
cc_disease:* AND existence:"Evidence at protein level" AND organism_id:9606 AND reviewed:true

# Secreted proteins with a signal peptide
cc_subcellular_location:secreted AND ft_signal:* AND reviewed:true

# Recently updated human entries
organism_id:9606 AND date_modified:[2025-01-01 TO *] AND reviewed:true

# Well-characterized drug targets
(keyword:"Pharmaceutical" OR keyword:"Drug target") AND reviewed:true
```

## Field prefixes to remember

- `cc_` — comment blocks (function, disease, interaction, localization)
- `ft_` — sequence features (domains, sites, PTMs, variants)
- `go_` — Gene Ontology (`go_p` process, `go_c` component, `go_f` function)
- `xref_` / `database:` — cross-references to external resources

Retrieve the authoritative, current field list from
`GET https://rest.uniprot.org/configure/uniprotkb/search-fields` (searchable
query fields) — distinct from the *return* fields listed in `fields.md`.

## Docs

- Query fields: https://www.uniprot.org/help/query-fields
- Text search: https://www.uniprot.org/help/text-search
- API queries: https://www.uniprot.org/help/api_queries
