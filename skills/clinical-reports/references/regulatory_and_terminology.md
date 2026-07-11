# Regulatory Compliance, De-identification, and Terminology

Cross-cutting rules that apply to every clinical document: privacy law,
trial-conduct regulation, standardized nomenclature, and safe abbreviations.

> These are documentation guardrails, not legal advice. Institutional privacy,
> IRB/IEC, and regulatory teams own the authoritative determinations.

---

## HIPAA and de-identification

HIPAA protects Protected Health Information (PHI). Core obligations: minimum
necessary disclosure, patient authorization for use beyond
treatment/payment/operations, secure storage and transmission, audit trails, and
breach notification. Sharing PHI with a third-party service requires a Business
Associate Agreement (BAA).

Two ways to render data de-identified:

### Safe Harbor — remove/alter all 18 identifiers

1. Names
2. Geographic subdivisions smaller than a state (street, city, ZIP; ZIP3
   allowed only under population rules)
3. All date elements except year (and any age > 89)
4. Telephone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health-plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers and serial numbers (incl. license plates)
13. Device identifiers and serial numbers
14. Web URLs
15. IP addresses
16. Biometric identifiers (finger/voice prints, retinal scans)
17. Full-face photographs and comparable images
18. Any other unique identifying number, characteristic, or code

Ages over 89 must be aggregated to **"90 or older"**.

### Expert Determination

A qualified statistician certifies, using accepted methods, that the
re-identification risk is very small, and documents the methods and result. Use
this when Safe Harbor would strip clinically essential detail.

### Heuristic scan (aid, not guarantee)

A regex pass catches the most common leaks quickly; always finish with manual
review. Useful patterns:

```
Names        \b(Dr\.|Mr\.|Mrs\.|Ms\.)\s+[A-Z][a-z]+
             \b[A-Z][a-z]+,\s+[A-Z][a-z]+\b        # Last, First
SSN          \b\d{3}-\d{2}-\d{4}\b
Dates        \b(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}\b
Phone        \b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b
Email        \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b
MRN          (?i)(mrn|medical\s+record\s+(number|#))[:]\s*\d+
URL          https?://\S+
IP           \b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b
Image file   \.(jpg|jpeg|png|gif)\b
Age > 89     \b(\d{2,3})\s*(?:year|yr)s?[\s-]?old\b   # flag matches > 89
```

Grade findings by severity (SSN/biometrics = critical; names/dates/MRN/IP =
high; account/device = medium), then remediate and re-scan.

---

## FDA regulations (US clinical trials)

- **21 CFR Part 11** — electronic records and electronic signatures.
- **21 CFR Part 50** — protection of human subjects / informed consent.
- **21 CFR Part 56** — IRB standards.
- **21 CFR Part 312** — IND regulations (safety reporting at 312.32; see
  `clinical_trials.md`).

## ICH-GCP (E6)

Good Clinical Practice governs trial conduct: protocol adherence, documented
informed consent, source-document requirements (ALCOA — attributable, legible,
contemporaneous, original, accurate), audit trails/data integrity, and defined
investigator responsibilities.

---

## Standardized nomenclature

| System | Use |
| --- | --- |
| **SNOMED CT** | Comprehensive clinical terminology for EHRs; semantic interoperability |
| **LOINC** | Laboratory and clinical observation identifiers; data exchange |
| **ICD-10-CM** | Diagnosis coding for billing and epidemiology |
| **CPT** | Procedure coding for billing (maintained by the AMA) |
| **RxNorm** | Normalized drug names |
| **AJCC TNM** | Cancer staging (see `diagnostic_reports.md`) |

Coding to the correct system supports reimbursement, interoperability, and
downstream analytics — but code the documented facts, never upcode.

---

## Abbreviations — Joint Commission "Do Not Use" list

These are error-prone; spell them out:

| Do not write | Write instead |
| --- | --- |
| U | "unit" |
| IU | "international unit" |
| QD, QOD | "daily", "every other day" |
| Trailing zero (X.0 mg) | X mg (no trailing zero) |
| Missing leading zero (.X mg) | 0.X mg (always a leading zero) |
| MS, MSO4, MgSO4 | "morphine sulfate" / "magnesium sulfate" |

Use standard abbreviations elsewhere for efficiency, but never at the cost of
clarity.

---

## Documentation quality principles

- **Complete** — every required element present for the document type.
- **Accurate** — verified data and sound clinical reasoning.
- **Timely** — contemporaneous; regulatory/critical-value deadlines met.
- **Clear** — unambiguous language, logical structure, correct terminology.
- **Compliant** — privacy protected, institutional and regulatory rules followed,
  signed and dated.
