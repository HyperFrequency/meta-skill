# Diagnostic Reports (Radiology, Pathology, Laboratory)

Diagnostic reports communicate findings that drive clinical decisions. They must
be clear, systematic, and actionable, and they must answer the clinical question
that prompted the study.

---

## Radiology reports

Standard section order:

1. **Patient demographics** — identifier (name or research ID), age/DOB, MRN,
   exam date/time.
2. **Clinical indication** — the reason for the study and the specific question.
   Example: "Rule out pulmonary embolism in a patient with acute dyspnea."
3. **Technique** — modality (X-ray, CT, MRI, US, PET), region, contrast (agent,
   route, volume), protocol/sequence, and any quality limitation. Example:
   "Contrast-enhanced CT chest/abdomen/pelvis with 100 mL IV iodinated contrast;
   no oral contrast."
4. **Comparison** — prior studies and their dates; state stability or change.
5. **Findings** — systematic, organ-by-organ. Report positive findings first,
   then pertinent negatives. Measure lesions. Use standardized terminology
   (ACR lexicon, RadLex).
6. **Impression / conclusion** — concise numbered summary that answers the
   clinical question, gives a differential where appropriate, states the level
   of diagnostic certainty, and recommends follow-up.

Example impression:

```
1. Bilateral ground-glass opacities, lower-lobe predominant, consistent with
   viral/atypical pneumonia; COVID-19 cannot be excluded. Clinical correlation
   advised.
2. No pulmonary embolism.
3. Recommend follow-up imaging in 4-6 weeks to confirm resolution.
```

### Structured reporting systems (use where they apply)

| System | Domain |
| --- | --- |
| **BI-RADS** | Breast imaging |
| **Lung-RADS** | Lung-cancer screening CT |
| **LI-RADS** | Liver observations (at-risk patients) |
| **PI-RADS** | Prostate MRI |
| **C-RADS** | CT colonography |
| **TI-RADS** | Thyroid nodules |

Each assigns a category that maps to a management recommendation; using the
right one improves consistency and enables downstream data extraction. Report
the category and its recommended action explicitly.

---

## Pathology reports

Surgical-pathology section order:

1. **Patient information** — identifiers, age/sex, ordering physician, received
   date.
2. **Specimen** — type (biopsy/excision/resection), site, laterality, number of
   parts. Example: "Skin, left forearm, excisional biopsy."
3. **Clinical history** — indication and relevant priors.
4. **Gross description** — macroscopic appearance: size, weight, color,
   orientation, sectioning/sampling (cassette labels).
5. **Microscopic description** — histology, cellular and architectural features,
   margins, special stains / immunohistochemistry.
6. **Diagnosis** — primary diagnosis with grade/stage, margin status, and node
   status where applicable.
7. **Comment** — differential, recommended ancillary studies, correlation notes.

### CAP synoptic reporting (cancer specimens)

The College of American Pathologists (CAP) publishes cancer protocols with
required synoptic data elements. Report them as discrete labeled fields so they
are unambiguous and machine-readable. Core elements:

- Tumor site and size
- Histologic type and grade
- Extent/depth of invasion
- Lymph-vascular and perineural invasion
- Margin status (and distance to closest margin)
- Lymph nodes: number examined / number positive
- **Pathologic stage** using the AJCC **TNM** classification (pT, pN, pM)
- Ancillary/molecular markers (e.g., biomarker status)

Example (melanoma):

```
MALIGNANT MELANOMA, superficial spreading type
Breslow thickness: 1.2 mm
Clark level: IV
Mitotic rate: 3/mm^2
Ulceration: absent
Margins: negative (closest 0.4 cm)
Lymphovascular invasion: not identified
```

---

## Laboratory reports

Components:

1. **Patient and specimen** — identifiers, specimen type (blood/serum/urine/CSF),
   collection and received date/time, ordering provider.
2. **Test and method** — full test name, methodology (immunoassay, PCR,
   spectrophotometry), accession number.
3. **Results** — value + units + **reference range** + abnormal flag (H/L).
   Example:

   ```
   Hemoglobin           8.5 g/dL   (L)  [ref 12.0-16.0]
   WBC                  15.2 x10^3/uL (H) [ref 4.5-11.0]
   ```

4. **Interpretation** (when applicable) — clinical significance, therapeutic
   ranges for drug levels, suggested follow-up.
5. **Quality control** — specimen adequacy and issues (hemolyzed, lipemic,
   clotted), processing delays, technical limitations.

### Critical values

Life-threatening results require **immediate** notification to a responsible
clinician, and the notification (recipient + time) must be documented. Typical
examples (institution-specific thresholds vary):

- Glucose < 40 or > 500 mg/dL
- Potassium < 2.5 or > 6.5 mEq/L
- Platelets < 20 x10^3/uL
- Positive blood culture / critical INR

CLIA governs US laboratory quality; report units and reference ranges exactly as
the performing lab defines them — do not import ranges from another lab.
