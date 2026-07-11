# ISO 13485:2016 Mandatory Documents and Records

ISO 13485:2016 requires a Quality Manual, a set of **documented procedures**, one or more
**Medical Device Files**, and the **records** that evidence conformity. The familiar
figure of "31 documented procedures" is a convention — several requirements are
conditional, so the literal list runs to ~33. Read it as *coverage*, not a file count:

- Procedures may be **combined** (CAPA = 8.5.2 + 8.5.3; document + record control =
  4.2.4 + 4.2.5; identification + traceability = 7.5.8 + 7.5.9) or **split**.
- Conditional procedures ("when applicable") may be excluded **with justification** in
  the Quality Manual.
- Regulation (FDA QMSR, EU MDR/IVDR, Health Canada) may require more than ISO 13485.

---

## Foundational documents

| Document | Clause | Must contain (summary) |
|----------|--------|------------------------|
| Quality Manual | 4.2.2 | QMS scope + justified exclusions; procedures/references; process interactions; documentation structure |
| Medical Device File | 4.2.3 | Per device type/family — see full contents below |
| Quality Policy | 5.3 | Commitment to requirements + effectiveness; frames objectives; signed by top management |
| Quality Objectives | 5.4.1 | Measurable, consistent with policy, at relevant functions |

### Medical Device File — required contents (4.2.3)
1. General description and intended use/purpose.
2. Label and instructions-for-use (IFU) specifications.
3. Product specifications.
4. Manufacturing specifications.
5. Procedures for purchasing, manufacturing, and servicing.
6. Procedures for measuring and monitoring.
7. Installation requirements (if applicable).
8. Risk management file(s).
9. Verification and validation information.
10. Design and development file(s) (when applicable).

Under FDA QMSR (effective 2 Feb 2026), the MDF replaces the separate DHF, DMR, and DHR.

---

## Documentation matrix — procedures and records

"Cond." = required only when applicable to the organization/product; exclusion must be
justified in the Quality Manual.

| Clause | Procedure | Mandatory | Records |
|--------|-----------|-----------|---------|
| 4.1.5 | Risk Management (ISO 14971 interface) | Yes | Yes |
| 4.1.6 | Software Validation (QMS software) | Yes | Yes |
| 4.2.4 | Control of Documents | Yes | — |
| 4.2.5 | Control of Records | Yes | — |
| 5.5.3 | Internal Communication | Yes | — |
| 5.6.1 | Management Review | Yes | Yes |
| 6.2 | Competence / Training | Yes | Yes |
| 6.3 | Infrastructure Maintenance | Cond. | Yes |
| 6.4.2 | Contamination Control | Cond. | Yes |
| 7.2.3 | Customer Communication | Yes | Yes |
| 7.3.1-10 | Design and Development | Cond. | Yes |
| 7.4.1 | Purchasing | Yes | Yes |
| 7.4.3 | Verification of Purchased Product | Yes | Yes |
| 7.5.1 | Production & Service Provision | Yes | Yes |
| 7.5.2 | Product Cleanliness | Cond. | Yes |
| 7.5.3 | Installation | Cond. | Yes |
| 7.5.4 | Servicing | Cond. | Yes |
| 7.5.6 | Process Validation | Cond. | Yes |
| 7.5.7 | Sterilization / Sterile Barrier Validation | Cond. | Yes |
| 7.5.8 | Product Identification | Yes | Yes |
| 7.5.9 | Traceability | Yes | Yes |
| 7.5.10 | Customer Property | Cond. | Yes |
| 7.5.11 | Preservation of Product | Yes | Yes |
| 7.6 | Control of Monitoring & Measuring Equipment | Yes | Yes |
| 8.2.1 | Feedback | Yes | Yes |
| 8.2.2 | Complaint Handling | Yes | Yes |
| 8.2.3 | Reporting to Regulatory Authorities | Yes | Yes |
| 8.2.4 | Internal Audit | Yes | Yes |
| 8.2.5 | Process Monitoring & Measurement | Yes | Yes |
| 8.2.6 | Product Monitoring & Measurement | Yes | Yes |
| 8.3 | Control of Nonconforming Product (incl. rework) | Yes | Yes |
| 8.4 | Analysis of Data | Yes | Yes |
| 8.5.2 | Corrective Action | Yes | Yes |
| 8.5.3 | Preventive Action | Yes | Yes |

