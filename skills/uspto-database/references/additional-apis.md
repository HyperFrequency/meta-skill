# Additional USPTO APIs

Beyond PatentSearch, examination data, and trademarks, USPTO exposes specialized APIs for
citations, office actions, patent ownership, post-grant trials, litigation, and code
lookups. Most are served through the Open Data Portal (`https://data.uspto.gov/`); confirm
current versions and paths in the API catalog (`https://developer.uspto.gov/api-catalog`).
All use the USPTO account key (`X-Api-Key`).

## 1. Enriched Citation API

- **Versions:** v3 / v2 / v1
- Citation intelligence for IP5 offices (USPTO, EPO, JPO, KIPO, CNIPA) and public use.
- **Provides:** forward citations (who cites a patent), backward citations (its prior
  art), examiner-vs-applicant attribution, and citation context.
- **Use for:** prior-art analysis, patent-landscape mapping, and citation-based strength
  signals.

## 2. Office-Action APIs

### 2.1 Office-Action Text Retrieval (v1)
Full-text of office-action correspondence for an application: restrictions, rejections,
objections, examiner amendments, and search notes. Typical flow: use examination data
(PEDS/ODP) to learn *which* office actions exist for an application, then pull their text
here.

### 2.2 Office-Action Citations (v2, beta v1)
Patent and non-patent-literature citations *extracted from office actions* — the
references examiners actually relied on, with context (rejection vs. informational). A
research dataset for examiner search behavior.

### 2.3 Office-Action Rejection (v2, beta v1)
Structured rejection data (bulk data through ~March 2025). Rejection statutes:

| Statute | Basis |
| --- | --- |
| 35 U.S.C. §102 | Anticipation (lack of novelty) |
| 35 U.S.C. §103 | Obviousness |
| 35 U.S.C. §112 | Enablement / written description / indefiniteness |
| 35 U.S.C. §101 | Subject-matter eligibility |

Use to analyze common rejection reasons, spot problematic claim language, and mine
historical responses.

### 2.4 Office-Action Weekly Zips (v1)
Bulk weekly archives of full-text office-action documents for large-scale analysis.

## 3. Patent Assignment Search API

- **Version:** v1.4 — **XML** responses
- **Base URL:** `https://assignment-api.uspto.gov/patent/v1.4/`

```
GET  /v1.4/assignment/patent/{patent_number}
GET  /v1.4/assignment/application/{application_number}
POST /v1.4/assignment/search    body: {"criteria": {"assigneeName": "Company Name"}}
```

```python
import os, requests
import xml.etree.ElementTree as ET

def patent_assignments(patent_number):
    r = requests.get(
        f"https://assignment-api.uspto.gov/patent/v1.4/assignment/patent/{patent_number}",
        headers={"X-Api-Key": os.environ["USPTO_API_KEY"]}, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return [
        {
            "recorded": a.findtext("recordedDate"),
            "assignor": a.findtext(".//assignor/name"),
            "assignee": a.findtext(".//assignee/name"),
            "type": a.findtext("conveyanceText"),
        }
        for a in root.findall(".//assignment")
    ]
```

Conveyance types mirror trademarks: `ASSIGNMENT OF ASSIGNORS INTEREST`,
`SECURITY AGREEMENT`, `MERGER`, `CHANGE OF NAME`, `ASSIGNMENT OF PARTIAL INTEREST`.

## 4. PTAB API

- **Version:** v2 — Patent Trial and Appeal Board proceedings.
- **Covers:** inter partes review (IPR), post-grant review (PGR), covered-business-method
  (CBM) review, and ex parte appeals.
- **Data:** petitions, trial and final written decisions, petitioner/patent-owner
  identities, claims challenged, and outcomes.
- Migrating to the Open Data Portal — check current access details.

## 5. Patent Litigation Cases API

- **Version:** v1 — ~74,600+ U.S. district-court litigation records.
- **Data:** case numbers and filing dates, asserted patents, parties, venues, outcomes.
- **Use for:** litigation-risk analysis, most-litigated-patent lists, venue trends,
  enforcement patterns.

## 6. Cancer Moonshot Patent Data Set API

- **Version:** v1.0.1 — curated cancer-related patents (research, treatment, diagnostics)
  with bulk download and cancer-type/treatment categorization. For oncology prior art and
  landscape work.

## 7. OCE Patent Examination Status/Event Codes API

- **Version:** v1 — the official decoder for USPTO status and event codes.
- Use it to translate transaction codes from examination data into human-readable
  descriptions instead of hardcoding a lookup table:

```python
def enrich_transactions(transactions, describe):
    """describe(code) -> str, backed by the OCE codes API (cache it)."""
    for t in transactions:
        t["description"] = describe(t["code"])
    return transactions
```

## Combined-workflow pattern

One patent, many APIs — assemble a full intelligence record:

```python
def full_patent_profile(patent_number):
    return {
        "details":     search_patent(patent_number),        # PatentSearch
        "prosecution": examination_history(patent_number),  # PEDS / ODP
        "assignments": patent_assignments(patent_number),   # Assignment (XML)
        "citations":   enriched_citations(patent_number),   # Enriched Citation
        "litigation":  litigation_for(patent_number),       # Litigation Cases
        "ptab":        ptab_proceedings(patent_number),     # PTAB
    }
```

For a company portfolio: start from Patent Assignment Search (`assigneeName`) or a
PatentSearch assignee query to enumerate patents, then run `full_patent_profile` per patent
and aggregate (counts, citation totals, litigated share, technology areas).

## Cross-cutting best practices

- **One key across these APIs** — the USPTO account key covers TSDR, assignments, and the
  Open Data Portal endpoints (PatentSearch is the separate PatentsView key).
- **Exponential backoff** on `429`/`5xx`; cache responses.
- **Validate inputs** (patent/application/serial numbers) before calling.
- **Track versions** — several of these APIs are mid-migration to `data.uspto.gov`;
  pin and re-verify endpoints for long-running jobs.

## Resources

- Developer portal: `https://developer.uspto.gov/`
- API catalog: `https://developer.uspto.gov/api-catalog`
- Open Data Portal: `https://data.uspto.gov/`
- Key registration: `https://account.uspto.gov/api-manager/`
