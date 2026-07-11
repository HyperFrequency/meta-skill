# Evidence Types and Data Sources

Evidence is any event that implicates a target as a potential causal gene/protein
for a disease. Every evidence record is standardized to an **Ensembl gene ID**
(target) and an **EFO term** (disease/phenotype), and is grouped into a broad
**data type** (`datatypeId`) built from specific **data sources** (`datasourceId`).
The `evidences` query filters server-side by **`datasourceIds`** — there is no
`datatypes` argument. To select a whole data type, pass all of its source IDs, or
omit the filter and group on the `datatypeId` field returned on each row.

## The seven data types

### 1. `genetic_association`

Human genetics linking variants to disease — the strongest evidence for disease
relevance.

- **GWAS** — common-variant, population-level associations; filtered by
  Locus-to-Gene (**L2G**) scores (>0.05), with fine-mapping and colocalization.
  Sources include GWAS Catalog, FinnGen, UK Biobank, EBI GWAS.
- **Gene burden** — aggregate rare-variant tests; key for Mendelian/rare disease.
- **ClinVar (germline)** — expert variant interpretations (pathogenic → benign).
- **Genomics England PanelApp** — expert green/amber/red gene-disease ratings.
- **Gene2Phenotype** — curated gene-disease relationships with inheritance.
- **UniProt literature & variants**, **Orphanet**, **ClinGen** — curated
  gene-disease validity assertions.

### 2. `somatic_mutation`

Cancer genomics identifying driver genes.

- **Cancer Gene Census** — expert-curated cancer genes with tier (1 strong,
  2 emerging), mutation and tumor types.
- **IntOGen** — computational driver-gene predictions across large cohorts.
- **ClinVar (somatic)** — oncogenic/likely-oncogenic classifications.
- **Cancer Biomarkers** — FDA/EMA-approved and trial prognostic/predictive markers.

### 3. `known_drug`

Clinical precedence: drugs targeting a gene for a disease indication.

- **ChEMBL** — approved (Phase 4), clinical (Phase 1–3), and withdrawn drugs as
  drug-target-indication triplets. Surfaced via `drugAndClinicalCandidates` with
  `maxClinicalStage` and per-trial `clinicalReports { trialPhase,
  trialOverallStatus }`; mechanism detail comes from the drug's
  `mechanismsOfAction`.

### 4. `affected_pathway`

Genes linked to disease via pathway perturbation and functional screens.

- **CRISPR screens** / **Project Score** (Cancer Dependency Map) — knockout
  fitness / essentiality across cancer cell lines.
- **SLAPenrich** — somatic-mutation pathway enrichment.
- **PROGENy** — inferred signaling pathway activity.
- **Reactome** — curated pathway annotations.
- **Gene signatures** — expression-based pathway activity patterns.

### 5. `rna_expression`

Differential expression in disease vs control tissue.

- **Expression Atlas** — RNA-Seq/microarray differential expression with log2
  fold-change and p-values, plus baseline expression across tissues/conditions.

### 6. `animal_model`

In-vivo phenotypes from gene perturbation.

- **IMPC** (International Mouse Phenotyping Consortium) — systematic mouse
  knockout phenotypes mapped to disease via ontologies.

### 7. `literature`

Text-mining of biomedical literature.

- **Europe PMC** — gene-disease co-occurrence in abstracts, normalized by
  citation count and weighted by publication type/recency.

## Scoring

Each source has its own methodology; scores are normalized toward **0–1**, where
higher means stronger evidence. Scores rank **relative strength, not confidence
or probability**.

- **Binary/categorical** — ClinVar pathogenic ≈ 1.0, likely-pathogenic ≈ 0.99;
  Gene2Phenotype confirmed/probable; PanelApp green/amber/red.
- **Statistical** — GWAS L2G composites; gene-burden significance; expression
  adjusted p-values and fold-changes.
- **Clinical precedence** — known-drug phase weights (Phase 4 = 1.0, Phase 3 ≈
  0.8, ...) modified by trial status.
- **Computational** — IntOGen q-values; PROGENy/SLAPenrich pathway scores.

Overall association scores aggregate all evidence for a pair via a **harmonic
sum** across data types, so many weak sources do not trivially outweigh one
strong one. Read `datatypeScores` (per-type breakdown) rather than the headline
score alone.

## Interpretation by data type

| Data type | Strength | Watch out for |
| --- | --- | --- |
| `genetic_association` | Strongest human disease relevance; Mendelian = high confidence | GWAS needs L2G to name the causal gene; ancestry/population effects |
| `somatic_mutation` | Direct in cancer; drivers indicate therapeutic potential | Cancer-type specificity |
| `known_drug` | Clinical validation; approved = highest | Mechanism relevance to a *new* indication; Phase 1–2 is early/risky |
| `affected_pathway` | Mechanistic plausibility | May not predict clinical success |
| `rna_expression` | Observational | Correlation not causation; may be disease consequence |
| `animal_model` | Translational biology | Variable human translation; best when phenotype matches |
| `literature` | Exploratory signal | Publication bias; requires manual review to validate |

## General considerations

1. **Convergent evidence across types raises confidence** more than a single
   strong source.
2. **Under-studied diseases score lower** despite potentially valid targets —
   limited research, not weak biology.
3. **Scores are not probabilities** of clinical success.
4. **Context matters** — disease mechanism, target druggability, related-
   indication precedence, and safety all modulate how to read a score.
5. **Source reliability varies** — weight expert-curated sources (ClinGen,
   Gene2Phenotype, Cancer Gene Census) above computational predictions and
   sole text-mining hits.
6. **Validate critical calls** in primary databases (ClinVar, ClinGen) and by
   reading the `studyId` / `literature` behind the record.
