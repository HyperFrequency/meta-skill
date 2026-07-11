# Reference Implementation

A runnable `retrieve_analogs.py` for molecular RAG over ChEMBL. Rewritten from the
openscience original with the correctness fixes called out in
`references/chembl-api.md`: SMILES URL-encoding, the 40% threshold floor, and
retry/backoff on throttling. Requires `rdkit` and `requests`.

```bash
pip install rdkit requests   # modern wheels ship as `rdkit`, not `rdkit-pypi`
```

## CLI

| Flag | Default | Meaning |
|------|---------|---------|
| `--smiles` | (required) | query SMILES |
| `--similarity-threshold` | `0.6` | Tanimoto fraction in `[0.4, 1.0]` (clamped) |
| `--target` | `None` | restrict to activity vs this `CHEMBL…` target |
| `--include-activities` | off | attach measured bioactivities to each analog |
| `--max-results` | `20` | number of analogs to return |
| `--output` | `analogs.json` | output path |

## Output schema

```json
{
  "query": "O=C(Nc1ccccc1)c1ccccc1Cl",
  "threshold": 0.6,
  "target": null,
  "num_results": 12,
  "analogs": [
    {
      "chembl_id": "CHEMBL153534",
      "smiles": "O=C(Nc1ccccc1)c1ccccc1F",
      "pref_name": null,
      "similarity": 0.87,
      "mw": 231.24, "logp": 3.1, "hba": 2, "hbd": 1, "psa": 29.1,
      "activities": [
        {"target": "...", "target_id": "CHEMBL301",
         "type": "IC50", "value": "12", "units": "nM",
         "relation": "=", "pchembl_value": "7.92"}
      ]
    }
  ]
}
```

`activities` is present only with `--include-activities` (property mode) or always
(target mode). Invalid query SMILES exits non-zero with a message rather than
writing a file.

## Source

