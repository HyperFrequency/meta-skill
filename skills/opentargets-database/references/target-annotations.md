# Target Annotations and Features

Open Targets treats a target as "any naturally-occurring molecule that can be
targeted by a medicinal product" — chiefly protein-coding genes identified by
Ensembl gene IDs, plus some RNAs and pseudogenes. These annotations answer *is
this gene druggable, safe, and biologically credible?*

## The twelve annotation categories

### 1. Tractability

Druggability potential per modality.

- **Small molecule** — from structural features and chemical precedence.
- **Antibody** — favored by cell-surface / secreted localization.
- **PROTAC (targeted degradation)** — E3-ligase compatibility; emerging modality.
- **Other** — gene therapy, RNA/oligonucleotide approaches.

Levels, best to worst:
1. **Clinical precedence** — target of an approved/clinical drug with similar
   mechanism.
2. **Discovery precedence** — target of tool compounds or preclinical compounds.
3. **Predicted tractable** — computational prediction only.
4. **Unknown** — insufficient data.

GraphQL: `tractability { label modality value }`.

### 2. Safety liabilities

Aggregated toxicity signals: `safetyLiabilities { event effects { direction
dosing } biosamples { tissueLabel cellLabel } }`. Each `effects` entry pairs a
`direction` (activation/inhibition) with a `dosing` note; `biosamples` are flat
(`tissueLabel`, `cellLabel`), not nested.

- **Sources** — ToxCast (HT toxicology), AOPWiki (adverse-outcome pathways),
  PharmGKB (pharmacogenomics), curated literature/clinical adverse events.
- **Flags** — organ toxicity (liver/kidney/cardiac), on-target liability,
  off-target effects, clinical adverse events from drugs hitting the gene.

### 3. Baseline expression

`baselineExpression(page: {index: 0, size: 50}) { rows { tissueBiosample {
biosampleId biosampleName } unit median specificity_score } }`. (The legacy
`target.expressions` field with nested `rna`/`protein` blocks was removed.)

- **Rows** — one row per tissue × assay; RNA vs protein rows are distinguished by
  `unit` (e.g. `TPM` vs `PPB (iBAQ)`). `median` is the summary level;
  `specificity_score` flags tissue-restricted expression.
- **Sources** — Expression Atlas / GTEx (RNA median TPM across tissues), Human
  Protein Atlas (protein IHC, subcellular localization).
- **Reads** — tissue specificity aids selectivity; ubiquitous expression hurts
  the therapeutic window.

### 4. Molecular interactions

Physical PPIs (IntAct, BioGRID, STRING), pathway/complex membership (Reactome),
and disease-relevant interactors.

### 5. Gene essentiality

- **Project Score** — CRISPR-Cas9 fitness screens across 300+ cancer cell lines.
- **DepMap** — large-scale cancer dependency; identifies common-essential genes.
- Scaled 0 (non-essential) → 1 (essential); pan-essential genes are risky
  targets (poor selectivity between disease and normal cells).

### 6. Chemical probes and tool compounds

High-quality validation reagents from the Probes & Drugs Portal and the SGC
(Target Enabling Packages). Quality bar: potency (often IC50 < 100 nM),
selectivity (>30-fold), demonstrated cell activity, negative control available.

### 7. Pharmacogenetics

Variant-drug pairs affecting drug response (dosing, efficacy, toxicity), with
clinical annotations and evidence levels. For dedicated pharmacogenomic dosing,
use the `clinpgx-database` skill.

### 8. Genetic constraint (gnomAD)

`geneticConstraint { constraintType score exp obs }`.

- **pLI** — probability of loss-of-function intolerance, 0–1; **pLI > 0.9** =
  LoF-intolerant, suggests essentiality.
- **LOEUF** — observed/expected LoF upper-bound fraction; **lower = more
  constrained**; more interpretable than pLI across the range.
- **Missense constraint** — Z-scores / O:E for missense depletion.
- High constraint implies important function and a potential **safety concern**
  if inhibited.

### 9. Comparative genomics

Ortholog data (Ensembl Compara) across mouse/rat/zebrafish etc., with orthology
confidence (1:1, 1:many) and percent identity — gauges model-organism
transferability.

### 10. Cancer annotations

- **Cancer Gene Census** — oncogene / TSG / fusion role, tier 1 (established) or
  2 (emerging), tumor and mutation types.
- **Cancer Hallmarks** — functional roles (proliferation, apoptosis evasion,
  metastasis, ...).
- **Oncology trials** — drugs in development against the gene.

### 11. Mouse phenotypes

MGI knockout/mutation phenotypes and disease-model associations (Mammalian
Phenotype Ontology) — predict on-target effects and safety liabilities.

### 12. Pathways (Reactome)

Curated, hierarchical biological pathways placing the target in functional
context: `pathways { pathway pathwayId }`. Useful for mechanism hypotheses and
finding related targets.

## Comprehensive target-profile query

```graphql
query targetProfile($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    biotype
    tractability { label modality value }
    safetyLiabilities {
      event
      effects { direction dosing }
      biosamples { tissueLabel cellLabel }
    }
    baselineExpression(page: {index: 0, size: 20}) {
      rows {
        tissueBiosample { biosampleId biosampleName }
        unit
        median
      }
    }
    chemicalProbes { id origin isHighQuality }
    drugAndClinicalCandidates {
      count
      rows {
        maxClinicalStage
        drug { id name }
        diseases { disease { id name } }
        clinicalReports { trialPhase trialOverallStatus }
      }
    }
    geneticConstraint { constraintType score exp obs }
    pathways { pathway pathwayId }
  }
}
```

Variables: `{"ensemblId": "ENSG00000157764"}`. Note the current schema has no
`target.expressions` or `target.knownDrugs`; use `baselineExpression` and
`drugAndClinicalCandidates` as shown.

## Prioritization heuristics

**Assess in this order:** druggability (tractability) → safety → disease
relevance → validation readiness → clinical-path considerations.

### Red flags

- High essentiality **and** ubiquitous expression → poor therapeutic window.
- Multiple safety liabilities → toxicity risk.
- High genetic constraint (**pLI > 0.9** / low LOEUF) → critical gene, inhibition
  may harm.
- No tractability precedence → higher risk, longer development.
- Conflicting evidence across sources → investigate deeper.

### Green flags

- Clinical precedence in a related indication → de-risked mechanism.
- Tissue-specific expression → better selectivity.
- Chemical probes available → faster validation.
- Low essentiality **with** disease relevance → good therapeutic window.
- Multiple evidence types converge → higher confidence.
