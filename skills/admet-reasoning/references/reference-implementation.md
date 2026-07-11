# Reference Implementation

A self-contained RDKit script that computes physicochemical descriptors, checks
them against the thresholds in `physchem-liabilities.md`, runs the SMARTS alerts
from `structural-alerts.md`, and emits a structured JSON liability report. Single
molecule or batch CSV.

Save as `reason_admet.py`. Requires `rdkit` (modern conda/pip wheels are the
`rdkit` package; the old `rdkit-pypi` name is deprecated), plus `pandas` for
batch mode.

```python
#!/usr/bin/env python3
"""ADMET reasoning: map liabilities to structural cause, mechanism, and fix.

Usage:
    python reason_admet.py --smiles "Nc1ccc(cc1)[N+](=O)[O-]" --output report.json
    python reason_admet.py --smiles "CCN1CCN(CC1)c1ccccc1" --endpoints hERG,CYP
    python reason_admet.py --input compounds.csv --output liabilities.json
"""

import argparse
import json
import sys

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, QED
    from rdkit import RDLogger
    RDLogger.logger().setLevel(RDLogger.ERROR)
except ImportError:
    print("Error: rdkit is required (pip install rdkit).", file=sys.stderr)
    sys.exit(1)


# Physicochemical thresholds. See references/physchem-liabilities.md.
PROPERTY_THRESHOLDS = {
    "LogP":     {"min": 1.0, "max": 3.0, "severity": "medium"},
    "LogS_est": {"min": -4.0,            "severity": "medium"},
    "MW":       {"min": 150, "max": 500, "severity": "medium"},
    "TPSA":     {"min": 20,  "max": 130, "severity": "medium"},
    "QED":      {"min": 0.5,             "severity": "low"},
    "HBA":      {"max": 10,              "severity": "low"},
    "HBD":      {"max": 5,               "severity": "low"},
    "RotBonds": {"max": 10,              "severity": "low"},
}

# (SMARTS, endpoint, structural_cause, mechanism, suggested_fix).
# See references/structural-alerts.md for the annotated catalogue.
STRUCTURAL_ALERTS = [
    ("[NX3;H1]1CCNCC1", "hERG", "Basic piperazine (pKa ~8.5)",
     "Protonated amine binds the hERG inner vestibule via cation-pi interaction",
     "Replace piperazine with morpholine to keep the H-bond acceptor while dropping basicity"),
    ("[NX3;H1]1CCCCC1", "hERG", "Basic piperidine",
     "Lipophilic basic amine is a classic hERG pharmacophore blocking the K+ channel",
     "Reduce basicity: N-acylation, swap to tetrahydropyran, or add a polar substituent"),
    ("[nH]1cccc1", "hERG", "Electron-rich pyrrole-type heteroaromatic",
     "Electron-rich heteroaromatics can contact hERG channel aromatic residues",
     "N-methylation or ring expansion"),

    ("[N+](=O)[O-]", "DILI", "Nitro group",
     "Nitroreduction to nitroso and hydroxylamine metabolites drives oxidative stress",
     "Replace nitro with cyano, trifluoromethyl, or methylsulfonyl"),
    ("c1ccc2c(c1)ccc1ccccc12", "DILI", "Anthracene / extended PAH",
     "CYP-mediated oxidation to reactive epoxides damages hepatocytes",
     "Break into monocyclic systems or add polar substituents to block metabolic sites"),
    ("O=c1cc[nH]c(=O)c1", "DILI", "Pyrimidinedione / uracil-type dione (broad alert)",
     "Proposed CYP bioactivation to reactive epoxide intermediates",
     "Bioisosteric replacement of the dione motif"),

    ("c1cnc[nH]1", "CYP", "Unsubstituted imidazole (heme-coordinating azole)",
     "Azole nitrogen coordinates the CYP heme iron, blocking the active site",
     "N-methylation or replacement with a non-coordinating heterocycle"),
    ("c1ccc(-c2ccccc2)cc1", "CYP", "Biphenyl",
     "Planar lipophilic aromatics fit the CYP3A4 hydrophobic channel",
     "Introduce an sp3 carbon to break planarity, or add a polar group"),

    ("[NX3;H2]c1ccccc1", "AMES", "Aromatic amine (aniline)",
     "CYP1A2 N-hydroxylation forms an electrophilic nitrenium ion that adducts DNA",
     "Acetylate (amide), N-methylate, or replace with a non-amino substituent"),
    ("[NX3;H2]c1ccc(cc1)[N+](=O)[O-]", "AMES", "para-Nitroaniline",
     "Nitroreduction plus amine activation yields a potent DNA-reactive species",
     "Remove either the nitro or the amino group; use a non-reactive bioisostere"),

    ("c1ccc2ccccc2c1", "Solubility", "Fused aromatic rings",
     "Extended flat aromatics raise crystal-packing energy and lower aqueous solubility",
     "Disrupt planarity with sp3 centres, cut ring count, or add solubilizing groups"),
]

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def compute_properties(mol):
    """Descriptors plus an ESOL (Delaney) LogS estimate."""
    props = {
        "MW":       round(Descriptors.MolWt(mol), 1),
        "LogP":     round(Descriptors.MolLogP(mol), 2),
        "TPSA":     round(Descriptors.TPSA(mol), 1),
        "HBA":      Descriptors.NumHAcceptors(mol),
        "HBD":      Descriptors.NumHDonors(mol),
        "RotBonds": Descriptors.NumRotatableBonds(mol),
        "QED":      round(QED.qed(mol), 3),
        "AromaticRings": Descriptors.NumAromaticRings(mol),
        "FractionCSP3":  round(Descriptors.FractionCSP3(mol), 3),
        "HeavyAtoms":    mol.GetNumHeavyAtoms(),
    }
    # ESOL: aromatic proportion = aromatic heavy atoms / heavy atoms.
    heavy = props["HeavyAtoms"]
    aromatic_atoms = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic())
    aromatic_proportion = aromatic_atoms / heavy if heavy else 0.0
    props["LogS_est"] = round(
        0.16 - 0.63 * props["LogP"] - 0.0062 * props["MW"]
        + 0.066 * props["RotBonds"] - 0.74 * aromatic_proportion,
        2,
    )
    return props


def check_thresholds(props):
    """Physicochemical liabilities, sorted most-severe first."""
    liabilities = []
    for name, rule in PROPERTY_THRESHOLDS.items():
        value = props.get(name)
        if value is None:
            continue
        violation = None
        if "min" in rule and value < rule["min"]:
            violation = f"Below minimum ({rule['min']})"
        elif "max" in rule and value > rule["max"]:
            violation = f"Above maximum ({rule['max']})"
        if violation:
            liabilities.append({
                "property": name, "value": value,
                "violation": violation, "severity": rule["severity"],
            })
    liabilities.sort(key=lambda x: _SEVERITY_RANK.get(x["severity"], 99))
    return liabilities


def check_structural_alerts(mol, endpoints=None):
    """Match the SMARTS catalogue; optionally restrict to given endpoints."""
    hits = []
    for smarts, endpoint, cause, mechanism, fix in STRUCTURAL_ALERTS:
        if endpoints and endpoint not in endpoints:
            continue
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is None:
            continue  # malformed pattern — skip rather than crash the batch
        if mol.HasSubstructMatch(pattern):
            hits.append({
                "endpoint": endpoint,
                "structural_cause": cause,
                "mechanism": mechanism,
                "suggested_fix": fix,
                "smarts": smarts,
                "num_matches": len(mol.GetSubstructMatches(pattern)),
            })
    return hits


def generate_report(smiles, endpoints=None):
    """Full liability report for one SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": f"Invalid SMILES: {smiles}"}

    props = compute_properties(mol)
    threshold_liabilities = check_thresholds(props)
    structural_alerts = check_structural_alerts(mol, endpoints)
    total = len(threshold_liabilities) + len(structural_alerts)

    if total == 0:
        assessment = "CLEAN - no ADMET liabilities detected"
    elif total <= 2:
        assessment = "MINOR CONCERNS - addressable with targeted modifications"
    elif total <= 4:
        assessment = "MODERATE CONCERNS - optimization needed before advancement"
    else:
        assessment = "SIGNIFICANT CONCERNS - major redesign may be required"

    return {
        "smiles": Chem.MolToSmiles(mol),
        "properties": props,
        "threshold_liabilities": threshold_liabilities,
        "structural_alerts": structural_alerts,
        "total_liabilities": total,
        "assessment": assessment,
    }


def print_summary(report):
    print("=" * 60)
    print("ADMET REASONING REPORT")
    print("=" * 60)
    print(f"Molecule:   {report.get('smiles', 'N/A')}")
    print(f"Assessment: {report.get('assessment', 'N/A')}")
    for l in report.get("threshold_liabilities", []):
        print(f"  [{l['severity'].upper()}] {l['property']} = {l['value']} - {l['violation']}")
    for a in report.get("structural_alerts", []):
        print(f"\n  [{a['endpoint']}] {a['structural_cause']}")
        print(f"    Mechanism:     {a['mechanism']}")
        print(f"    Suggested fix: {a['suggested_fix']}")


def main():
    ap = argparse.ArgumentParser(description="ADMET reasoning with mechanistic explanations")
    ap.add_argument("--smiles", help="Single input SMILES")
    ap.add_argument("--input", help="Input CSV file (batch mode)")
    ap.add_argument("--smiles-col", default="SMILES", help="SMILES column name for --input")
    ap.add_argument("--endpoints", help="Restrict to endpoints, comma-separated (hERG,DILI,CYP,AMES,Solubility)")
    ap.add_argument("--output", default="report.json")
    args = ap.parse_args()

    endpoints = args.endpoints.split(",") if args.endpoints else None

    if args.smiles:
        report = generate_report(args.smiles, endpoints)
        print_summary(report)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nFull report -> {args.output}")
        return 0 if "error" not in report else 1

    if args.input:
        import pandas as pd
        df = pd.read_csv(args.input)
        reports = [generate_report(smi, endpoints) for smi in df[args.smiles_col]]
        with open(args.output, "w") as f:
            json.dump(reports, f, indent=2)
        flagged = sum(1 for r in reports if r.get("total_liabilities", 0) > 0)
        print(f"Analyzed {len(reports)} molecules: {flagged} with liabilities -> {args.output}")
        return 0

    print("Error: provide --smiles or --input", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

## Report shape

```json
{
  "smiles": "Nc1ccc([N+](=O)[O-])cc1",
  "properties": {"MW": 138.1, "LogP": 1.39, "TPSA": 71.9, "QED": 0.55, "...": "..."},
  "threshold_liabilities": [],
  "structural_alerts": [
    {"endpoint": "AMES", "structural_cause": "para-Nitroaniline",
     "mechanism": "Nitroreduction plus amine activation yields a potent DNA-reactive species",
     "suggested_fix": "Remove either the nitro or the amino group; use a non-reactive bioisostere",
     "smarts": "[NX3;H2]c1ccc(cc1)[N+](=O)[O-]", "num_matches": 1}
  ],
  "total_liabilities": 1,
  "assessment": "MINOR CONCERNS - addressable with targeted modifications"
}
```

## Notes and edge cases

- **Invalid SMILES** return `{"error": ...}` instead of raising, so a bad row
  never aborts a batch. Filter these before aggregating counts.
- **`--endpoints`** filters structural alerts only; physicochemical thresholds
  are always evaluated.
- The banding in `assessment` is a coarse triage signal — a single high-severity
  genotox alert outweighs several low-severity physchem violations. Read the
  itemized `structural_alerts`, do not stop at the headline.
- This is a heuristic reference, not a validated predictor. See the false-positive
  caveats in `structural-alerts.md` and the boundaries in `../SKILL.md`.
