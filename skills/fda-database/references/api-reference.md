# openFDA API Reference

Complete reference for the openFDA REST API: base URL, authentication, rate limits, query
syntax, response/error formats, and the endpoint catalogue with searchable key fields.

Official docs: <https://open.fda.gov/apis/> · Field explorers:
`https://open.fda.gov/apis/{category}/{endpoint}/searchable-fields/`

## Base URL and transport

```
https://api.fda.gov/{category}/{endpoint}.json
```

- **HTTPS only** — HTTP requests are rejected.
- `category` ∈ `drug`, `device`, `food`, `animalandveterinary`, `other`.
- Example URLs: `https://api.fda.gov/drug/event.json`,
  `https://api.fda.gov/device/510k.json`, `https://api.fda.gov/food/enforcement.json`.

## Authentication

An API key is optional but recommended. Register (free) at
<https://open.fda.gov/apis/authentication/>. Pass it as the `api_key` query parameter:

```python
params = {"api_key": "YOUR_KEY", "search": "...", "limit": 10}
requests.get("https://api.fda.gov/drug/event.json", params=params)
```

Store the key in an environment variable (e.g. `FDA_API_KEY`); never hard-code it.

## Rate limits

| Mode | Per minute | Per day |
| --- | --- | --- |
| No key | 240 / IP | 1,000 / IP |
| With key | 240 / key | 120,000 / key |

Exceeding the limit returns HTTP `429`. Handle it with exponential backoff (wait ~60 s and
retry). Response headers may include `X-RateLimit-Limit` and `X-RateLimit-Remaining`.

## Query parameters

| Param | Purpose | Notes |
| --- | --- | --- |
| `search` | Filter records | Lucene-style; see operators below |
| `limit` | Records per response | **Default 1**, max 1000 |
| `skip` | Offset for pagination | Max 25,000 (skip + limit ≤ 26,000) |
| `count` | Aggregate by a field | Returns `{term, count}` rows, not records |
| `sort` | Order records | `field:asc` or `field:desc` |

`search`, `count`, and `sort` are mutually usable, but `count` replaces the record list
with aggregation buckets.

## Search operators

| Operator | Syntax | Example |
| --- | --- | --- |
| Field match | `field:value` | `patient.drug.medicinalproduct:aspirin` |
| AND | `+AND+` | `...aspirin+AND+occurcountry:ca` |
| OR (explicit) | `+OR+` | `...:aspirin+OR+...:ibuprofen` |
| OR (grouped) | `field:(a b)` | `medicinalproduct:(aspirin ibuprofen)` |
| NOT | `+NOT+` | `_exists_:occurcountry+AND+NOT+occurcountry:us` |
| Wildcard | `*` | `medicinalproduct:met*`, `*cillin*` |
| Exact phrase | quotes | `reactionmeddrapt:"heart attack"` |
| Range | `[lo+TO+hi]` | `receivedate:[20200101+TO+20201231]` |
| Open range | `[lo+TO+*]` | `patient.patientonsetage:[65+TO+*]` |
| Exists | `_exists_:field` | `_exists_:patient.patientonsetage` |
| Missing | `_missing_:field` | `_missing_:patient.patientonsetage` |

Dates use `YYYYMMDD`. Escape embedded quotes in values. Avoid a bare `search=*` and
leading wildcards (`*term`) — both are slow and may time out.

### Counting with `.exact`

`count` on a free-text field tokenizes into individual words unless you append `.exact`:

```python
# Counts whole reaction phrases (correct):
{"search": "patient.drug.medicinalproduct:aspirin",
 "count": "patient.reaction.reactionmeddrapt.exact"}
```

Without `.exact` you would count "heart" and "attack" separately. Always use `.exact` when
aggregating reaction terms, device names, recall reasons, or any multi-word field.

## Response format

```json
{
  "meta": {
    "disclaimer": "...", "terms": "...", "license": "...",
    "last_updated": "2024-01-15",
    "results": { "skip": 0, "limit": 10, "total": 15234 }
  },
  "results": [ { /* record */ } ]
}
```

- `meta.results.total` — total matches (approximate for very large sets).
- A `count` query returns `results` as `[{"term": "...", "count": N}, ...]`.

### Error format and codes

```json
{ "error": { "code": "INVALID_QUERY", "message": "..." } }
```

| HTTP | Code | Meaning |
| --- | --- | --- |
| 404 | `NOT_FOUND` | No records matched (openFDA returns 404, not `[]`, for zero hits) |
| 400 | `INVALID_QUERY` | Malformed `search` / bad field name |
| 429 | — | Rate limit exceeded |
| 401 | — | Invalid API key |
| 500 | — | Server error |

