# Ensembl REST API — Endpoint Reference

Full catalogue of the Ensembl REST endpoint categories. Paths, parameters, and
examples below are the canonical URL contract; drive them with the client in
[query-helper.md](query-helper.md) or plain `requests`.

## Servers

| Purpose | Base URL |
| --- | --- |
| Current assemblies (GRCh38, all species) | `https://rest.ensembl.org` |
| Human GRCh37 / hg19 only | `https://grch37.rest.ensembl.org` |
| Non-vertebrates (plants, fungi, metazoa, protists, bacteria) | Ensembl Genomes servers, e.g. `https://rest.ensemblgenomes.org` |

**Rate limits:** ~15 requests/second for anonymous clients. Registered clients
get a higher hourly budget. On HTTP 429, wait for the `Retry-After` header.

**Release:** do not assume a fixed release. Read it live from `GET /info/data`.
(Release 115 was current in September 2025.)

---

## 1. Archive

Historical records for retired identifiers.

- `GET /archive/id/:id` — archived entry for a retired ID.
  `GET /archive/id/ENSG00000157764`
- `POST /archive/id` — batch, body `{"id": ["ENSG...", ...]}`.

## 2. Comparative Genomics

Gene trees, alignments, and homology across species.

- `GET /alignment/region/:species/:region` — genomic alignments for a region.
- `GET /genetree/id/:id` — gene tree for a family (`ENSGT00390000003602`).
- `GET /genetree/member/id/:id` — gene tree containing a member gene.
- `GET /genetree/member/symbol/:species/:symbol` — gene tree by symbol.
- `GET /homology/id/:id` — orthologs/paralogs for a gene. Params:
  `target_species`, `type` (`orthologues` | `paralogues` | `all`), `format`
  (`full` | `condensed`). `GET /homology/id/ENSG00000139618?target_species=mouse`
- `GET /homology/symbol/:species/:symbol` — homologs by symbol.

## 3. Cross References (xrefs)

Link Ensembl objects to external databases (UniProt, RefSeq, HGNC, …).

- `GET /xrefs/id/:id` — external references for an Ensembl ID.
- `GET /xrefs/symbol/:species/:symbol` — Ensembl objects for an external symbol.
- `GET /xrefs/name/:species/:name` — search by external name (e.g. `NP_000050`).

## 4. Information

Metadata about species, assemblies, biotypes, and releases.

- `GET /info/species` — all species with assemblies and taxonomy IDs.
- `GET /info/assembly/:species` — assembly build (e.g. GRCh38.p14).
- `GET /info/assembly/:species/:region` — details for a chromosome/region.
- `GET /info/biotypes/:species` — available gene biotypes.
- `GET /info/analysis/:species` — analysis logic names.
- `GET /info/data` — current release version(s). **Use this to detect release.**

## 5. Linkage Disequilibrium (LD)

- `GET /ld/:species/:id/:population_name` — LD for a variant in a population.
  `GET /ld/human/rs1042522/1000GENOMES:phase_3:KHV`
- `GET /ld/pairwise/:species/:id1/:id2` — LD between two variants.
- `GET /ld/region/:species/:region/:population_name` — LD across a region.

## 6. Lookup

- `GET /lookup/id/:id` — object by Ensembl ID. Param `expand=1` includes child
  objects (transcripts, translations). `GET /lookup/id/ENSG00000139618?expand=1`
- `POST /lookup/id` — **batch**, body `{"ids": ["ENSG00000139618", "ENSG00000157764"]}`.
- `GET /lookup/symbol/:species/:symbol` — object by symbol. Param `expand=1`.
- `POST /lookup/symbol/:species` — batch, body `{"symbols": ["BRCA2", "TP53"]}`.

## 7. Mapping

Convert coordinates across systems and assemblies.

- `GET /map/cdna/:id/:region` — cDNA → genomic. `GET /map/cdna/ENST00000288602/100..300`
- `GET /map/cds/:id/:region` — CDS → genomic.
- `GET /map/translation/:id/:region` — protein → genomic.
  `GET /map/translation/ENSP00000288602/1..100`
- `GET /map/:species/:asm_one/:region/:asm_two` — assembly ↔ assembly.
  `GET /map/human/GRCh37/7:140453136..140453136/GRCh38`

## 8. Ontologies and Taxonomy

- `GET /ontology/id/:id` — ontology term (`GO:0005515`).
- `GET /ontology/name/:name` — search ontology by term name (URL-encode spaces).
- `GET /ontology/ancestors/:id` and `/ontology/descendants/:id` — term graph.
- `GET /taxonomy/classification/:id` — lineage for a taxon (`9606` = human).
- `GET /taxonomy/id/:id` — taxonomy node by NCBI taxon ID or name.
- `GET /taxonomy/name/:name` — taxonomy nodes by name.

## 9. Overlap

Features overlapping an object or region.

- `GET /overlap/id/:id` — features overlapping a gene/transcript. Param `feature`
  (`gene`, `transcript`, `cds`, `exon`, `repeat`, …). Requires at least one
  `feature`.
- `GET /overlap/region/:species/:region` — features in an interval. Param
  `feature` (`gene`, `transcript`, `variation`, `somatic_variation`,
  `structural_variation`, `regulatory`, `motif`, `repeat`, `simple`, `misc`, …).
  `GET /overlap/region/human/7:140424943..140624564?feature=gene`
