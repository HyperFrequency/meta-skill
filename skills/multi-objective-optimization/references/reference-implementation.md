# Reference Implementation

A runnable, dependency-light Pareto optimizer over RDKit for
`multi-objective-optimization`. It parses objectives, generates candidates by
bioisosteric replacement, scores each against every objective as a gap, extracts
the non-dominated front, and emits JSON. Two modes: `optimize` (grow a candidate
set from one parent SMILES) and `analyze` (rank an existing set from a CSV).

Requires `rdkit`, `numpy`, and (for `--input`) `pandas`.

```python
#!/usr/bin/env python3
"""Pareto-aware multi-objective molecular optimization over RDKit."""

import argparse, json, sys

try:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import Descriptors, QED, AllChem, DataStructs
    RDLogger.logger().setLevel(RDLogger.ERROR)
except ImportError:
    sys.exit("rdkit is required (pip install rdkit)")

# --- Per-molecule property functions. Extend this map to add objectives. ---
PROPERTY_FUNCS = {
    "MW": Descriptors.MolWt,
    "LogP": Descriptors.MolLogP,
    "TPSA": Descriptors.TPSA,
    "HBA": lambda m: float(Descriptors.NumHAcceptors(m)),
    "HBD": lambda m: float(Descriptors.NumHDonors(m)),
    "RotBonds": lambda m: float(Descriptors.NumRotatableBonds(m)),
    "QED": QED.qed,
    "AromaticRings": lambda m: float(Descriptors.NumAromaticRings(m)),
    "FractionCSP3": Descriptors.FractionCSP3,
    "NumRings": lambda m: float(Descriptors.RingCount(m)),
}

# --- Bioisosteric edits used to grow candidates in optimize mode. ---
# (query pattern, replacement, human-readable rationale)
BIOISOSTERES = [
    ("[cH]", "[n]", "C→N in ring"),
    ("Cl", "F", "Cl→F"),
    ("OC", "O", "OMe→OH"),
    ("c1ccccc1", "c1ccncc1", "phenyl→pyridine"),
    ("C(=O)N", "S(=O)(=O)N", "amide→sulfonamide"),
]


def parse_objectives(spec):
    """'LogP:minimize:3.0,TPSA:range:20:130' -> list of objective dicts."""
    objectives = []
    for item in spec.split(","):
        parts = [p.strip() for p in item.split(":")]
        if len(parts) == 3:
            prop, direction, target = parts
            objectives.append({"property": prop, "direction": direction,
                               "target": float(target)})
        elif len(parts) == 4:  # range: NAME:range:lo:hi
            prop, _, lo, hi = parts
            objectives.append({"property": prop, "direction": "range",
                               "target_min": float(lo), "target_max": float(hi)})
    return objectives


def gap(value, obj):
    """One-sided hinge: 0 means the objective is satisfied, higher is worse."""
    d = obj["direction"]
    if d == "minimize":
        return max(0.0, value - obj["target"])
    if d == "maximize":
        return max(0.0, obj["target"] - value)
    if d == "range":
        if value < obj["target_min"]:
            return obj["target_min"] - value
        if value > obj["target_max"]:
            return value - obj["target_max"]
        return 0.0
    return abs(value - obj.get("target", value))


def evaluate(mol, objectives):
    """Return (properties, gaps) dicts keyed by property name."""
    props, gaps = {}, {}
    for obj in objectives:
        name = obj["property"]
        fn = PROPERTY_FUNCS.get(name)
        if fn is None:
            continue
        val = fn(mol)
        props[name] = round(val, 4)
        gaps[name] = round(gap(val, obj), 4)
    return props, gaps


def dominates(a, b):
    """True if gap-vector a Pareto-dominates b (<= on all, < on at least one)."""
    keys = a.keys()
    better = False
    for k in keys:
        if a[k] > b[k]:
            return False
        if a[k] < b[k]:
            better = True
    return better


def pareto_front(scored):
    """Split scored candidates into (non-dominated front, dominated set)."""
    front, dominated = [], []
    for i, ci in enumerate(scored):
        if any(dominates(cj["gaps"], ci["gaps"])
               for j, cj in enumerate(scored) if i != j):
            dominated.append(ci)
        else:
            front.append(ci)
    return front, dominated


def generate(smiles, limit=16):
    """Grow unique, valid candidates from one parent via bioisosteric edits."""
    parent = Chem.MolFromSmiles(smiles)
    if parent is None:
        return []
    out, seen = [], set()
    for query, repl, why in BIOISOSTERES:
        if len(out) >= limit:
            break
        q = Chem.MolFromSmarts(query) or Chem.MolFromSmiles(query)
        r = Chem.MolFromSmiles(repl) or Chem.MolFromSmarts(repl)
        if q is None or r is None or not parent.HasSubstructMatch(q):
            continue
        for prod in AllChem.ReplaceSubstructs(parent, q, r):
            smi = Chem.MolToSmiles(prod)
            if smi and smi != smiles and smi not in seen \
                    and Chem.MolFromSmiles(smi) is not None:
                seen.add(smi)
                out.append({"smiles": smi, "rationale": why})
    return out[:limit]


def tanimoto(ref_smiles, mol):
    ref = Chem.MolFromSmiles(ref_smiles)
    f1 = AllChem.GetMorganFingerprintAsBitVect(ref, 2, nBits=2048)
    f2 = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    return round(DataStructs.TanimotoSimilarity(f1, f2), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smiles", help="parent SMILES (optimize mode)")
    ap.add_argument("--input", help="CSV of candidates (analyze mode)")
    ap.add_argument("--smiles-col", default="SMILES")
    ap.add_argument("--objectives", required=True,
                    help='e.g. "LogP:minimize:3.0,QED:maximize:0.5"')
    ap.add_argument("--candidates", type=int, default=16)
    ap.add_argument("--mode", choices=["optimize", "analyze"], default="optimize")
    ap.add_argument("--output", default="pareto_results.json")
    args = ap.parse_args()

    objectives = parse_objectives(args.objectives)
    if not objectives:
        sys.exit("no valid objectives parsed")

    if args.mode == "optimize" and args.smiles:
        if Chem.MolFromSmiles(args.smiles) is None:
            sys.exit(f"invalid SMILES: {args.smiles}")
        pool = [{"smiles": args.smiles, "is_reference": True}] \
            + generate(args.smiles, args.candidates)
    elif args.input:
        import pandas as pd
        pool = [{"smiles": s} for s in pd.read_csv(args.input)[args.smiles_col]]
    else:
        sys.exit("provide --smiles (optimize) or --input (analyze)")

    scored = []
    for entry in pool:
        mol = Chem.MolFromSmiles(entry["smiles"])
        if mol is None:
            continue
        props, gaps = evaluate(mol, objectives)
        scored.append({
            "smiles": Chem.MolToSmiles(mol),
            "properties": props,
            "gaps": gaps,
            "total_gap": round(sum(gaps.values()), 4),
            "similarity": tanimoto(args.smiles, mol) if args.smiles else None,
            "rationale": entry.get("rationale", ""),
            "is_reference": entry.get("is_reference", False),
        })

    front, dominated = pareto_front(scored)
    front.sort(key=lambda x: x["total_gap"])  # presentation order only

    result = {
        "objectives": objectives,
        "total_evaluated": len(scored),
        "pareto_front_size": len(front),
        "pareto_front": front,
        "dominated": dominated[:10],
    }
    with open(args.output, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"front={len(front)}/{len(scored)} -> {args.output}")


if __name__ == "__main__":
    main()
```

