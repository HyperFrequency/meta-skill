# Adverse-Event Grading (CTCAE) and Dose-Limiting Toxicity

Grade a laboratory or clinical parameter against the CTCAE severity scale and
flag dose-limiting toxicities (DLTs).

## What CTCAE is

The **Common Terminology Criteria for Adverse Events (CTCAE v5.0)** maps each
adverse-event term to a severity grade 0–5 (0 none, 1 mild, 2 moderate, 3 severe,
4 life-threatening, 5 death). Veterinary oncology uses the analogous
**VCOG-CTCAE** scale.

## Grading lab values

Encode the threshold for each parameter as an ordered set of predicates and
return the highest matching grade. **These thresholds are an illustrative
subset** — the authoritative CTCAE table governs, and the upper limit of normal
(ULN) / lower limit of normal (LLN) are lab-specific, so parameterize them rather
than hard-coding.

```python
# Illustrative CTCAE v5.0 subset — confirm against the official criteria.
# ANC/platelets in cells/mm^3; hemoglobin in g/dL; ALT relative to ULN.
CTCAE = {
    "neutrophil_count": {1: lambda x: 1500 <= x < 2000,   # (LLN..1500 per CTCAE)
                         2: lambda x: 1000 <= x < 1500,
                         3: lambda x:  500 <= x < 1000,
                         4: lambda x:         x <  500},
    "platelet_count":   {1: lambda x: 75000 <= x < 150000,
                         2: lambda x: 50000 <= x <  75000,
                         3: lambda x: 25000 <= x <  50000,
                         4: lambda x:          x <  25000},
    "hemoglobin":       {1: lambda x: 10 <= x < 12,
                         2: lambda x:  8 <= x < 10,
                         3: lambda x:       x <  8,
                         4: lambda x: False},              # life-threatening: clinical
    "ALT_x_ULN":        {1: lambda r: 1 <= r < 3,          # r = measured / ULN
                         2: lambda r: 3 <= r < 5,
                         3: lambda r: 5 <= r < 20,
                         4: lambda r:      r >= 20},
}

def grade(parameter, value):
    if parameter not in CTCAE:
        return {"parameter": parameter, "value": value, "grade": None,
                "error": "unknown parameter"}
    for g in (4, 3, 2, 1):                 # highest grade first
        if CTCAE[parameter][g](value):
            return {"parameter": parameter, "value": value, "grade": g}
    return {"parameter": parameter, "value": value, "grade": 0}
```

Pass ALT as a **ratio to that lab's ULN**, not the raw IU/L, so the same
predicates apply across labs. Add parameters as needed from the official table;
keep the predicates mutually exclusive and ordered.

## Dose-limiting toxicity

A DLT is an adverse event, attributable to the drug and occurring in the defined
observation window (e.g. cycle 1), that meets a protocol-specified severity —
conventionally **Grade ≥ 3 non-hematologic** or **Grade ≥ 4 hematologic**, with
protocol-specific exceptions (e.g. brief manageable nausea).

```python
def flag_dlts(graded_events, hematologic_params, threshold_heme=4, threshold_nonheme=3):
    """graded_events: list of dicts from grade(); hematologic_params: set of names."""
    dlts = []
    for ae in graded_events:
        g = ae.get("grade")
        if g is None:
            continue
        is_heme = ae["parameter"] in hematologic_params
        cutoff = threshold_heme if is_heme else threshold_nonheme
        if g >= cutoff:
            dlts.append(ae)
    return dlts
```

## Boundaries and cautions

- **Grading ≠ attribution.** CTCAE assigns severity only; whether an event is
  drug-related (and thus DLT-eligible) is a separate clinical judgment.
- The bundled thresholds are a starting point, not a validated CTCAE
  implementation — always reconcile against the current official criteria and
  the protocol's DLT definition, which frequently deviates from the generic
  Grade 3/4 rule.
- This is per-observation grading, not a trial-level safety analysis
  (incidence tables, exposure-adjusted rates, causality) — take that to
  `statistical-analysis` / `statsmodels`, and clinical decision rules to
  `clinical-decision-support`.
- For any regulated or patient-facing use, a qualified clinician must review the
  grading; treat this as decision support, never as an autonomous determination.