- `GET /overlap/translation/:id` — protein-level features (domains, PTMs).

## 10. Phenotype Annotations

- `GET /phenotype/accession/:species/:accession` — by ontology accession
  (`EFO:0003767`).
- `GET /phenotype/gene/:species/:gene` — phenotype associations for a gene.
- `GET /phenotype/region/:species/:region` — phenotypes in a region.
- `GET /phenotype/term/:species/:term` — search phenotypes by free text.

## 11. Regulation

- `GET /regulatory/species/:species/microarray/:microarray/:probe` — probe info.
- `GET /species/:species/binding_matrix/:binding_matrix_id` — TF binding matrix
  (`ENSPFM0001`).

## 12. Sequence

- `GET /sequence/id/:id` — sequence for an ID. Params: `type` (`genomic` |
  `cds` | `cdna` | `protein`), `format`, plus `expand_5prime`/`expand_3prime`,
  `mask`, `multiple_sequences`. `GET /sequence/id/ENSG00000139618?type=protein`
- `POST /sequence/id` — batch, body `{"ids": ["ENSG00000139618", ...]}`.
- `GET /sequence/region/:species/:region` — sequence for an interval. Params:
  `coord_system`, `coord_system_version`, `mask`, `expand_*`.
- `POST /sequence/region/:species` — batch, body `{"regions": ["X:1000000..1000100:1"]}`.

**FASTA output:** send header `Content-Type: text/x-fasta` (and read
`response.text`), or append the `.fasta` extension to the path.

## 13. Transcript Haplotypes

- `GET /transcript_haplotypes/:species/:id` — haplotypes from phased genotypes
  for a transcript (`ENST00000288602`).

## 14. Variant Effect Predictor (VEP)

Predict functional consequences of variants. Rich parameter set (e.g.
`canonical`, `hgvs`, `protein`, `sift`, `polyphen`, `ccds`, `domains`,
`numbers`, `mane`, `AlphaMissense`, plugin flags).

- `GET /vep/:species/hgvs/:hgvs_notation` — from HGVS.
  `GET /vep/human/hgvs/ENST00000366667:c.803C>T`
- `POST /vep/:species/hgvs` — batch, body `{"hgvs_notations": ["ENST...:c.803C>T"]}`.
- `GET /vep/:species/id/:id` — from a colocated variant ID (`rs699`).
- `POST /vep/:species/id` — batch, body `{"ids": ["rs699", "rs6025"]}`.
- `GET /vep/:species/region/:region/:allele` — from region + allele.
  `GET /vep/human/region/7:140453136:C/T`
- `POST /vep/:species/region` — batch, body `{"variants": ["7 140453136 . C T . . ."]}`
  (VCF-style rows).

## 15. Variation

- `GET /variation/:species/:id` — variant record. Params: `pops=1` (population
  frequencies), `genotypes=1`, `phenotypes=1`, `population_genotypes=1`.
  `GET /variation/human/rs699?pops=1`
- `POST /variation/:species` — batch, body `{"ids": ["rs699", "rs6025"]}`.
- `GET /variation/:species/pmcid/:pmcid` — variants cited in a PMC article.
- `GET /variation/:species/pmid/:pmid` — variants cited in a PubMed article.

## 16. Variation GA4GH

GA4GH-standard access.

- `POST /ga4gh/beacon` — beacon query for variant presence.
- `GET /ga4gh/features/:id` and `POST /ga4gh/features/search`.
- `POST /ga4gh/variants/search`, `POST /ga4gh/callsets/search`,
  `POST /ga4gh/datasets/search`.

---

## Response Formats

Most endpoints negotiate format via the request header, a `content-type` query
param, or a path extension:

| Format | How to request |
| --- | --- |
| JSON (default) | header `Content-Type: application/json` |
| FASTA (sequences) | header `Content-Type: text/x-fasta` or `.fasta` extension |
| XML | header `Content-Type: text/xml` (subset of endpoints) |
| Plain text | header `Content-Type: text/plain` |

## Shared Parameters

- `expand` — include child objects (transcripts, translations) on `lookup`.
- `format` — `full` vs `condensed` (homology), or output format elsewhere.
- `db_type` — `core` (default), `otherfeatures`, `variation`, `funcgen`.
- `object_type` — restrict the returned object type.
- `species` — common name (`human`) or scientific name (`homo_sapiens`).
- `callback` — JSONP callback name.

## Error Codes

| Code | Meaning | Action |
| --- | --- | --- |
| 200 | Success | — |
| 400 | Bad request (invalid params) | Fix the URL/params; do not retry blindly. |
| 404 | Not found (unknown ID) | The identifier does not exist for that species/assembly. |
| 429 | Rate limit exceeded | Sleep for `Retry-After` seconds, then retry. |
| 5xx | Server error | Retry with exponential back-off. |

## Practical Notes

1. **Prefer batch POST endpoints** for multiple IDs/regions — one round trip
   instead of N.
2. **Cache** per-release responses; data changes only on a new release.
3. **Choose the server by assembly** — GRCh37 has its own host.
4. **URL-encode** free-text parameters (ontology/phenotype terms, HGVS with
   special characters).
5. **Coordinates are 1-based, inclusive**; region syntax is `chr:start..end` or
   `chr:start-end`, optionally with a `:strand` suffix.
