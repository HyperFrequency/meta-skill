# ISO 13485 Gap Analysis

Gap analysis measures the distance between an existing QMS and ISO 13485:2016. Run it in
two passes: an **automated keyword scan** to flag which required procedures/documents are
even present, then a **manual deep review** that judges adequacy and implementation — not
just presence. Presence of a document titled "CAPA" does not mean the CAPA clause is met.

## Status scheme

Score every requirement with one of four states:

| Status | Meaning |
|--------|---------|
| Compliant | Fully implemented and documented, with evidence |
| Partial | Implemented but incomplete or weak; needs improvement |
| Non-compliant | Not implemented or not documented |
| N/A | Genuinely inapplicable — **must be justified** in the Quality Manual |

For each item record: current status, existing evidence (document/record IDs), the gap,
the action required, an owner, and a target date.

## Pass 1 — automated keyword scan

The scan reads a directory of QMS documents and checks each required procedure/key
document's keyword set against the corpus, then reports coverage and a compliance
percentage. It is a **triage flag only** — a keyword hit does not confirm conformity, and
a miss may be a wording difference, so always confirm manually.

### Clause → procedure keyword map

The map below drives the scan. Extend it for regulation-specific documents you expect.

| Clause | Procedure | Trigger keywords |
|--------|-----------|------------------|
| 4.1.5 | Risk Management | risk management, iso 14971, risk analysis, risk control |
| 4.1.6 | Software Validation | software validation, computer software, validation |
| 4.2.4 | Control of Documents | document control, document approval, obsolete document |
| 4.2.5 | Control of Records | record control, retention, record storage, retrieval |
| 5.5.3 | Internal Communication | internal communication, qms communication |
| 5.6.1 | Management Review | management review, review meeting |
| 6.2 | Competence / Training | competence, training, personnel qualification |
| 7.2.3 | Customer Communication | customer communication, customer feedback, advisory notice |
| 7.3 | Design & Development | design input, design output, design verification, design validation |
| 7.4.1 | Purchasing | purchasing, supplier, procurement, vendor |
| 7.4.3 | Verification of Purchased Product | incoming inspection, verification of purchased |
| 7.5.1 | Production & Service | production, manufacturing, work instruction, process control |
| 7.5.6 | Process Validation | process validation, validation protocol, validation report |
| 7.5.8 | Product Identification | product identification, labeling, marking |
| 7.5.9 | Traceability | traceability, lot, serial number, batch |
| 7.5.11 | Preservation of Product | preservation, storage, packaging, handling |
| 7.6 | Control of M&M Equipment | calibration, measuring equipment, measurement |
| 8.2.1 | Feedback | feedback, post-production, post-market, early warning |
| 8.2.2 | Complaint Handling | complaint, complaint handling, complaint investigation |
| 8.2.3 | Regulatory Reporting | regulatory reporting, adverse event, reportable event |
| 8.2.4 | Internal Audit | internal audit, audit program, audit checklist |
| 8.2.5 | Process Monitoring | process monitoring, process measurement, process metrics |
| 8.2.6 | Product Monitoring | product inspection, acceptance criteria, release |
| 8.3 | Nonconforming Product | nonconforming, ncr, nonconformance, reject |
| 8.5.2 | Corrective Action | corrective action, capa, root cause |
| 8.5.3 | Preventive Action | preventive action, capa, prevention |

Key documents (not procedures): **Quality Manual** (quality manual, quality management
system), **Medical Device File** (medical device file, mdf, dmr), **Quality Policy**,
**Quality Objectives**.

### Scan script

Save as `gap_scan.py` and run with `python gap_scan.py --docs-dir <path> [--output
report.json]`. It reads `.txt`/`.md` full-text and falls back to filename matching for
binary formats (`.pdf/.docx/.odt`) — extract those to text first for a reliable scan.