Treat 404 as "no results," not a hard failure.

## Recall classification (drug / device / food `enforcement`)

- **Class I** — reasonable probability of serious injury or death (e.g. undeclared severe
  allergen, botulism, Listeria).
- **Class II** — temporary or reversible harm, low probability of serious harm.
- **Class III** — unlikely to cause harm but violates FDA labeling/manufacturing rules.

`status` cycles `Ongoing` → `Completed` / `Terminated`. Common `enforcement` fields:
`recall_number`, `classification`, `status`, `product_description`, `reason_for_recall`,
`recalling_firm`, `distribution_pattern`, `code_info`, `recall_initiation_date`,
`report_date`, `voluntary_mandated`.

---

# Endpoint catalogue

## drug (6 endpoints)

### `drug/event` — Adverse events (source: FAERS)
Side effects, medication errors, therapeutic failures.
Key fields: `patient.drug.medicinalproduct`, `patient.drug.drugindication`,
`patient.reaction.reactionmeddrapt`, `patient.patientonsetage`, `receivedate`,
`serious` (1=serious, 2=not), `seriousnessdeath`, `occurcountry`,
`primarysource.qualification`, `patient.drug.openfda.brand_name` / `generic_name`.

### `drug/label` — Product labeling (source: SPL)
Structured prescribing information.
Key fields: `openfda.brand_name`, `openfda.generic_name`, `openfda.unii`,
`indications_and_usage`, `warnings`, `boxed_warning`, `adverse_reactions`,
`dosage_and_administration`, `contraindications`, `drug_interactions`,
`active_ingredient`, `inactive_ingredient`, `description`, `pharmacodynamics`.
(Text sections are arrays — index `[0]` and use `.get()` with defaults.)

### `drug/ndc` — National Drug Code Directory
Key fields: `product_ndc`, `generic_name`, `brand_name`, `labeler_name`, `dosage_form`,
`route`, `product_type`, `marketing_category`, `application_number`,
`active_ingredients` (name + strength), `packaging`, `listing_expiration_date`.

### `drug/enforcement` — Drug recalls
See recall fields above (`classification`, `reason_for_recall`, `product_description`, …).

### `drug/drugsfda` — Drugs@FDA (approvals since 1939)
Key fields: `application_number`, `sponsor_name`, `openfda.brand_name`/`generic_name`,
`products` (with `active_ingredients`, `dosage_form`, `route`, `marketing_status`),
`submissions` (`submission_type`, `submission_status`, `submission_status_date`,
`review_priority`).

### `drug/drugshortages` — Current & resolved shortages
Key fields: `product_name`, `status` (`Currently in Shortage`, `Resolved`,
`Discontinued`), `reason`, `shortage_start_date`, `resolution_date`, `active_ingredient`,
`marketed_by`, `presentation`.

## device (9 endpoints)

Devices carry a risk class: **Class I** (low, e.g. bandages), **Class II** (moderate,
e.g. infusion pumps), **Class III** (high, e.g. implantable pacemakers).

### `device/event` — Adverse events (source: MAUDE)
Key fields: `device.brand_name`, `device.generic_name`, `device.manufacturer_d_name`,
`device.device_class`, `event_type` (Death/Injury/Malfunction/Other), `date_received`,
`mdr_report_key`, `product_problem_flag`, `patient.patient_problems`, `remedial_action`,
`device.openfda.device_name`, `device.openfda.medical_specialty_description`.

### `device/510k` — Premarket notifications (substantial equivalence)
Key fields: `k_number`, `applicant`, `device_name`, `device_class`, `decision_date`,
`decision_description` (SE / Not SE), `product_code`, `clearance_type`,
`expedited_review_flag`, `advisory_committee`, `openfda.regulation_number`.

### `device/classification` — Device classification database
Key fields: `product_code` (3-letter), `device_name`, `device_class`,
`medical_specialty` / `medical_specialty_description`, `regulation_number`,
`review_panel`, `definition`, `implant_flag`, `life_sustain_support_flag`,
`gmp_exempt_flag`.

### `device/enforcement` — Device recalls (enforcement reports)
See recall fields above, plus `product_res_number`.

### `device/recall` — Recall detail
Key fields: `res_event_number`, `product_code`, `product_res_number`, `firm_fei_number`,
`k_numbers`, `pma_numbers`, `root_cause_description`, `openfda.device_name`/`device_class`.

### `device/pma` — Premarket approval (Class III)
Key fields: `pma_number` (e.g. `P850005`), `supplement_number`, `applicant`,
`trade_name`, `generic_name`, `product_code`, `decision_date`, `decision_code`
(`APPR`=approved), `advisory_committee`, `openfda.regulation_number`.

