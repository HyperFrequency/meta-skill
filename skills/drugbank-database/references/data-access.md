# DrugBank Data Access

Authentication, downloading, parsing, caching, and a reusable helper class.

## Authentication

DrugBank requires an account to download data.

1. Register at go.drugbank.com and accept the license (free for academic use;
   commercial use requires a paid license).
2. Note your username and password.

Supply credentials one of three ways (in order of preference):

**Environment variables (recommended)**

```bash
export DRUGBANK_USERNAME="your_username"
export DRUGBANK_PASSWORD="your_password"
```

**Config file** — `~/.config/drugbank.ini`:

```ini
[drugbank]
username = your_username
password = your_password
```

**Direct (avoid — leaks into logs/history)**

```python
download_drugbank(username="user", password="pass")
```

## Installation

```bash
uv pip install drugbank-downloader   # Python >= 3.9
uv pip install bioversions           # optional: auto-detect latest version
uv pip install lxml                   # optional: faster/robust XML parsing
```

`drugbank-downloader` is MIT-licensed (by Charles Tapley Hoyt). The DrugBank
data it fetches is CC BY-NC 4.0 and governed by DrugBank's license agreement.

## Downloading

```python
from drugbank_downloader import download_drugbank

# Pin an exact version for reproducibility (returns the local file path)
path = download_drugbank(version="5.1.10")
# -> ~/.data/drugbank/5.1.10/full database.xml.zip

# Latest version (requires bioversions)
path = download_drugbank()

# Custom storage prefix
path = download_drugbank(version="5.1.10", prefix=["custom", "location", "drugbank"])
```

Verify the download completed (the archive is ~150 MB compressed; expect > 1 GB
uncompressed):

```python
import os
if os.path.exists(path):
    print(f"{os.path.getsize(path) / 1024**2:.1f} MB")
```

CLI equivalent:

```bash
drugbank_downloader --username USER --password PASS   # or rely on env/config
```

## Parsing

`drugbank-downloader` reads the zipped XML without extracting it.

```python
from drugbank_downloader import open_drugbank, parse_drugbank, get_drugbank_root
import xml.etree.ElementTree as ET

# Stream the file object out of the zip
with open_drugbank(version="5.1.10") as handle:
    tree = ET.parse(handle)
    root = tree.getroot()

# Or use the convenience wrappers
tree = parse_drugbank(version="5.1.10")   # ElementTree
root = get_drugbank_root(version="5.1.10")  # root <drugbank> element
```

Every query needs the DrugBank namespace bound:

```python
ns = {"db": "http://www.drugbank.ca"}
drugs = root.findall("db:drug", ns)
```

## Caching parsed results

Parsing is slow and memory-heavy; cache derived structures keyed by version so
the cache invalidates when you upgrade DrugBank.

```python
import pickle
from pathlib import Path

version = "5.1.10"
cache_file = Path(f"drugbank_{version}_index.pkl")

if cache_file.exists():
    with cache_file.open("rb") as f:
        index = pickle.load(f)
else:
    index = build_indexes(get_drugbank_root(version=version))  # see drug-queries.md
    with cache_file.open("wb") as f:
        pickle.dump(index, f)
```

## Reusable helper class

A small class that lazily loads the root, caches drug-element lookups, and wraps
the most common extractions. Extend it with methods from the other reference
files as needed.

```python
import xml.etree.ElementTree as ET
from typing import Any, Optional

class DrugBankHelper:
    """Lazy accessor over a parsed DrugBank tree, with per-drug caching."""

    NS = {"db": "http://www.drugbank.ca"}

    def __init__(self, root: Optional[ET.Element] = None, version: str | None = None):
        self._root = root
        self._version = version
        self._drug_cache: dict[str, ET.Element] = {}

    def _get_root(self) -> ET.Element:
        if self._root is None:
            from drugbank_downloader import get_drugbank_root
            self._root = get_drugbank_root(version=self._version)
        return self._root

    @staticmethod
    def _text(element) -> Optional[str]:
        return element.text if element is not None else None

    def find_drug(self, drugbank_id: str) -> Optional[ET.Element]:
        """Return the <drug> element with the given primary DrugBank ID."""
        if drugbank_id in self._drug_cache:
            return self._drug_cache[drugbank_id]
        for drug in self._get_root().findall("db:drug", self.NS):
            primary = drug.find('db:drugbank-id[@primary="true"]', self.NS)
            if primary is not None and primary.text == drugbank_id:
                self._drug_cache[drugbank_id] = drug
                return drug
        return None

    def get_drug_info(self, drugbank_id: str) -> dict[str, Any]:
        drug = self.find_drug(drugbank_id)
        if drug is None:
            return {}
        f = lambda tag: self._text(drug.find(f"db:{tag}", self.NS))
        return {
            "drugbank_id": drugbank_id,
            "name": f("name"),
            "type": drug.get("type"),
            "description": f("description"),
            "cas_number": f("cas-number"),
            "indication": f("indication"),
            "mechanism_of_action": f("mechanism-of-action"),
        }
```

Usage:

```python
db = DrugBankHelper(version="5.1.10")
print(db.get_drug_info("DB00001")["name"])   # -> Lepirudin
```

Note `find_drug` is O(n) on first miss (it scans until it matches). For many
lookups, build a full ID index once — see `references/drug-queries.md`.

## API vs bulk download

DrugBank also offers a credentialed REST/Clinical API (separate key, scoped by
region — FDA/Health Canada/EMA — and rate-limited). Terms and quotas change;
consult DrugBank's current API documentation. **For any batch or whole-database
work, prefer the bulk XML download over the API** — it is faster, reproducible,
and avoids rate limits. Cache API responses locally if you must use it.

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| Authentication fails | Wrong credentials, unaccepted license, or expired account |
| Download fails | Network, insufficient disk (~1-2 GB), or unavailable version — retry an older stable version (e.g. `5.1.7`) |
| Queries return `None`/`[]` | Namespace not bound — pass `{"db": "http://www.drugbank.ca"}` |
| Parse error | Incomplete download (check file size) or corrupt XML — re-download; try `lxml` |
| MemoryError | Tree too large — use `lxml`, `iterparse` streaming, or subset to approved drugs |

```python
from drugbank_downloader import download_drugbank

try:
    path = download_drugbank(version="5.1.10")
except Exception as e:
    print(f"Falling back: {e}")
    path = download_drugbank(version="5.1.7")   # older stable version
```

## Best practices

1. Pin the exact version and record it in your analysis/publication.
2. Keep credentials in env vars or a config file, never in code.
3. Cache parsed/indexed data keyed by version.
4. Keep local copies to reduce re-downloads.
5. Confirm licensing (CC BY-NC) fits your use case before starting.
