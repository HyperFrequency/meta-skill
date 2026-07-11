# ZINC22 / CartBlanche22 — API Reference

Technical reference for querying ZINC programmatically: base URLs, endpoint grammar,
parameters, output fields, the tranche system, the file repository, similarity/substructure
services, rate limiting, and version differences.

> **Read this first — grammar caveat.** ZINC's programmatic surface is spread across several
> docking.org services and its URL grammar has changed between releases. The patterns below
> reflect the documented CartBlanche22 conventions and are a reliable *starting point*, but
> confirm the exact spelling against the live app (`cartblanche22.docking.org`) and
> `wiki.docking.org` before building large pipelines. The *capabilities* (ID lookup, SMILES
> similarity, catalog resolution, random sampling, tranche downloads) are stable; the exact
> query string may drift.

## Base URLs

| Purpose | URL |
|---|---|
| ZINC22 substance API | `https://cartblanche22.docking.org/` |
| Similarity search (SmallWorld) | `https://sw.docking.org/` |
| Substructure / SMARTS search (Arthor) | `https://arthor.docking.org/` |
| 3D file repository | `https://files.docking.org/` and `https://files22.docking.org/` |
| Main website | `https://zinc.docking.org/` |
| Documentation wiki | `https://wiki.docking.org/` |
| Source / issues | `https://github.com/docking-org/` |
| ZINC20 (maintained) | `https://zinc20.docking.org/` |

## Endpoints (CartBlanche22)

All endpoints accept a `.txt` (TSV) or `.json` extension and an `output_fields` list.
Small queries go over GET; large batches are uploaded via POST / multipart file.

### 1. Substances by ZINC ID — `/substances.txt`

| Parameter | Req? | Meaning |
|---|---|---|
| `zinc_id` | yes | single ZINC ID or comma-separated list |
| `output_fields` | no | comma-separated field names (default: all) |

```bash
# Single
curl "https://cartblanche22.docking.org/[email protected]_fields=zinc_id,smiles,catalogs"

# Multiple
curl "https://cartblanche22.docking.org/substances.txt:zinc_id=ZINC000000000001,ZINC000000000002,ZINC000000000003&output_fields=zinc_id,smiles,tranche"

# Large batch via POST + file upload (one ID per line in zinc_ids.txt)
curl -X POST "https://cartblanche22.docking.org/substances.txt?output_fields=zinc_id,smiles" \
  -F "zinc_id=@zinc_ids.txt"
```

TSV response shape:

```
zinc_id             smiles     catalogs
ZINC000000000001    CC(C)O     [vendor1,vendor2]
ZINC000000000002    c1ccccc1   [vendor3]
```

### 2. Structure search by SMILES — `/smiles.txt`

| Parameter | Req? | Meaning |
|---|---|---|
| `smiles` | yes | query SMILES (URL-encode special characters) |
| `dist` | no | Tanimoto distance threshold, 0–10 (0 = exact) |
| `adist` | no | secondary/anonymized distance metric, 0–10 |
| `output_fields` | no | comma-separated field names |

```bash
# Exact match
curl "https://cartblanche22.docking.org/smiles.txt:smiles=c1ccccc1&output_fields=zinc_id,smiles"

# Analog search, Tanimoto distance 3
curl "https://cartblanche22.docking.org/smiles.txt:smiles=CC(C)Cc1ccc(cc1)C(C)C(=O)O&dist=3&output_fields=zinc_id,smiles,catalogs"

# URL-encoded SMILES (aspirin: CC(=O)Oc1ccccc1C(=O)O)
curl "https://cartblanche22.docking.org/smiles.txt:smiles=CC%28%3DO%29Oc1ccccc1C%28%3DO%29O&dist=2"
```

Distance intuition: `0` exact · `1–3` close analogs · `4–6` moderate · `7–10` diverse.
For similarity sweeps over billions of compounds, use **SmallWorld** (`sw.docking.org`)
rather than CartBlanche; for substructure/SMARTS, use **Arthor** (`arthor.docking.org`).

### 3. Supplier code search — `/catitems.txt`

| Parameter | Req? | Meaning |
|---|---|---|
| `catitem_id` | yes | vendor catalog code |
| `output_fields` | no | comma-separated field names |

```bash
curl "https://cartblanche22.docking.org/catitems.txt:catitem_id=SUPPLIER-12345&output_fields=zinc_id,smiles,supplier_code,catalogs"
```

### 4. Random sampling — `/substance/random.txt`

| Parameter | Req? | Meaning |
|---|---|---|
| `count` | no | number of compounds (default 100; server-capped) |
| `subset` | no | `fragment` \| `lead-like` \| `drug-like` \| `lugs` |
| `output_fields` | no | comma-separated field names |

```bash
# Default 100
curl "https://cartblanche22.docking.org/substance/random.txt"

# 5000 drug-like
curl "https://cartblanche22.docking.org/substance/random.txt:count=5000&subset=drug-like&output_fields=zinc_id,smiles,tranche"
```

Subset definitions:

| Subset | Rough bounds |
|---|---|
| `fragment` | MW < 250; fragment-based discovery |
| `lead-like` | MW 250–350, LogP ≤ 3.5, rotatable bonds ≤ 7 |
| `drug-like` | MW 350–500; Lipinski Rule of Five |
| `lugs` | large, highly curated "unusually good" subset |