```python
#!/usr/bin/env python3
"""Molecular RAG — retrieve structurally similar compounds with measured data
from ChEMBL, to ground molecular property predictions. After MolRAG (Xian 2025)."""

import argparse, json, sys, time
from urllib.parse import quote

from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
from rdkit import RDLogger
RDLogger.logger().setLevel(RDLogger.ERROR)
import requests

CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"


def ecfp4(smiles, n_bits=2048):
    mol = Chem.MolFromSmiles(smiles)
    return None if mol is None else AllChem.GetMorganFingerprintAsBitVect(
        mol, radius=2, nBits=n_bits)


def _get(url, params=None, tries=4):
    """GET with backoff on throttling / transient server errors."""
    for attempt in range(tries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)          # exponential backoff
                continue
            print(f"ChEMBL {resp.status_code}: {url}", file=sys.stderr)
            return None
        except requests.RequestException as exc:
            print(f"request error: {exc}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def similarity_search(smiles, pct, limit):
    """ChEMBL similarity search. `pct` is an integer Tanimoto percentage >= 40.
    SMILES is URL-encoded so charges/bonds/ring markers survive the path."""
    url = f"{CHEMBL}/similarity/{quote(smiles, safe='')}/{pct}.json"
    data = _get(url, {"limit": limit})
    return (data or {}).get("molecules", [])


def activities(chembl_id, target=None, limit=50):
    params = {"molecule_chembl_id": chembl_id, "limit": limit, "format": "json"}
    if target:
        params["target_chembl_id"] = target
    data = _get(f"{CHEMBL}/activity.json", params)
    return (data or {}).get("activities", [])


def summarize_activity(a):
    return {
        "target": a.get("target_pref_name"),
        "target_id": a.get("target_chembl_id"),
        "type": a.get("standard_type"),
        "value": a.get("standard_value"),
        "units": a.get("standard_units"),
        "relation": a.get("standard_relation"),
        "pchembl_value": a.get("pchembl_value"),
    }


def main():
    p = argparse.ArgumentParser(description="Retrieve similar compounds from ChEMBL")
    p.add_argument("--smiles", required=True)
    p.add_argument("--similarity-threshold", type=float, default=0.6)
    p.add_argument("--target", default=None)
    p.add_argument("--include-activities", action="store_true")
    p.add_argument("--max-results", type=int, default=20)
    p.add_argument("--output", default="analogs.json")
    args = p.parse_args()

    mol = Chem.MolFromSmiles(args.smiles)
    if mol is None:
        print(f"Invalid SMILES: {args.smiles}", file=sys.stderr)
        return 1
    query = Chem.MolToSmiles(mol)
    query_fp = ecfp4(query)

    # ChEMBL requires an integer percentage with a hard floor of 40.
    pct = max(40, min(100, int(args.similarity_threshold * 100)))
    if int(args.similarity_threshold * 100) < 40:
        print("threshold below ChEMBL minimum 0.40 — clamped to 0.40",
              file=sys.stderr)

    print(f"Query: {query}  threshold={pct}%"
          + (f"  target={args.target}" if args.target else ""))
    hits = similarity_search(query, pct, args.max_results * (2 if args.target else 1))

    results = []
    for m in hits:
        smi = (m.get("molecule_structures") or {}).get("canonical_smiles")
        fp = ecfp4(smi) if smi else None
        if fp is None:
            continue
        props = m.get("molecule_properties") or {}
        entry = {
            "chembl_id": m.get("molecule_chembl_id"),
            "smiles": smi,
            "pref_name": m.get("pref_name"),
            "similarity": round(DataStructs.TanimotoSimilarity(query_fp, fp), 4),
            "mw": props.get("full_mwt"), "logp": props.get("alogp"),
            "hba": props.get("hba"), "hbd": props.get("hbd"), "psa": props.get("psa"),
        }
        if args.target:
            acts = activities(entry["chembl_id"], target=args.target, limit=100)
            if not acts:
                continue
            entry["activities"] = [summarize_activity(a) for a in acts]
            time.sleep(0.2)
        elif args.include_activities:
            acts = activities(entry["chembl_id"], limit=20)
            entry["activities"] = [summarize_activity(a) for a in acts[:10]]
            time.sleep(0.2)
        results.append(entry)
        if len(results) >= args.max_results:
            break

    results.sort(key=lambda r: r.get("similarity", 0), reverse=True)
    out = {"query": query, "threshold": args.similarity_threshold,
           "target": args.target, "num_results": len(results), "analogs": results}

    print(f"Found {len(results)} analogs")
    for i, r in enumerate(results[:10], 1):
        print(f"  {i}. {r.get('pref_name') or r['chembl_id']} "
              f"(sim={r['similarity']}) {r['smiles'][:50]}")
        for a in (r.get("activities") or [])[:3]:
            print(f"     {a['type']}: {a['relation'] or '='} {a['value']} {a['units']}")

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Worked examples

```bash
# lead-optimization SAR context around a chlorobenzamide anilide
python retrieve_analogs.py --smiles "O=C(Nc1ccccc1)c1ccccc1Cl" \
    --include-activities --similarity-threshold 0.6 --output sar_context.json

# novelty check: is this generated molecule already known?
python retrieve_analogs.py --smiles "<generated SMILES>" \
    --similarity-threshold 0.9 --max-results 5 --output novelty.json
#   -> num_results 0  => structurally novel vs ChEMBL
#   -> a ~1.0 similarity hit => the compound (or a salt/stereo variant) is known

# plausible potency window against a named target
python retrieve_analogs.py --smiles "O=C(Nc1ccccc1)c1ccccc1Cl" \
    --target CHEMBL301 --output target_analogs.json
```

## Differences from the openscience original

- SMILES are `urllib.parse.quote`-encoded before path interpolation (the original
  broke on charged/ring-bond SMILES).
- Similarity threshold is clamped to ChEMBL's 40% floor with a warning instead of
  silently issuing an invalid request.
- All HTTP goes through one `_get` helper with exponential backoff on 429/5xx.
- `pchembl_value` and `standard_relation` are carried through so downstream
  reasoning can normalize potency and respect censored (`>`/`<`) values.