```python
#!/usr/bin/env python3
"""Keyword triage of a QMS document set against ISO 13485:2016 procedures."""
import argparse, json
from datetime import datetime
from pathlib import Path

PROCEDURES = {
    "4.1.5": ("Risk Management", ["risk management", "iso 14971", "risk analysis", "risk control"]),
    "4.1.6": ("Software Validation", ["software validation", "computer software", "validation"]),
    "4.2.4": ("Control of Documents", ["document control", "document approval", "obsolete document"]),
    "4.2.5": ("Control of Records", ["record control", "retention", "record storage", "retrieval"]),
    "5.5.3": ("Internal Communication", ["internal communication", "qms communication"]),
    "5.6.1": ("Management Review", ["management review", "review meeting"]),
    "6.2":   ("Competence/Training", ["competence", "training", "personnel qualification"]),
    "7.2.3": ("Customer Communication", ["customer communication", "customer feedback", "advisory notice"]),
    "7.3":   ("Design and Development", ["design input", "design output", "design verification", "design validation"]),
    "7.4.1": ("Purchasing", ["purchasing", "supplier", "procurement", "vendor"]),
    "7.4.3": ("Verification of Purchased Product", ["incoming inspection", "verification of purchased"]),
    "7.5.1": ("Production and Service", ["production", "manufacturing", "work instruction", "process control"]),
    "7.5.6": ("Process Validation", ["process validation", "validation protocol", "validation report"]),
    "7.5.8": ("Product Identification", ["product identification", "labeling", "marking"]),
    "7.5.9": ("Traceability", ["traceability", "lot", "serial number", "batch"]),
    "7.5.11":("Preservation of Product", ["preservation", "storage", "packaging", "handling"]),
    "7.6":   ("Control of M&M Equipment", ["calibration", "measuring equipment", "measurement"]),
    "8.2.1": ("Feedback", ["feedback", "post-production", "post-market", "early warning"]),
    "8.2.2": ("Complaint Handling", ["complaint", "complaint handling", "complaint investigation"]),
    "8.2.3": ("Regulatory Reporting", ["regulatory reporting", "adverse event", "reportable event"]),
    "8.2.4": ("Internal Audit", ["internal audit", "audit program", "audit checklist"]),
    "8.2.5": ("Process Monitoring", ["process monitoring", "process measurement", "process metrics"]),
    "8.2.6": ("Product Monitoring", ["product inspection", "acceptance criteria", "release"]),
    "8.3":   ("Nonconforming Product", ["nonconforming", "ncr", "nonconformance", "reject"]),
    "8.5.2": ("Corrective Action", ["corrective action", "capa", "root cause"]),
    "8.5.3": ("Preventive Action", ["preventive action", "capa", "prevention"]),
}
KEY_DOCS = {
    "Quality Manual": ["quality manual", "quality management system"],
    "Medical Device File": ["medical device file", "mdf", "device master record", "dmr"],
    "Quality Policy": ["quality policy"],
    "Quality Objectives": ["quality objective"],
}
HIGH_PRIORITY = {"8.2.2", "8.5.2", "8.5.3", "7.4.1", "8.2.4"}
TEXT_EXT = {".txt", ".md"}
BINARY_EXT = {".pdf", ".doc", ".docx", ".odt"}

def load(docs_dir: Path):
    corpus = []
    for path in docs_dir.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in TEXT_EXT:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        elif ext in BINARY_EXT:
            text = path.name.lower()  # filename-only fallback; extract to text for accuracy
        else:
            continue
        corpus.append((str(path.relative_to(docs_dir)), text))
    return corpus

def hits(corpus, keywords):
    return [name for name, text in corpus if any(k in text for k in keywords)]

def analyze(docs_dir: Path):
    corpus = load(docs_dir)
    found = {c: h for c, (_, kw) in PROCEDURES.items() if (h := hits(corpus, kw))}
    docs = {d: h for d, kw in KEY_DOCS.items() if (h := hits(corpus, kw))}
    missing = [{"clause": c, "title": PROCEDURES[c][0]} for c in PROCEDURES if c not in found]
    total = len(PROCEDURES)
    recs = []
    if "Quality Manual" not in docs:
        recs.append("CRITICAL: no Quality Manual detected — the foundational QMS document.")
    crit = [m["title"] for m in missing if m["clause"] in HIGH_PRIORITY]
    if crit:
        recs.append("HIGH PRIORITY: draft critical procedures: " + ", ".join(crit))
    return {
        "analysis_date": datetime.now().isoformat(),
        "documents_analyzed": str(docs_dir),
        "files_scanned": len(corpus),
        "summary": {
            "required_procedures": total,
            "procedures_found": len(found),
            "procedures_missing": total - len(found),
            "compliance_percentage": round(len(found) / total * 100, 1),
        },
        "found_procedures": found,
        "missing_procedures": missing,
        "found_documents": docs,
        "recommendations": recs,
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ISO 13485 keyword gap triage")
    ap.add_argument("--docs-dir", required=True)
    ap.add_argument("--output")
    a = ap.parse_args()
    report = analyze(Path(a.docs_dir))
    print(json.dumps(report["summary"], indent=2))
    for r in report["recommendations"]:
        print("-", r)
    if a.output:
        Path(a.output).write_text(json.dumps(report, indent=2))
        print("saved:", a.output)
```

## Pass 2 — manual deep review

Work the full clause list (Clauses 4-8) item by item, scoring each with the status scheme.
For every item: read the requirement, locate existing evidence, note the gap, and define
the action. Then roll up compliance per clause:

| Clause | Items | Compliant | Partial | Non-compliant | N/A | Compliance % |
|--------|-------|-----------|---------|---------------|-----|--------------|
| 4. QMS | | | | | | |
| 5. Management | | | | | | |
| 6. Resources | | | | | | |
| 7. Product realization | | | | | | |
| 8. Measurement & improvement | | | | | | |

The item-level requirement list is the clause breakdown in
`requirements-by-clause.md`; expand each clause into its lettered sub-requirements.

## Prioritized action plan

Rank gaps by risk and regulatory exposure, not by clause order:

- **Critical (now)** — missing Quality Manual/policy; safety- or reporting-related gaps
  (complaints 8.2.2, CAPA 8.5.2/8.5.3, nonconforming product 8.3, regulatory reporting
  8.2.3).
- **High (≤30 days)** — core process procedures (internal audit 8.2.4, purchasing 7.4.1,
  management review 5.6.1, document/record control).
- **Medium (≤90 days)** — supporting processes (competence, calibration, validation,
  traceability).
- **Low (≤180 days)** — refinements and improvement opportunities.

Capture owners, target dates, and resource needs, then track milestones through gap-closure
→ internal audit readiness → certification audit.

## Audit-readiness review

Re-run the same checklist as a readiness gate before a certification or surveillance audit:

- [ ] All applicable documented procedures approved and effective.
- [ ] Quality Manual complete, with justified exclusions and a signed quality policy.
- [ ] A Medical Device File complete for every product family.
- [ ] At least one internal audit completed and findings closed.
- [ ] A management review completed with recorded outputs.
- [ ] Records exist for every required item (not just the procedures).
- [ ] CAPA and complaint systems demonstrably operating with effectiveness evidence.
- [ ] Personnel trained on the QMS procedures they perform.

Then run a **mock audit** using the clause requirements as criteria: sample records to
confirm consistent implementation and interview staff to confirm understanding.
