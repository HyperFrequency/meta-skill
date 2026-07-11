# STRING REST API Reference

Complete endpoint, parameter, and output specification for the STRING API.
Base URL: `https://string-db.org/api`. Pin a version for reproducibility, e.g.
`https://version-12-0.string-db.org/api`. Official docs: `https://string-db.org/help/api/`.

## Request Anatomy

```
{base}/{output_format}/{method}?{params}
```

- `output_format` — one of `tsv`, `tsv-no-header`, `json`, `xml`, `psi-mi`,
  `psi-mi-tab`, `image`, `highres_image`, `svg` (availability depends on
  method; see each method below).
- `method` — `get_string_ids`, `network`, `interaction_partners`,
  `ppi_enrichment`, `enrichment`, `homology`, `version`, plus image variants.
- Send as GET for small inputs; use **POST** for large identifier lists.

### Shared parameters

| Param | Notes |
|---|---|
| `identifiers` | Required. Proteins separated by a carriage return (`%0d` in a raw URL; join with `"\r"` in `requests`). |
| `species` | NCBI taxon ID. Required for >10 identifiers; always send it. |
| `caller_identity` | Short string identifying your app/project. Send on every call. |

## Methods

### 1. `get_string_ids` — identifier mapping

Map gene symbols, UniProt IDs, and synonyms to STRING IDs. Run this first.

- Endpoint: `/tsv/get_string_ids`
- Extra params: `limit` (matches per query, default 1), `echo_query` (1 to
  include the original query term in output).
- Output columns: `queryItem`, `queryIndex`, `stringId`, `ncbiTaxonId`,
  `taxonName`, `preferredName`, `annotation`.

### 2. `network` — interaction table

- Endpoint: `/tsv/network` (also `/json/network`, `/xml/network`).
- Extra params:
  - `required_score` — 0-1000 confidence cutoff (default 400).
  - `network_type` — `functional` (default) or `physical`.
  - `add_nodes` — add N most-connected neighbors (0-10) to widen the network.
  - `show_query_node_labels` — 1 to force query labels.
- Output columns: `stringId_A`, `stringId_B`, `preferredName_A`,
  `preferredName_B`, `ncbiTaxonId`, `score` (combined, 0-1), then per-channel
  subscores `nscore`, `fscore`, `pscore`, `ascore`, `escore`, `dscore`,
  `tscore`. Note: TSV scores are returned as 0-1 floats even though the
  `required_score` filter is on the 0-1000 scale.

### 3. `interaction_partners` — partners of the input

- Endpoint: `/tsv/interaction_partners`.
- Extra params: `required_score`, `limit` (max partners returned per input
  protein, default 10).
- Output columns: same schema as `network`. Use to find hubs or expand a seed
  set; unlike `network`, it returns partners even if they are not among your
  input identifiers.

### 4. `ppi_enrichment` — network connectivity test

- Endpoint: `/json/ppi_enrichment` (also `/tsv/`).
- Extra params: `required_score`.
- Output fields: `number_of_nodes`, `number_of_edges`,
  `expected_number_of_edges` (edges in a random set of the same size drawn from
  the same-degree background), `average_node_degree`,
  `local_clustering_coefficient`, `p_value`.
- Interpretation: `p_value < 0.05` => the proteins are more connected than
  chance, i.e. they likely share function / form a module. A high p-value does
  not prove the proteins are unrelated, only that STRING sees no excess
  connectivity above background.

### 5. `enrichment` — functional term enrichment

- Endpoint: `/tsv/enrichment` (also `/json/`).
- No score threshold; enrichment always uses the full-confidence background.
- Categories returned in the `category` column: `Process`, `Function`,
  `Component` (GO BP/MF/CC), `KEGG`, `RCTM` (Reactome), `WikiPathways`,
  `Pfam`, `InterPro`, `SMART`, `Keyword` (UniProt), `NetworkNeighborAL`, `PMID`,
  `COMPARTMENTS`, `TISSUES`, `DISEASES`, `MPO`, `Monarch`. Exact set varies by
  species.
- Output columns: `category`, `term`, `number_of_genes`,
  `number_of_genes_in_background`, `ncbiTaxonId`, `inputGenes`,
  `preferredNames`, `p_value`, `fdr`, `description`.
- Statistics: Fisher's exact test, Benjamini-Hochberg FDR. Treat `fdr < 0.05`
  as significant.

### 6. `homology` — similarity scores

- Endpoint: `/tsv/homology`.
- Output: pairwise best-hit bit-score-derived similarity between the input
  proteins (within one species). For cross-species orthology, use
  `homology_best` or run against `ensembl-database` / `gget` instead.

### 7. `version` — database version

- Endpoint: `/tsv/version`. Output columns: `string_version`,
  `stable_address`. Record this in methods sections for reproducibility.

### 8. Image methods — rendered network

- Endpoints: `/image/network` (PNG), `/highres_image/network` (2x PNG),
  `/svg/network` (vector).
- Extra params:
  - `network_flavor` — `evidence` (colored lines by evidence type, default),
    `confidence` (line thickness = combined score), or `actions`
    (activation/inhibition arrows; requires the actions dataset).
  - `required_score`, `add_nodes`, `hide_node_labels`, `hide_disconnected_nodes`,
    `block_structure_pics_in_bubbles`.
- Output: binary image bytes. Write with `open(path, "wb")`.

## STRING Identifier Format

`{taxonId}.{ensemblProteinId}`, e.g. `9606.ENSP00000269305` (human TP53). The
prefix is the NCBI taxon; the suffix is usually an Ensembl protein ID (`ENSP...`).
Passing STRING IDs directly skips the name-resolution step and is unambiguous.

## Output Formats

Swap the format segment in the URL:

| Segment | Content |
|---|---|
| `tsv` | Tab-separated with header (default for data) |
| `tsv-no-header` | Tab-separated, no header row |
| `json` | Array of objects |
| `xml` | XML |
| `psi-mi`, `psi-mi-tab` | Proteomics Standards Initiative interchange formats |
| `image` / `highres_image` / `svg` | Rendered network |

## Async Values/Ranks Enrichment (large ranked lists)

For enrichment over a full ranked/valued list (e.g. differential-expression
log-fold-changes) rather than a plain gene set:

1. `POST /json/get_api_key` -> obtain a job API key.
2. Submit tab-separated `proteinId<TAB>value` rows with the key.
3. Poll `/json/valuesranks_enrichment_status?job_id={id}` until complete.
4. Retrieve the enrichment tables and figures.

Requirements: the complete protein set (do not pre-filter), a numeric value per
protein, and the correct species. This is aggregate-rank enrichment, distinct
from the simple set-based `enrichment` method above.

## Error Handling

| HTTP | Meaning | Fix |
|---|---|---|
| 200 empty body | Nothing passed the filter | Lower `required_score`; verify species |
| 400 | Bad parameters/syntax | Check separator, param names |
| 404 | Unknown protein/species | Map IDs first; verify taxon ID |
| 500 | Server error / too large | Reduce input size; retry after a pause |

Guard every call with `response.raise_for_status()` and handle an empty body
distinctly from an HTTP error — an empty 200 usually means the threshold was
too high, not that the request failed.

## Bulk Download (skip the API)

For proteome-scale work, download flat files instead of looping the API:
`https://string-db.org/cgi/download` provides full interaction files, protein
annotations, per-channel evidence, and pathway mappings per species. For a
whole proteome, the website "Upload proteome" workflow builds the complete
network and predicts function server-side.
