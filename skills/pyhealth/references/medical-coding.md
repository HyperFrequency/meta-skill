# Medical Code Translation (`pyhealth.medcode`)

Clinical data mixes coding systems. `medcode` gives you two tools: `InnerMap`
for lookups and hierarchy navigation *within* one system, and `CrossMap` for
translation *across* systems. Use them to standardize codes, reduce
dimensionality (group rare codes into clinical categories), and reconcile
datasets that speak different vocabularies.

## InnerMap — within one system

```python
from pyhealth.medcode import InnerMap

icd9 = InnerMap.load("ICD9CM")
icd9.lookup("428.0")          # -> human-readable name / attributes
icd9.get_ancestors("428.0")   # parent codes up the hierarchy
icd9.get_descendants("428")   # child codes
```

`lookup` and the ancestor/descendant walks are the verified surface. Descendant
traversal and code standardization (normalizing `"4280"` -> `"428.0"`) exist but
naming can differ by version — confirm before scripting a batch job.

## CrossMap — across systems

```python
from pyhealth.medcode import CrossMap

# Diagnosis -> clinical category (dimensionality reduction)
icd9_to_ccs = CrossMap.load("ICD9CM", "CCSCM")
icd9_to_ccs.map("82101")            # -> CCS category code(s)

# Drug identifier -> therapeutic classification
ndc_to_atc = CrossMap.load("NDC", "ATC")
ndc_to_atc.map("00527051210")       # -> ATC code(s)
```

`CrossMap.load(src, dst)` then `.map(code)` returns a list because clinical
mappings are frequently one-to-many (one ICD-9 code -> several ICD-10 codes).
**Always handle the list**, and expect some codes to have no mapping.

## Supported Systems

- **Diagnoses**: `ICD9CM`, `ICD10CM`, `CCSCM` (Clinical Classifications Software —
  groups ICD codes into ~250 clinically meaningful categories).
- **Procedures**: `ICD9PROC`, `ICD10PROC`, `CCSPROC`.
- **Medications**: `NDC` (FDA product-level drug code), `RXNORM` (normalized drug
  terminology), `ATC` (WHO therapeutic classification).

## The ATC Hierarchy (drug grouping)

ATC encodes a drug at five nested levels — useful when you want a *drug class*
feature instead of a specific product:

| Level | Meaning | Width | `C03CA01` |
|---|---|---|---|
| 1 | Anatomical main group | 1 letter | `C` (cardiovascular) |
| 2 | Therapeutic subgroup | 2 digits | `C03` (diuretics) |
| 3 | Pharmacological subgroup | 1 letter | `C03C` (high-ceiling diuretics) |
| 4 | Chemical subgroup | 1 letter | `C03CA` (sulfonamides) |
| 5 | Chemical substance | 2 digits | `C03CA01` (furosemide) |

To coarsen a level-5 ATC code to a class, truncate the string
(`"C03CA01"[:3] == "C03"`) or climb with
`InnerMap.load("ATC").get_ancestors(code)`. Some PyHealth versions add a level
argument to the NDC->ATC mapping; if you use it, verify the exact keyword against
your installed version rather than assuming it.

## Integrating with a Dataset

```python
from pyhealth.medcode import CrossMap

icd_to_ccs = CrossMap.load("ICD10CM", "CCSCM")
for patient in dataset.iter_patients():
    for visit in patient.visits:
        for event in visit.events:
            if event.vocabulary == "ICD10CM":
                ccs = icd_to_ccs.map(event.code)   # list; may be empty
```

Grouping to CCS (diagnoses) or ATC level 2-3 (drugs) before modeling shrinks the
vocabulary, tames rare-code sparsity, and stabilizes embeddings.

## Practical Rules

1. **Standardize before mapping** — inconsistent formats (`4280` vs `428.0`)
   silently miss.
2. **Handle one-to-many and empty results** — never index `[0]` blindly.
3. **Record code provenance** — ICD-9 vs ICD-10 era matters when you pool
   multi-year or multi-site data.
4. **Group to reduce dimensionality** — CCS / ATC classes beat raw codes for
   small cohorts.
