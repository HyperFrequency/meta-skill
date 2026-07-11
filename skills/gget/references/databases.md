# Databases Behind gget

Each gget module is a thin, tested client over a live public database. Because
those databases change structure over time, gget is re-tested biweekly and
patched to match — so the single most important operational habit is to **keep
gget current** (`uv pip install --upgrade gget`) and to **pin versions** when a
result must be reproducible.

## Source Map

| Database | Modules | Cadence | Access |
|----------|---------|---------|--------|
| Ensembl | `ref`, `search`, `info`, `seq` | numbered releases, ~every 3 months | FTP + REST |
| UCSC Genome Browser | `blat` | new assemblies periodically | web service |
| UniProt | `info`, `seq` (AA), `elm` | Swiss-Prot weekly, TrEMBL monthly | REST |
| NCBI (Gene/Protein/RefSeq) | `info`, `bgee` (non-Ensembl) | continuous | E-utilities |
| RCSB PDB | `pdb` | weekly | REST |
| ELM | `elm` | periodic (local download) | downloaded DB |
| NCBI BLAST DBs (nt/nr/…) | `blast` | regular | BLAST API |
| ARCHS4 | `archs4` | periodic | HTTP API |
| CZ CELLxGENE Discover | `cellxgene` | continuous | Census API |
| Bgee | `bgee` | numbered releases | REST |
| Enrichr / modEnrichr | `enrichr` | ongoing | REST |
| Open Targets | `opentargets` | ~quarterly | GraphQL |
| cBioPortal | `cbio` | continuous | web API |
| COSMIC | `cosmic` | regular releases | licensed download |
| AlphaFold2 (local) | `alphafold` | model params via `gget setup` | local compute |
| OpenAI API | `gpt` | model updates | REST (key) |

## Reproducibility

Pin the version, record the tool version, and save raw outputs:

```python
import gget
print(gget.__version__)

# Pin an Ensembl release
gget.ref("homo_sapiens", release=110)

# Pin a CELLxGENE census snapshot
gget.cellxgene(gene=["PAX7"], census_version="2023-07-25")

# Persist results with a dated filename
res = gget.search(["ACE2"], species="homo_sapiens")
res.to_csv("search_ACE2_2026-01-15.csv", index=False)
```

## When Databases Drift

A module that worked before can fail after an upstream restructure. Recovery order:

1. `uv pip install --upgrade gget` and retry.
2. Check https://github.com/pachterlab/gget/issues for a known break/fix.
3. For repeated large-scale work, prefer local backends (`diamond` with a saved
   `--diamond_db`, a downloaded `cosmic` TSV) and cache results to avoid hammering
   rate-limited APIs.

## Per-Database Notes

- **Ensembl:** IDs are stable across releases; `gene_name` values are not. Use
  species shortcuts (`human`, `mouse`) and `gget ref --list_species` to discover
  valid names.
- **UniProt:** accessions are more stable than gene names; Swiss-Prot annotations
  are manually curated. `-pdb` in `gget info` adds runtime — set it only when you
  need structure IDs.
- **BLAST/BLAT:** start at defaults, then narrow the database (`swissprot`,
  `refseq_protein`) and tune the E-value to query length.
- **CELLxGENE:** gene symbols are case-sensitive (`PAX7` vs `Pax7`); a wrong case
  returns empty rather than erroring.
- **COSMIC:** free for academic use, licensed for commercial; requires an account
  and a one-time database download before any query.
- **cBioPortal:** cache locally (`-dd`) for repeated analyses.

## Citation

Cite gget **and** the underlying database(s):

- **gget:** Luebbert, L. & Pachter, L. (2023). *Efficient querying of genomic
  reference databases with gget.* Bioinformatics.
  https://doi.org/10.1093/bioinformatics/btac836
- **Databases:** ARCHS4 — Lachmann et al., Nat. Commun. 2018; Bgee — Bastian et
  al., 2021; and the citation each source database requests.