### `device/registrationlisting` — Establishment registrations & listings
Key fields: `registration.fei_number`, `registration.name`,
`registration.registration_number`, `registration.iso_country_code`,
`registration.state_code`, `registration.reg_expiry_date_year`, `products.product_code`,
`products.openfda.device_name`/`device_class`, `proprietary_name`, `establishment_type`.

### `device/udi` — Global UDI Database (GUDID)
Key fields: `identifiers.id` (DI), `identifiers.issuing_agency` (GS1/HIBCC/ICCBBA),
`brand_name`, `version_model_number`, `catalog_number`, `company_name`, `is_rx`, `is_otc`,
`is_combination_product`, `is_kit`, `has_lot_or_batch_number`, `has_serial_number`,
`has_expiration_date`, `mri_safety`, `gmdn_terms`, `product_codes`, `storage`.

### `device/covid19serology` — COVID-19 antibody-test evaluations
Key fields: `manufacturer`, `device`, `authorization_status`, `control_panel`,
`sample_sensitivity_report_one`/`_two`, `sample_specificity_report_one`/`_two`.

## food (2 endpoints)

### `food/event` — Adverse events (source: CAERS; food, supplements, cosmetics)
Key fields: `date_started`, `date_created`, `report_number`, `outcomes`
(Hospitalization / Death / Disability / …), `reactions`, `consumer.age`,
`consumer.age_unit`, `consumer.gender`, `products.name_brand`, `products.industry_name`,
`products.industry_code`, `products.role` (Suspect / Concomitant).

### `food/enforcement` — Food recalls
See recall fields, plus `city`, `state`, `country`, `initial_firm_notification`. The FDA
requires declaration of **9 major allergens**: milk, eggs, fish, crustacean shellfish,
tree nuts, peanuts, wheat, soybeans, sesame — the dominant cause of Class I food recalls.

## animalandveterinary (1 endpoint)

### `animalandveterinary/event` — Animal-drug adverse events (source: FDA CVM)
Reactions are coded with **VeDDRA** (Veterinary Dictionary for Drug Related Affairs).
Key fields: `unique_aer_id_number`, `primary_reporter`, `onset_date`, `animal.species`,
`animal.gender`, `animal.age.min`/`max`/`unit`, `animal.breed.breed_component`,
`animal.breed.is_crossbred`, `animal.weight.*`, `drug.brand_name`,
`drug.active_ingredients.name`, `drug.route`, `drug.dosage_form`, `drug.atc_vet_code`,
`reaction.veddra_term_name`, `reaction.veddra_term_code`, `reaction.veddra_version`,
`reaction.number_of_animals_affected`, `outcome.medical_status`, `serious_ae`.
Note: `serious_ae` compares as the string `"true"`, and `outcome`/`reaction` are arrays.

## other (2 endpoints)

### `other/substance` — Substance registry (source: GSRS)
Molecular-level substance data.
Key fields: `uuid`, `approvalID` (the **UNII**, 10-char alphanumeric, e.g. `R16CO5Y76E`),
`substanceClass` (chemical / protein / nucleic acid / polymer / structurally diverse /
mixture / concept), `names.name`/`names.preferred`, `codes.code`/`codes.codeSystem`
(CAS, ECHA, …), `relationships.type` (ACTIVE MOIETY / METABOLITE / IMPURITY),
`structure.smiles`, `structure.inchi`, `structure.inchiKey`, `structure.formula`,
`structure.molecularWeight`, `protein.subunits`, `nucleicAcid.subunits`,
`mixture.components`.
UNIIs are stable and form-specific (a salt and its free acid get different UNIIs). Search
by UNII with `approvalID:R16CO5Y76E`, by name with `names.name:acetaminophen`, by CAS with
`codes.code:50-78-2`, or by formula with `structure.formula:C8H9NO2`.

### `other/nsde` — NSDE (legacy historical substance/NDC data)
Key fields: `proprietary_name`, `nonproprietary_name`, `substance_name`, `dosage_form`,
`route`, `company_name`, `active_numerator_strength`, `active_ingred_unit`,
`pharm_classes`, `dea_schedule`. Prefer `other/substance` for current data.

## External resources

- openFDA home: <https://open.fda.gov/> · Try-the-API explorer:
  <https://open.fda.gov/apis/try-the-api/>
- Bulk downloads (for whole-dataset analytics): <https://open.fda.gov/apis/downloads/>
- UNII search: <https://precision.fda.gov/uniisearch> · GSRS:
  <https://fdasis.nlm.nih.gov/srs/>
- GUDID: <https://accessgudid.nlm.nih.gov/>
- Support: `open-fda@fda.hhs.gov` · <https://github.com/FDA/openfda>
