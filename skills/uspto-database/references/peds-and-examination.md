# Patent Examination Data (PEDS / Open Data Portal)

Examination (prosecution) data is the timeline of what happened to a patent application
between filing and disposition: transaction events, status changes, office actions,
continuity/family links, and patent-term adjustment.

## Where this data lives — read this first

- **PAIR Bulk Data (PBD)** — decommissioned. Do not use.
- **PEDS** (`ped.uspto.gov`) — the long-standing examination-data system that replaced
  PBD. **USPTO is migrating examination data to the Open Data Portal**
  (`data.uspto.gov`), and PEDS endpoints are being retired. Treat PEDS URLs as
  transitional and **verify the current access path at `data.uspto.gov` before building a
  long-running integration.**
- **Coverage:** roughly **1981–present** (some bibliographic records back to 1935).

Because the underlying host is in flux, this reference describes *capabilities and codes*
you can rely on, and points to the maintained library and portal for exact request shapes
rather than asserting endpoint paths that may have moved.

## Scripted access: `uspto-opendata-python`

The community library from ip-tools wraps USPTO examination data by application or patent
number.

```bash
pip install uspto-opendata-python
```

- Docs: `https://docs.ip-tools.org/uspto-opendata-python/`
- PyPI: `https://pypi.org/project/uspto-opendata-python/`
- Source: `https://github.com/ip-tools/uspto-opendata-python`

Consult the library docs for the current client class and method names (the package has
tracked USPTO's backend changes over time). Conceptually it lets you fetch an
application's bibliographic record plus its transaction list, then you post-process the
transactions yourself.

If the library lags a USPTO migration, fall back to direct HTTP against `data.uspto.gov`
using your USPTO account key (`X-Api-Key`) per the portal's current API catalog.

## What examination data gives you

- **Bibliographic:** application number, filing date, title, inventors, assignees,
  application type (utility/design/plant/reissue), patent number + issue date if granted.
- **Transaction history:** every examination event with a date, a code, and a description.
- **Status:** current application status and status date.
- **Patent-term adjustment/extension (PTA/PTE):** summary and history.
- **Continuity/family:** parent/child application relationships.

## Status values (examples)

`Patented Case`, `Pending`, `Allowed`, `Abandoned`, `Non-Final Rejection`,
`Final Rejection`, `Response Filed`.

## Transaction (event) codes

Frequently encountered codes:

| Code | Meaning |
| --- | --- |
| `CTNF` | Non-final rejection mailed |
| `CTFR` | Final rejection mailed |
| `AOPF`/`CTAV` | Office action / action mailed |
| `NOA` | Notice of allowance mailed |
| `WRIT` | Applicant response filed |
| `ISS.FEE` | Issue-fee payment |
| `ABND` | Application abandoned |

The authoritative, full list of status and event codes is served by the **OCE Patent
Examination Status/Event Codes API** (see `additional-apis.md`) — use it to decode any
code you do not recognize instead of hardcoding descriptions.

## Prosecution-analysis patterns

Once you have an application's transaction list, these are the common derived metrics.
Adapt field names to whatever the library/portal returns.

```python
from datetime import datetime

def pendency_days(filing_date, issue_date):
    fmt = "%Y-%m-%d"
    return (datetime.strptime(issue_date, fmt) - datetime.strptime(filing_date, fmt)).days

def summarize_prosecution(transactions):
    """Count office actions and rejection types from a transaction list."""
    codes = [t["code"] for t in transactions]
    return {
        "non_final_rejections": codes.count("CTNF"),
        "final_rejections": codes.count("CTFR"),
        "notices_of_allowance": codes.count("NOA"),
        "responses_filed": codes.count("WRIT"),
        "abandoned": "ABND" in codes,
    }

def recent_office_actions(transactions, since="2024-01-01"):
    oa_codes = {"CTNF", "CTFR", "AOPF"}
    return [t for t in transactions if t["code"] in oa_codes and t["date"] > since]
```

For a portfolio, iterate applications and aggregate: average pendency, rejection-rate
distribution, share still pending vs. granted vs. abandoned.

## Integration with other APIs

- **Office-Action Text API** — pull the *full text* of an office action once PEDS/ODP
  tells you it exists (match by application number).
- **Patent Assignment Search** — ownership changes over the application's life.
- **PTAB API** — whether the granted patent later faced an IPR/PGR challenge.
- **OCE Status/Event Codes API** — decode transaction codes.

## Notes

- Use standardized application numbers (digits only — no slashes or spaces).
- Data can lag real prosecution by 1–2 days.
- Not every field is populated for every application; code defensively.
- Batch and cache; re-fetch only to pick up new transactions.
