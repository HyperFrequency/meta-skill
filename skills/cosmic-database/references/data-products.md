# COSMIC Data Products Reference

COSMIC (Catalogue of Somatic Mutations in Cancer) is maintained by the Wellcome
Sanger Institute at https://cancer.sanger.ac.uk/cosmic. It is distributed as a
set of **whole-file dumps** (TSV/CSV/VCF, gzip-compressed) rather than a
fine-grained public query API. Files are grouped by genome assembly and release,
and the interactive web interface offers point lookups for exploration.

## Release model and versioning

- COSMIC ships new releases periodically (historically a few per year). As of the
  source material the current release was **v102 (May 2025)**; treat that as a
  snapshot, not a constant — check the release notes for the live version.
- Use the literal token `latest` in a file path to always resolve the newest
  release, or pin a version (e.g. `v102`) for reproducibility.
- **Filenames and paths change between major releases.** Older releases used flat
  names like `CosmicMutantExport.tsv.gz`; recent releases moved to a
  `Cosmic_<Product>_v<NN>_<Assembly>.tsv.gz` convention. Always confirm the exact
  filename against the current COSMIC download page or release notes before
  scripting a path. The names below are the classic/legacy forms — accurate in
  spirit, but verify per release.

## Genome assemblies

All genomic data is published for two reference genomes. Pick one deliberately
and keep it consistent across a pipeline:

- **GRCh38** (hg38) — current standard, recommended for new work.
- **GRCh37** (hg19) — legacy, for older pipelines and cross-study comparison.

Legacy path pattern: `{assembly}/cosmic/{version}/{filename}`, e.g.
`GRCh38/cosmic/latest/CosmicMutantExport.tsv.gz`.

## Data products catalogue

### Core somatic mutations
- `CosmicMutantExport.tsv.gz` — complete coding mutations (SNVs + small indels)
  with genomic coordinates, annotations, sample and tumor-type associations.
- `CosmicMutantExportCensus.tsv.gz` — the same, restricted to Cancer Gene Census
  genes (much smaller, good first pull).
- `CosmicCodingMuts.vcf.gz` — coding mutations in VCF 4.x, INFO fields carry
  COSMIC annotations; ships with a `.tbi` tabix index.
- `CosmicNonCodingVariants.vcf.gz` — non-coding variants in VCF.

### Cancer Gene Census (CGC)
- `cancer_gene_census.csv` — expert-curated list of ~700+ genes with strong
  evidence of a causal role in cancer. Columns include gene role
  (oncogene / TSG / fusion), mutation types, translocation partners, evidence
  **Tier** (1 or 2), hallmark associations, and somatic/germline flags. This is
  the canonical "is this a known cancer gene" reference and the standard filter
  for prioritizing variants.

### Mutational signatures
Published under a `signatures/` area (e.g. `signatures/signatures.tsv`). Current
reference set is **v3.4** (introduced around COSMIC v98):
- **SBS** — Single Base Substitution signatures (96-channel profiles).
- **DBS** — Doublet Base Substitution signatures (78-channel).
- **ID** — Insertion/Deletion signatures (83-channel).
Each signature carries an etiology annotation. These are the reference profiles
that signature-deconvolution tools (SigProfiler, deconstructSigs) fit against.

### Structural variants and fusions
- `CosmicStructExport.tsv.gz` — structural breakpoints, translocations, large
  rearrangements.
- `CosmicFusionExport.tsv.gz` — curated gene-fusion events.

### Copy number and expression
- `CosmicCompleteCNA.tsv.gz` — copy-number gains/losses, amplifications and
  deletions, segment- and gene-level.
- `CosmicCompleteGeneExpression.tsv.gz` — over/under-expression Z-scores by
  gene and tissue.

### Drug-resistance mutations
- `CosmicResistanceMutations.tsv.gz` — mutations linked to therapy resistance,
  with drug/treatment associations and clinical relevance.

### Cell Lines Project
Cell-line-specific mutation, CNA, fusion, and microsatellite-instability files
for cancer cell lines (useful for benchmarking and model systems).

### Sample metadata
- `CosmicSample.tsv.gz` — per-sample metadata: tumor site/histology, sample
  source, study references. Join on the sample identifier to attach clinical
  context to mutation rows.

## Key fields

### Mutation export (`CosmicMutantExport`)
- `Gene name` — HGNC symbol.
- `Accession Number` — transcript identifier.
- `COSMIC ID` / mutation ID — unique mutation identifier (e.g. `COSV`/`COSM`).
- `CDS mutation` — coding-sequence change (e.g. `c.35G>A`).
- `AA mutation` — amino-acid change (e.g. `p.G12D`).
- `Primary site` / `Primary histology` — anatomical location and tumor class.
- Genomic coordinates — chromosome, position, strand.
- `Mutation type` — substitution / insertion / deletion / etc.
- Zygosity, `Pubmed ID` — heterozygous/homozygous status, literature reference.

### Cancer Gene Census (`cancer_gene_census.csv`)
- `Gene Symbol`, `Entrez GeneId`.
- `Role in Cancer` — oncogene, TSG, fusion (a gene may have several).
- `Mutation Types`, `Translocation Partner`.
- `Tier` — evidence classification (1 = strong, 2 = emerging).
- `Hallmark`, `Somatic`, `Germline`.

## File formats

- **TSV/CSV** — headered, gzip-compressed. Read with `pandas.read_csv(...,
  compression='gzip')`, or stream with `awk`/`zcat` for huge files.
- **VCF** — VCF 4.x, gzip-compressed and tabix-indexed (`.vcf.gz` + `.vcf.gz.tbi`).
  Read with `pysam`, `bcftools`, `cyvcf2`, or GATK; region queries need the index.

## Downstream tool ecosystem

COSMIC files feed directly into:
- **Variant annotation** — VEP, ANNOVAR, SnpEff.
- **Signature analysis** — SigProfiler, deconstructSigs, MuSiCa (fit the SBS/DBS/ID
  reference set).
- **Cancer-genomics portals** — cBioPortal, OncoKB, CIViC (complementary
  annotation of the same variants).
- **General analysis** — pandas, scikit-learn for ML feature tables.

## Citation and licensing

Cite: Tate JG, Bamford S, Jubb HC, et al. *COSMIC: the Catalogue Of Somatic
Mutations In Cancer.* Nucleic Acids Research. 2019;47(D1):D941–D947.

COSMIC data is free for academic and non-commercial use with registration;
commercial use requires a license through QIAGEN
(`cosmic-translation@sanger.ac.uk`). General contact: `cosmic@sanger.ac.uk`.

- Website: https://cancer.sanger.ac.uk/cosmic
- Help/docs: https://cancer.sanger.ac.uk/cosmic/help
- Release notes: https://cancer.sanger.ac.uk/cosmic/release_notes
- Registration: https://cancer.sanger.ac.uk/cosmic/register
