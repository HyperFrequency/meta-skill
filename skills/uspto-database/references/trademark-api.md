# USPTO Trademark APIs

Two APIs cover trademarks:

1. **TSDR** (Trademark Status & Document Retrieval) — case status, prosecution, owners,
   goods/services, documents.
2. **Trademark Assignment Search** — ownership transfers and security interests.

Both authenticate with the **USPTO account key** (`X-Api-Key`, from
`https://account.uspto.gov/api-manager/`) — not the PatentSearch/PatentsView key.

## 1. TSDR

- **Base URL:** `https://tsdrapi.uspto.gov/ts/cd/`
- **Swagger:** `https://developer.uspto.gov/swagger/tsdr-api-v1`

### Status by serial or registration number

```
GET /ts/cd/casedocs/sn{serial_number}/info.json      # by serial (application) number
GET /ts/cd/casedocs/rn{registration_number}/info.json # by registration number
```

```python
import os, requests

def get_trademark_status(serial_number):
    r = requests.get(
        f"https://tsdrapi.uspto.gov/ts/cd/casedocs/sn{serial_number}/info.json",
        headers={"X-Api-Key": os.environ["USPTO_API_KEY"]}, timeout=30)
    r.raise_for_status()
    return r.json()["TradeMarkAppln"]

tm = get_trademark_status("87654321")
print(tm["MarkVerbalElementText"], "→",
      tm["MarkCurrentStatusExternalDescriptionText"])
```

### Response fields (under `TradeMarkAppln`)

| Field | Meaning |
| --- | --- |
| `ApplicationNumber` | Serial number |
| `ApplicationDate` | Filing date |
| `ApplicationType` | TEAS Plus / Standard / etc. |
| `RegistrationNumber` | Registration number (if registered) |
| `RegistrationDate` | Registration date |
| `MarkVerbalElementText` | The mark's text |
| `MarkCurrentStatusExternalDescriptionText` | Current status text |
| `MarkCurrentStatusDate` | Status date |
| `MarkDrawingCode` | Mark type (words, design, …) |
| `GoodsAndServices` | Array of classes + descriptions |
| `Owners` | Array of owners/applicants |
| `ProsecutionHistoryEntry` | Array of prosecution events |

Also available: `.json` **status**, XML, and the multi-page document bundles (TSDR serves
case documents as well as status). Check the Swagger doc for document-retrieval paths.

### Status values

`REGISTERED`, `PENDING`, `PUBLISHED FOR OPPOSITION`, `ABANDONED`, `CANCELLED`,
`SUSPENDED`, `REGISTERED AND RENEWED`.

### Portfolio-health pattern

Classify a status string into a coarse bucket, then flag marks needing attention:

```python
def classify(status):
    s = status.upper()
    if "ABANDON" in s:               return "abandoned"
    if "CANCEL" in s or "EXPIR" in s: return "expired"
    if "REGISTERED" in s:            return "active"
    if "PENDING" in s or "PUBLISHED" in s: return "pending"
    if "SUSPEND" in s:              return "suspended"
    return "other"
```

`PUBLISHED FOR OPPOSITION` (opposition clock running) and `SUSPENDED` are the states that
most often need a human to look.

## 2. Trademark Assignment Search

- **Base URL:** `https://assignment-api.uspto.gov/trademark/v1.4/`
- **Format:** **XML** (do not call `.json()`)

### Lookups

```
GET  /v1.4/assignment/application/{serial_or_registration_number}
POST /v1.4/assignment/search        body: {"criteria": {"assigneeName": "Company Name"}}
```

```python
import os, requests
import xml.etree.ElementTree as ET

def trademark_assignments(number):
    r = requests.get(
        f"https://assignment-api.uspto.gov/trademark/v1.4/assignment/application/{number}",
        headers={"X-Api-Key": os.environ["USPTO_API_KEY"]}, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    for a in root.findall(".//assignment"):
        print(a.findtext("recordedDate"),
              a.findtext(".//assignor/name"), "→",
              a.findtext(".//assignee/name"),
              "|", a.findtext("conveyanceText"))
```

### Key XML fields

`reelFrame`, `conveyanceText`, `recordedDate`, `executionDate`, `assignors/assignor/name`,
`assignees/assignee/name`, `propertyNumbers`.

### Conveyance types

`ASSIGNMENT OF ASSIGNORS INTEREST`, `SECURITY AGREEMENT`, `MERGER`, `CHANGE OF NAME`,
`ASSIGNMENT OF PARTIAL INTEREST`. To find the *current* owner, sort assignments by
`recordedDate` descending and take the newest assignee.

## Tips

- Trademark data changes infrequently — cache aggressively.
- Validate serial/registration numbers before calling.
- Handle missing fields; not all marks carry every field.
- Combine TSDR (status) with Assignment (ownership history) for a full picture.

## Resources

- TSDR: `https://developer.uspto.gov/api-catalog/tsdr-data-api`
- Trademark Assignment: `https://developer.uspto.gov/api-catalog/trademark-assignment-search-data-api`
- Trademark search UI: `https://tmsearch.uspto.gov/`
- Key registration: `https://account.uspto.gov/api-manager/`
