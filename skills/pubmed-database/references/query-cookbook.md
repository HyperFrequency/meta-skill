# PubMed Query Cookbook

Copy-paste query templates for common research scenarios. Replace bracketed placeholders and
run through ESearch (see `references/api-reference.md`). Tag and field conventions are in
`references/search-syntax.md`.

## General patterns

```
# Recent research on a topic
breast cancer[tiab] AND 2023:2024[dp]

# Systematic reviews on a topic
(diabetes[tiab] OR diabetes mellitus[mh]) AND systematic review[pt]

# Meta-analyses
hypertension[tiab] AND meta-analysis[pt] AND 2020:2024[dp]

# Clinical trials
alzheimer disease[mh] AND randomized controlled trial[pt]

# Guidelines
asthma[tiab] AND (guideline[pt] OR practice guideline[pt])
```

## Disease-specific

```
# Cancer — type + treatment
lung cancer[tiab] AND immunotherapy[tiab] AND clinical trial[pt]
# Cancer genetics
breast neoplasms[mh] AND BRCA1[tiab] AND genetic testing[tiab]

# Cardiovascular — stroke intervention
stroke[mh] AND (thrombectomy[tiab] OR thrombolysis[tiab]) AND randomized controlled trial[pt]
# Hypertension management
hypertension[mh]/drug therapy AND comparative effectiveness[tiab]

# Infectious disease — COVID vaccines
COVID-19[tiab] AND (vaccine[tiab] OR vaccination[tiab]) AND 2023:2024[dp]
# Antibiotic resistance
(antibiotic resistance[tiab] OR drug resistance, bacterial[mh]) AND systematic review[pt]

# Neurology — Alzheimer biomarkers
alzheimer disease[mh] AND (diagnosis[sh] OR biomarkers[tiab]) AND 2020:2024[dp]

# Diabetes — new drug classes
diabetes mellitus, type 2[mh] AND (GLP-1[tiab] OR SGLT2[tiab]) AND 2022:2024[dp]
```

## Drug and treatment research

```
# Compare two drugs
(drug A[nm] OR drug B[nm]) AND condition[mh] AND comparative effectiveness[tiab]
# Drug side effects
medication name[nm] AND (adverse effects[sh] OR side effects[tiab])
# Combination therapy
(aspirin[nm] AND clopidogrel[nm]) AND acute coronary syndrome[mh]
# Surgery vs medication
condition[mh] AND (surgery[tiab] OR surgical[tiab]) AND (medication[tiab] OR drug therapy[sh]) AND comparative study[pt]
```

## Diagnostic research

```
# Sensitivity / specificity
test name[tiab] AND condition[tiab] AND (sensitivity[tiab] AND specificity[tiab])
# Diagnostic imaging
(MRI[tiab] OR magnetic resonance imaging[tiab]) AND brain tumor[tiab] AND diagnosis[sh]
# Screening programs
cancer type[tiab] AND screening[tiab] AND (cost effectiveness[tiab] OR benefit[tiab])
```

## Population-specific

```
# Pediatric
condition[tiab] AND (child[mh] OR pediatric[tiab]) AND treatment[tiab]
drug name[nm] AND pediatric[tiab] AND (dosing[tiab] OR dose[tiab])
# Geriatric
condition[tiab] AND (aged[mh] OR elderly[tiab] OR geriatric[tiab])
polypharmacy[tiab] AND elderly[tiab] AND adverse effects[tiab]
# Pregnancy
drug name[nm] AND (pregnancy[mh] OR pregnant women[tiab]) AND safety[tiab]
# Sex differences
condition[tiab] AND (sex factors[mh] OR gender differences[tiab])
```

## Epidemiology and public health

```
disease[tiab] AND (prevalence[tiab] OR epidemiology[sh]) AND country/region[tiab]
disease[mh] AND (risk factors[mh] OR etiology[sh]) AND cohort study[tiab]
condition[tiab] AND (health disparities[tiab] OR health equity[tiab]) AND minority groups[tiab]
```

## Methodology-specific

```
# Cohort / case-control / cross-sectional
condition[tiab] AND cohort study[tiab] AND prospective[tiab]
disease[tiab] AND case-control studies[mh] AND risk factors[tiab]
condition[tiab] AND cross-sectional studies[mh] AND prevalence[tiab]

# ML / AI in medicine
(machine learning[tiab] OR artificial intelligence[tiab]) AND diagnosis[tiab] AND validation[tiab]

# Genetics / molecular
disease[tiab] AND (genome-wide association study[tiab] OR GWAS[tiab])
CRISPR[tiab] AND (gene editing[tiab] OR genome editing[tiab]) AND 2020:2024[dp]
```

## Author, institution, journal, identifier

```
# Author work in a window
smith ja[au] AND cancer[tiab] AND 2023:2024[dp] AND english[la]
# Institution
harvard[affil] AND cancer research[tiab] AND 2023:2024[dp]
"mayo clinic"[affil] AND clinical trial[pt]
# Journal
(nature[ta] OR science[ta] OR cell[ta]) AND immunology[tiab]
0028-4793[issn] AND clinical trial[pt]
# Identifiers
12345678[pmid]
10.1056/NEJMoa123456[doi]
```

## PICO framework

Decompose a clinical question into Population / Intervention / Comparison / Outcome, turn each
into a `(synonym[tiab] OR MeSH[mh])` block, and join with `AND`:

```
P: diabetes mellitus, type 2[mh]
I: metformin[nm]
C: lifestyle modification[tiab]
O: glycemic control[tiab]

diabetes mellitus, type 2[mh]
  AND (metformin[nm] OR lifestyle modification[tiab])
  AND glycemic control[tiab]
  AND randomized controlled trial[pt]
```

## Comprehensive systematic-review template

```
(disease name[tiab] OR disease name[mh]) AND
((treatment[tiab] OR therapy[tiab] OR management[tiab]) OR
 (diagnosis[tiab]  OR screening[tiab]) OR
 (epidemiology[tiab] OR prevalence[tiab])) AND
(systematic review[pt] OR meta-analysis[pt] OR review[pt]) AND
2019:2024[dp] AND english[la]
```

## Quality and access filters

```
# High-quality evidence only
condition[tiab] AND (randomized controlled trial[pt] OR systematic review[pt] OR meta-analysis[pt])
  AND humans[mh] AND english[la] AND 2020:2024[dp]
# Free full text
topic[tiab] AND free full text[sb] AND 2023:2024[dp]
# Must have an abstract
condition[tiab] AND hasabstract[text] AND review[pt]
```

## Iterative refinement

```
1. diabetes                                                   → too broad
2. diabetes mellitus type 2                                   → better
3. diabetes mellitus, type 2[mh] AND metformin[nm]            → more specific
4. + AND randomized controlled trial[pt] AND 2020:2024[dp]    → focused
```

Record the final string, database, and run date so the search is reproducible. Hand DOIs/PMIDs
to `citation-management` for reference formatting.