---

## What each procedure must address (quick reference)

- **Risk Management (4.1.5)** — methodology, analysis/evaluation, risk controls,
  acceptability criteria, review (per ISO 14971).
- **Software Validation (4.1.6)** — risk-based approach, validation activities,
  acceptance criteria, user responsibilities, revalidation triggers.
- **Control of Documents (4.2.4)** — approval, review/update, revision status,
  availability at point of use, external documents, obsolete-document control.
- **Control of Records (4.2.5)** — identification, storage, security, integrity,
  retrieval, retention, disposition, change identification.
- **Management Review (5.6.1)** — frequency (≥ annual), the required inputs and outputs,
  attendees, records.
- **Competence/Training (6.2)** — competence determination, training provision and
  effectiveness evaluation, awareness, records.
- **Purchasing (7.4.1)** — supplier evaluation/selection/monitoring criteria, purchasing
  controls, change notification, sub-tier communication.
- **Design & Development (7.3)** — planning, inputs, outputs, review, verification,
  validation, transfer, change control, design files.
- **Process Validation (7.5.6)** — validate where output is not fully verifiable;
  equipment/personnel qualification; revalidation criteria; production-software validation.
- **Identification & Traceability (7.5.8/7.5.9)** — identification throughout realization;
  traceability extent; distribution records (consignee name/address, quantity shipped).
- **Feedback (8.2.1)** — early-warning system, post-production data, links to risk and CAPA.
- **Complaint Handling (8.2.2)** — receipt/recording/evaluation/investigation, regulatory
  reporting decision, customer notification, trending, records.
- **Internal Audit (8.2.4)** — program planning, criteria/scope/frequency/methods,
  impartial auditors, reporting, follow-up.
- **Nonconforming Product (8.3)** — identification, segregation, disposition, concession
  authority, actions before/after delivery, rework.
- **CAPA (8.5.2/8.5.3)** — nonconformity review, cause determination, action
  planning/implementation, effectiveness review, information sources, records.

---

## Required records (by clause, non-exhaustive)

- **Clause 4** — software validation (4.1.6); risk management (4.1.5); any records named
  in procedures/work instructions; regulatory-required records.
- **Clause 5-6** — management reviews (5.6.1); personnel competence/training (6.2);
  infrastructure maintenance (6.3).
- **Clause 7** — requirements review (7.2.2); design & development files (7.3.10);
  transfer (7.3.8); supplier evaluation/monitoring (7.4.1); purchased-product verification
  (7.4.3); cleanliness (7.5.2); installation (7.5.3); servicing (7.5.4); sterilization
  parameters per batch (7.5.5/7.5.7); process validation (7.5.6); identification &
  traceability incl. distribution (7.5.8/7.5.9); customer property (7.5.10); calibration
  (7.6).
- **Clause 8** — feedback/complaints (8.2.1/8.2.2); regulatory reporting (8.2.3); internal
  audits (8.2.4); process/product monitoring and release authority (8.2.5/8.2.6);
  nonconformities and concessions (8.3); data analysis (8.4); corrective and preventive
  action (8.5.2/8.5.3).

---

## Record retention

- **Minimum**: the lifetime of the medical device as the organization defines it, and not
  less than the retention period of any resulting record (4.2.5).
- **Regulatory**: as specified by applicable requirements — often 5-10 years minimum, and
  longer for implantable/long-life devices.
- **Contractual**: honor any longer customer-mandated period.

Define "device lifetime" explicitly and set retention to meet or exceed the strictest of
these.

---

## Commonly needed but not ISO-13485-mandated

Work instructions (manufacturing, testing, inspection, cleaning, equipment); forms
(training, calibration, audit checklists, complaint, CAPA, change request, supplier
evaluation); plans (quality plan, validation plans, post-market surveillance, clinical
evaluation); technical documentation (specs, test methods, packaging, labeling, IFU); and
region-specific regulatory dossiers (EU MDR/IVDR technical files, FDA 510(k)/PMA, clinical
evaluation reports, PSUR). These support conformity even though the standard does not name
them individually.