## CLI usage

Optimize one molecule against three objectives (minimize LogP toward 3, maximize
QED toward 0.5, keep TPSA in [20, 130]):

```bash
python pareto_optimize.py \
  --smiles "c1ccc(NC(=O)c2ccccc2Cl)cc1" \
  --objectives "LogP:minimize:3.0,QED:maximize:0.5,TPSA:range:20:130" \
  --candidates 16 --output pareto_results.json
```

Rank an existing candidate set from a CSV (column `SMILES`):

```bash
python pareto_optimize.py \
  --input candidates.csv --mode analyze \
  --objectives "LogP:minimize:3.0,QED:maximize:0.5" \
  --output pareto_front.json
```

## Output JSON

```json
{
  "objectives": [{"property": "LogP", "direction": "minimize", "target": 3.0}],
  "total_evaluated": 12,
  "pareto_front_size": 4,
  "pareto_front": [
    {
      "smiles": "...",
      "properties": {"LogP": 2.8, "QED": 0.61},
      "gaps": {"LogP": 0.0, "QED": 0.0},
      "total_gap": 0.0,
      "similarity": 0.72,
      "rationale": "Cl→F",
      "is_reference": false
    }
  ],
  "dominated": []
}
```

`pareto_front` is the deliverable (every non-dominated trade-off, sorted by
`total_gap` for readability). `dominated` is truncated to 10 for reference.
`similarity` is `null` in analyze mode when no parent is supplied.

## Wiring in real ADMET endpoints

To optimize a measured or ML-predicted endpoint (hERG, solubility, clearance)
rather than a physicochemical proxy, add it to `PROPERTY_FUNCS` as a function
that maps an RDKit `Mol` to a scalar — typically by calling `admet-prediction`
and returning the endpoint value. Everything downstream (gap, dominance, front)
is unchanged. Extend `BIOISOSTERES` to broaden the reachable chemical space.
