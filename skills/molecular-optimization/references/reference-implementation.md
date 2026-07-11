# Reference Implementation

A dependency-light RDKit reference for the optimization loop: analyze, identify
liabilities, generate candidates by bioisosteric replacement, verify, score, and
iterate. Single-molecule and batch entry points. This is a starting scaffold —
extend the bioisostere library and wire real ADMET endpoints (`admet-prediction`)
for production use.

Requires: `pip install rdkit numpy pandas` (pandas only for batch mode).

```python
#!/usr/bin/env python3
"""Iterative molecular optimization (analyze → liabilities → generate → verify → score → iterate)."""
import json, sys
from rdkit import Chem
from rdkit.Chem import Descriptors, QED, AllChem, DataStructs
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit import RDLogger
RDLogger.logger().setLevel(RDLogger.ERROR)

# Physicochemical bands (extend with predicted hERG/DILI/CYP from admet-prediction).
THRESHOLDS = {
    "MW":   {"min": 150, "max": 500, "severity": "medium"},
    "LogP": {"min": 1.0, "max": 3.0, "severity": "medium"},
    "TPSA": {"min": 20,  "max": 130, "severity": "medium"},
    "HBA":  {"max": 10, "severity": "low"},
    "HBD":  {"max": 5,  "severity": "low"},
    "QED":  {"min": 0.5, "severity": "low"},
}
SEVERITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# (SMARTS/SMILES pattern, replacement, rationale). Match order = priority.
BIOISOSTERES = [
    ("c1ccccc1", "c1ccncc1", "phenyl->pyridine (increase polarity, lower LogP)"),
    ("[cH]",     "n",        "aromatic CH->N (lower LogP)"),
    ("Cl",       "F",        "Cl->F (lower MW and lipophilicity)"),
    ("C(=O)N",   "S(=O)(=O)N","amide->sulfonamide"),
    ("OC",       "O",        "methoxy->hydroxy (lower LogP, add HBD)"),
    ("CC",       "C",        "shorten chain (lower MW/LogP)"),
]

def descriptors(mol):
    return {
        "MW": round(Descriptors.MolWt(mol), 1),
        "LogP": round(Descriptors.MolLogP(mol), 2),
        "TPSA": round(Descriptors.TPSA(mol), 1),
        "HBA": Descriptors.NumHAcceptors(mol),
        "HBD": Descriptors.NumHDonors(mol),
        "RotBonds": Descriptors.NumRotatableBonds(mol),
        "AromaticRings": Descriptors.NumAromaticRings(mol),
        "QED": round(QED.qed(mol), 3),
    }

def scaffold(mol):
    try:
        s = MurckoScaffold.GetScaffoldForMol(mol)
        return Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(s))
    except Exception:
        return None

def tanimoto(a, b):
    fa = AllChem.GetMorganFingerprintAsBitVect(a, 2, nBits=2048)
    fb = AllChem.GetMorganFingerprintAsBitVect(b, 2, nBits=2048)
    return round(DataStructs.TanimotoSimilarity(fa, fb), 4)

def liabilities(desc):
    out = []
    for prop, t in THRESHOLDS.items():
        if prop not in desc:
            continue
        v = desc[prop]
        if "min" in t and v < t["min"]:
            out.append((prop, t["severity"], f"{prop}={v} below {t['min']}"))
        elif "max" in t and v > t["max"]:
            out.append((prop, t["severity"], f"{prop}={v} above {t['max']}"))
    out.sort(key=lambda x: SEVERITY.get(x[1], 99))
    return out

def candidates(smiles, max_candidates=8):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    seen, out = {smiles}, []
    for old, new, why in BIOISOSTERES:
        if len(out) >= max_candidates:
            break
        patt = Chem.MolFromSmarts(old) or Chem.MolFromSmiles(old)
        repl = Chem.MolFromSmiles(new) or Chem.MolFromSmarts(new)
        if patt is None or repl is None or not mol.HasSubstructMatch(patt):
            continue
        for prod in AllChem.ReplaceSubstructs(mol, patt, repl):
            smi = Chem.MolToSmiles(prod)
            if smi not in seen and Chem.MolFromSmiles(smi) is not None:
                seen.add(smi)
                out.append({"smiles": smi, "rationale": why})
    return out[:max_candidates]

def verify(parent, cand_smiles, sim_floor=0.4):
    cand = Chem.MolFromSmiles(cand_smiles)
    if cand is None:
        return {"valid": False, "reason": "unparseable SMILES"}
    sim = tanimoto(parent, cand)
    ps, cs = scaffold(parent), scaffold(cand)
    v = {"valid": True, "similarity": sim,
         "scaffold_preserved": (ps == cs) if ps and cs else None}
    if sim < sim_floor:
        v["warning"] = f"low similarity {sim} — de novo territory, not optimization"
    return v

def score(parent_desc, cand_desc):
    p = {l[0] for l in liabilities(parent_desc)}
    c = {l[0] for l in liabilities(cand_desc)}
    fixed, introduced = p - c, c - p
    return {"score": len(fixed) - 0.5 * len(introduced),
            "fixed": sorted(fixed), "introduced": sorted(introduced)}

def optimize(smiles, max_iterations=3, max_candidates=8):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"invalid input SMILES: {smiles}"}
    parent_desc = descriptors(mol)
    best, best_score, current = None, -float("inf"), Chem.MolToSmiles(mol)
    log = []
    for i in range(max_iterations):
        cur_mol = Chem.MolFromSmiles(current)
        cur_liab = liabilities(descriptors(cur_mol))
        if not cur_liab:
            break
        scored = []
        for c in candidates(current, max_candidates):
            v = verify(mol, c["smiles"])
            if not v["valid"] or v.get("warning"):
                continue
            cd = descriptors(Chem.MolFromSmiles(c["smiles"]))
            s = score(parent_desc, cd)
            scored.append({**c, "descriptors": cd, "verification": v, "scoring": s})
        scored.sort(key=lambda x: x["scoring"]["score"], reverse=True)
        log.append({"iteration": i + 1, "liabilities": cur_liab,
                    "candidates": len(scored), "top": scored[:3]})
        if scored and scored[0]["scoring"]["score"] > best_score:
            best, best_score, current = scored[0], scored[0]["scoring"]["score"], scored[0]["smiles"]
        else:
            break
    return {"input": Chem.MolToSmiles(mol), "input_descriptors": parent_desc,
            "input_liabilities": liabilities(parent_desc), "iterations": log,
            "best": best, "best_score": best_score}

if __name__ == "__main__":
    smi = sys.argv[1] if len(sys.argv) > 1 else "c1ccc(NC(=O)c2ccccc2Cl)cc1"
    print(json.dumps(optimize(smi), indent=2))
```

## Notes

- **Bioisostere library is a stub.** Six rules cover common LogP/MW edits. For
  real work, expand it (or drive edits from `admet-reasoning`'s cause→fix
  mapping) and add functional-group and ring edits.
- **ADMET endpoints.** hERG / DILI / CYP are omitted from `THRESHOLDS` above
  because they need a predictor. Add them by scoring each molecule with
  `admet-prediction` and folding the results into `liabilities()`.
- **`ReplaceSubstructs` returns a tuple** of product mols (one per match site);
  this reference canonicalizes and de-dupes them.
- **The similarity floor doubles as the verify gate** — candidates below it are
  dropped rather than scored, so the loop cannot silently wander into de novo
  design.
- **Batch mode:** read a CSV with pandas, call `optimize()` per row inside a
  `try/except`, and append each result to a list; one bad SMILES must not abort
  the run.