## Output fields

| Field | Description | Example |
|---|---|---|
| `zinc_id` | ZINC identifier | `ZINC000000000001` |
| `smiles` | canonical SMILES | `CC(C)O` |
| `sub_id` | internal substance ID | `123456` |
| `supplier_code` | vendor catalog number | `AB-1234567` |
| `catalogs` | list of suppliers | `[emolecules,mcule]` |
| `tranche` | encoded physicochemical bin | `H02P025M300-0` |

Not every field is available on every endpoint or version. Omit `output_fields` to get all
available fields as TSV. Request the minimal set to cut transfer for large pulls.

## Tranche system

ZINC partitions its library into **tranches** — physicochemical bins used for organization
and for laying out the 3D file repository, so you can download exactly one property window.

> **Encoding caveat.** The exact meaning of each tranche-code component has varied across
> ZINC versions (early ZINC keyed tranches on heavy-atom count × LogP; other encodings key
> on H-bond donors, LogP, and MW). Confirm the current scheme on the wiki before relying on
> a parse. One documented `H##P###M###-phase` interpretation:

| Component | Documented meaning | Range |
|---|---|---|
| `H##` | hydrogen-bond donors (or heavy-atom count, version-dependent) | 00–99 |
| `P###` | LogP × 10 (may be signed, e.g. `P-005` = LogP −0.5) | −0xx–9xx |
| `M###` | molecular weight (Da) | 000–999 |
| `phase` | reactivity class (0 = unreactive/preferred; 1–9 increasing) | 0–9 |

```python
import re

def parse_tranche(tranche_str):
    """Parse a documented H##P###M###-phase tranche code. Returns None on mismatch.
    Verify component semantics against the current ZINC wiki for your release."""
    match = re.match(r"H(\d+)P(-?\d+)M(\d+)-(\d+)", tranche_str)
    if not match:
        return None
    return {
        "h_donors": int(match.group(1)),
        "logp": int(match.group(2)) / 10.0,
        "mw": int(match.group(3)),
        "phase": int(match.group(4)),
    }

# parse_tranche("H05P035M400-0") -> {'h_donors': 5, 'logp': 3.5, 'mw': 400, 'phase': 0}
```

## File repository

3D structures live under the file repository, organized hierarchically by tranche:

```
https://files.docking.org/zinc22/
├── H00/
│   ├── H00P010M200-0.db2.gz
│   └── ...
├── H01/
└── ...
```

| Extension | Format | Use |
|---|---|---|
| `.db2.gz` | DOCK database | multi-conformer DB for DOCK |
| `.mol2.gz` | MOL2 | 3D coordinates, general docking |
| `.sdf.gz` | SDF | structure-data file |
| `.smi` | SMILES | plain text with ZINC IDs |

Download recipes:

```bash
# Single tranche
wget https://files.docking.org/zinc22/H05/H05P035M400-0.db2.gz

# Many tranches in parallel
cat > tranche_urls.txt <<'EOF'
https://files.docking.org/zinc22/H05/H05P035M400-0.db2.gz
https://files.docking.org/zinc22/H05/H05P040M400-0.db2.gz
EOF
aria2c -i tranche_urls.txt -x 8 -j 4

# Recursive (use sparingly — very large)
wget -r -np -nH --cut-dirs=1 -A "*.db2.gz" https://files.docking.org/zinc22/H05/
```

## Rate limiting, etiquette, and retries

ZINC publishes no hard rate limit, but be a considerate client: space requests (~1 s),
batch IDs into single calls, cache locally, and schedule big downloads off-peak.

```python
import subprocess, time

def robust_zinc_query(url, max_retries=3, timeout=30):
    """GET a ZINC URL with exponential-backoff retries. Returns text or None."""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", str(timeout), url],
                capture_output=True, text=True, check=True,
            )
            if not result.stdout or "error" in result.stdout.lower():
                raise ValueError("empty or error response")
            return result.stdout
        except (subprocess.CalledProcessError, ValueError):
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None
```

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Empty results | bad SMILES, nonexistent ZINC ID, or too-tight `dist` — widen the search |
| Timeouts | lower `count`, batch queries, retry off-peak |
| Garbled SMILES query | URL-encode special characters (`urllib.parse.quote`) |
| Tranche file 404 | wrong tranche-code format or repository path — recheck the layout |
| Colon-URL rejected | grammar drift — confirm current syntax on the live app/wiki |

## Version differences

| Feature | ZINC22 | ZINC20 | ZINC15 |
|---|---|---|---|
| Scale | billions make-on-demand + 100Ms in-stock | lead/drug-like focus | ~750M cataloged |
| API host | `cartblanche22.docking.org` | `zinc20.docking.org` | `zinc15.docking.org` |
| Tranches | yes | yes | yes |
| 3D structures | yes | yes | yes |
| Status | current, growing | maintained | legacy |

Query *patterns* are broadly similar across versions; the host and exact grammar differ.

## Further reading

- ZINC wiki: `https://wiki.docking.org/`
- ZINC22 category: `https://wiki.docking.org/index.php/Category:ZINC22`
- SmallWorld: `https://sw.docking.org/` · Arthor: `https://arthor.docking.org/`
