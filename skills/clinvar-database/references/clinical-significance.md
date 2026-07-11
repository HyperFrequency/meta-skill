# ClinVar Clinical Significance — Interpretation Guide

ClinVar uses standardized terminology to describe how a variant relates to a
phenotype. Reading a classification correctly means reading it **together with
its review status** and knowing which of the three classification tracks it
belongs to.

> **Disclaimer.** ClinVar assertions are submitted evidence, not a diagnosis.
> Do not use them for direct medical decision-making without review by a
> genetics professional, and always evaluate a variant in the specific clinical
> and population context.

## Three classification tracks

1. **Germline** — inherited variants tied to Mendelian disease and drug response
   (ACMG/AMP terms).
2. **Somatic — clinical impact** — acquired variants with therapeutic
   implications (AMP/ASCO/CAP tiers).
3. **Somatic — oncogenicity** — acquired variants that drive cancer
   (ClinGen/CGC/VICC terms).

A variant can appear in more than one track; keep them distinct when filtering.

## Germline classifications (ACMG/AMP)

The five core terms (Richards et al. 2015):

| Term | Abbr | Meaning | Posterior |
|------|------|---------|-----------|
| Pathogenic | P | Causes disease | ~99% |
| Likely Pathogenic | LP | Likely causes disease | ~90% |
| Uncertain Significance | VUS | Insufficient evidence | N/A |
| Likely Benign | LB | Likely does not cause disease | ~90% non-pathogenic |
| Benign | B | Does not cause disease | ~99% non-pathogenic |

### Low-penetrance and risk-allele terms (ClinGen)

- **Pathogenic, low penetrance** / **Likely pathogenic, low penetrance** —
  disease-causing but not every carrier is affected.
- **Established risk allele** / **Likely risk allele** / **Uncertain risk
  allele** — association with increased risk at varying confidence.

### Other germline terms

`Drug response`, `Association`, `Protective`, `Affects`, `Other`,
`Not provided`.

### Zygosity rules

- **Recessive disorders**: a disease-causing allele is classified **Pathogenic**
  even though heterozygous carriers are unaffected — the term describes the
  allele's effect, not carrier status.
- **Compound heterozygotes**: each allele is classified independently. Two LP
  variants in *trans* can jointly cause recessive disease while each keeps its
  own classification.

## Somatic — clinical impact (AMP/ASCO/CAP tiers)

| Tier | Meaning |
|------|---------|
| Tier I — Strong | FDA-approved therapy or professional-guideline evidence |
| Tier II — Potential | Emerging clinical actionability |
| Tier III — Uncertain | Unknown clinical significance |
| Tier IV — Benign/Likely benign | No therapeutic implication |

## Somatic — oncogenicity (ClinGen/CGC/VICC)

`Oncogenic`, `Likely Oncogenic`, `Uncertain Significance`, `Likely Benign`,
`Benign` — parallel to the germline scale but about whether the variant *drives
cancer* rather than causes a Mendelian disease.

## Review status (star ratings)

The single most important quality signal. It measures evidence strength, not
correctness.

| Stars | Review status | Confidence |
|-------|---------------|------------|
| ★★★★ | Practice guideline | Highest — used in clinical guidelines |
| ★★★ | Reviewed by expert panel (e.g. ClinGen) | High |
| ★★ | Multiple submitters, no conflicts | Moderate consensus |
| ★ | Criteria provided, single submitter | Standard; depends on submitter |
| ☆ | No assertion criteria / no assertion provided | Lowest / none |

Practical rule: for any downstream decision prefer ★★★ or ★★★★. Treat ★ and ☆
as leads, not conclusions.

## Conflicting interpretations

As of June 2022, ClinVar flags a conflict when submitters disagree across these
boundaries:

- Pathogenic/LP **vs** Uncertain significance
- Pathogenic/LP **vs** Benign/LB
- Uncertain significance **vs** Benign/LB

The aggregate reads "Conflicting interpretations of pathogenicity" and every
individual submission is shown. Resolution order:

1. Star rating of each submission (higher wins).
2. Assertion criteria quality (ACMG-based > none).
3. Submission recency (newer may reflect new evidence).
4. Population frequency (gnomAD) and functional-study evidence.
5. Any expert-panel (★★★) or practice-guideline (★★★★) call.

Exclude conflicts in a query: `<gene>[gene] AND "clinsig pathogenic"[Properties] NOT "clinsig has conflicts"[Properties]`.

## Aggregate classification behavior

- **No conflict** — ClinVar displays one aggregate term; confidence rises with
  more concordant submitters.
- **Conflict** — displays the conflict label and defers resolution to you.

## Interpretation checklist

For research use:

1. Always read the review status; prefer ★★★/★★★★.
2. Open the submission detail and check the evidence/criteria.
3. Note the last-evaluated date; older calls may predate key data.
4. Confirm the assertion used ACMG-style criteria.
5. Consider ancestry, phenotype, and population frequency.
6. Investigate conflicts before concluding anything.

For annotation pipelines:

1. Prioritize higher review status.
2. Flag conflicts for manual review rather than auto-accepting.
3. Track classification changes across releases.
4. Carry gnomAD frequency alongside the ClinVar call.
5. Record the ClinVar release version and access date.

### Red flags

☆/★ ratings, unresolved conflicts, VUS treated as benign, stale submissions
with no update, and classifications resting on in-silico predictions alone.

## Reclassification

Variants move (in either direction) on new functional studies, added population
data, revised ACMG guidance, more affected patients, or family segregation.
VCV/RCV/SCV accessions are version-controlled and submission history is
retained, so a pinned release plus a recorded access date makes any result
reproducible.

## References

- ACMG/AMP guidelines: Richards et al. 2015 (PMID: 25741868)
- ClinGen SVI working group: https://clinicalgenome.org/
- ClinVar clinical significance docs: https://www.ncbi.nlm.nih.gov/clinvar/docs/clinsig/
- Review status docs: https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/
