# Medchem API Reference

Module-by-module reference for `medchem`, plus DataFrame integration and a
batch-filtering pattern.

> **Verify before relying on it.** The signatures below are documented at
> capability level and reflect a snapshot of the library's public surface. Exact
> function names, keyword arguments, and return-dict keys drift across releases —
> confirm against https://medchem-docs.datamol.io and
> https://github.com/datamol-io/medchem for the version you have installed.
> Across every filter class, the batch call convention is
> `filter(mols=..., n_jobs=1, progress=False)`; `n_jobs=-1` uses all cores.

---

## `medchem.rules`

### `RuleFilters`
Apply multiple named rules over a molecule list.

```python
RuleFilters(rule_list: list[str])
# call:
rfilter(mols: list[Chem.Mol], n_jobs: int = 1, progress: bool = False) -> dict
```

`rule_list` names any of the `basic_rules` functions (`"rule_of_five"`,
`"rule_of_cns"`, `"rule_of_veber"`, `"rule_of_oprea"`,
`"rule_of_leadlike_soft"`, `"rule_of_leadlike_strict"`, `"rule_of_three"`,
`"rule_of_reos"`, `"rule_of_drug"`, `"golden_triangle"`, `"pains_filter"`).
Returns per-rule pass/fail results keyed by rule name. See
[rules-catalog.md](rules-catalog.md) for each rule's thresholds and citations.

### `medchem.rules.basic_rules`
Individual rule functions, each `(mol: str | Chem.Mol) -> bool`:
`rule_of_five`, `rule_of_three`, `rule_of_oprea`, `rule_of_cns`,
`rule_of_leadlike_soft`, `rule_of_leadlike_strict`, `rule_of_veber`,
`rule_of_reos`, `rule_of_drug`, `golden_triangle`, `pains_filter`.

Note the sign convention: `pains_filter` returns **True when the molecule is
clean** (no PAINS substructure found).

---

## `medchem.structural`

### `CommonAlertsFilters`
```python
CommonAlertsFilters()
__call__(mols, n_jobs=1, progress=False) -> list[dict]
check_mol(mol: Chem.Mol) -> tuple[bool, list[str]]
```
Batch result per molecule:
```python
{"has_alerts": True, "alert_details": ["reactive_epoxide", "metabolic_hydrazine"], "num_alerts": 2}
```
`check_mol` returns `(has_alerts, [alert_names])` for a single molecule.

### `NIBRFilters`
```python
NIBRFilters()
__call__(mols, n_jobs=1, progress=False) -> list[bool]   # True = passes
```

### `LillyDemeritsFilters`
```python
LillyDemeritsFilters()
__call__(mols, n_jobs=1, progress=False) -> list[dict]
```
Batch result per molecule:
```python
{"demerits": 35, "passes": True,  # True when demerits <= 100
 "matched_patterns": [{"pattern": "phenolic_ester", "demerits": 20},
                      {"pattern": "aniline_derivative", "demerits": 15}]}
```

---

## `medchem.functional`

High-level one-shot wrappers over the filter classes — convenient when you do not
need to hold a reusable filter object. Confirm the exact names in your version;
the module exposes NIBR, common-alert, and Lilly-demerit filters plus rule and
chemical-group helpers, each taking `(mols, n_jobs=1)`.

```python
ok = mc.functional.nibr_filter(mols=mols, n_jobs=-1)             # list[bool]
alerts = mc.functional.common_alerts_filter(mols=mols, n_jobs=-1)  # list[dict]
```

---

## `medchem.groups`

### `ChemicalGroup`
```python
ChemicalGroup(groups: list[str], custom_smarts: dict[str, str] | None = None)
has_match(mols: list[Chem.Mol]) -> list[bool]
get_matches(mol: Chem.Mol) -> dict[str, list[tuple]]        # group -> atom-index tuples
get_all_matches(mols: list[Chem.Mol]) -> list[dict]
```
Predefined groups: `"hinge_binders"`, `"phosphate_binders"`,
`"michael_acceptors"`, `"reactive_groups"` (see
[rules-catalog.md](rules-catalog.md)). Add custom SMARTS alongside:

```python
group = mc.groups.ChemicalGroup(
    groups=["hinge_binders"],
    custom_smarts={"tfmk_warhead": "[C;H0](=O)C(F)(F)F"},   # trifluoromethyl ketone
)
```

---

## `medchem.catalogs`

### `NamedCatalogs`
Access curated substructure catalogs (`"functional_groups"`,
`"protecting_groups"`, `"reagents"`, `"fragments"`):

```python
catalog = mc.catalogs.NamedCatalogs.get("functional_groups")
matches = catalog.get_matches(mol)
```

---

## `medchem.complexity`

```python
calculate_complexity(mol: Chem.Mol, method: str = "bertz") -> float   # higher = more complex
ComplexityFilter(max_complexity: float, method: str = "bertz")
__call__(mols, n_jobs=1) -> list[bool]
```
`method` ∈ `{"bertz", "whitlock", "barone"}`. Complexity is a rough
synthetic-accessibility proxy — cap it in lead-opt/fragment stacks.

---

## `medchem.constraints`

### `Constraints`
```python
Constraints(
    mw_range: tuple[float, float] | None = None,
    logp_range: tuple[float, float] | None = None,
    tpsa_max: float | None = None,
    tpsa_range: tuple[float, float] | None = None,
    hbd_max: int | None = None,
    hba_max: int | None = None,
    rotatable_bonds_max: int | None = None,
    rings_range: tuple[int, int] | None = None,
    aromatic_rings_max: int | None = None,
)
__call__(mols, n_jobs=1) -> list[dict]   # {"passes": bool, "violations": [names]}
```
All parameters optional — set only the constraints you need.

---

## `medchem.query`

A boolean query language that combines rules, alerts, and property comparisons in
one expression. Operators `AND` / `OR` / `NOT`; comparisons `<`, `>`, `<=`, `>=`,
`==`, `!=`; properties `complexity`, `lilly_demerits`, `mw`, `logp`, `tpsa`;
rule/filter tokens like `rule_of_five`, `common_alerts`, `pains_filter`.

```python
query = mc.query.parse("rule_of_five AND NOT common_alerts")
results = query.apply(mols=mols, n_jobs=-1)   # list[bool]
```
More examples: `"rule_of_cns AND complexity < 400"`,
`"(rule_of_five OR rule_of_oprea) AND NOT pains_filter"`.

---

## `medchem.utils`

```python
batch_process(mols, func, n_jobs=1, progress=False, batch_size=None) -> list
standardize_mol(mol: Chem.Mol) -> Chem.Mol   # sanitize + neutralize charges, etc.
```

---

## DataFrame integration

```python
import pandas as pd
import datamol as dm
import medchem as mc

df = pd.read_csv("compounds.csv")
df["mol"] = df["smiles"].apply(dm.to_mol)
df = df[df["mol"].notnull()].reset_index(drop=True)   # drop unparseable rows

rfilter = mc.rules.RuleFilters(rule_list=["rule_of_five", "rule_of_cns"])
results = rfilter(mols=df["mol"].tolist(), n_jobs=-1, progress=True)

df["passes_ro5"] = [r["rule_of_five"] for r in results]
df["passes_cns"] = [r["rule_of_cns"] for r in results]
drug_like = df[df["passes_ro5"] & df["passes_cns"]]
```

---

## Combining several filters

```python
rule_ok  = mc.rules.RuleFilters(rule_list=["rule_of_five"])(mols, n_jobs=-1)
alerts   = mc.structural.CommonAlertsFilters()(mols, n_jobs=-1)
lilly    = mc.structural.LillyDemeritsFilters()(mols, n_jobs=-1)

keep = [
    m for i, m in enumerate(mols)
    if rule_ok[i]["rule_of_five"]
    and not alerts[i]["has_alerts"]
    and lilly[i]["passes"]
]
```

---

## Batch-filtering CLI pattern

A reusable script for filtering a library from the command line follows this
shape. It loads structures (CSV/TSV/SDF/plain-SMILES), drops invalid molecules,
applies the requested filter stack, writes a results CSV, and prints per-filter
pass rates.

```python
import argparse, sys
from pathlib import Path
import pandas as pd, datamol as dm, medchem as mc
from rdkit import Chem

def load(path: Path, smiles_col: str = "smiles"):
    suffix = path.suffix.lower()
    if suffix == ".sdf":
        mols = [m for m in Chem.SDMolSupplier(str(path)) if m is not None]
        df = pd.DataFrame({"smiles": [Chem.MolToSmiles(m) for m in mols]})
    elif suffix in (".csv", ".tsv"):
        df = pd.read_csv(path, sep="\t" if suffix == ".tsv" else ",")
        mols = [dm.to_mol(s) for s in df[smiles_col]]
    else:  # one SMILES per line
        smis = [l.strip() for l in path.read_text().splitlines() if l.strip()]
        df, mols = pd.DataFrame({"smiles": smis}), [dm.to_mol(s) for s in smis]
    keep = [i for i, m in enumerate(mols) if m is not None]   # drop unparseable
    return df.iloc[keep].reset_index(drop=True), [mols[i] for i in keep]

def main():
    ap = argparse.ArgumentParser(description="Batch medchem filtering")
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", "-o", type=Path, required=True)
    ap.add_argument("--rules", help="comma-separated rule names")
    ap.add_argument("--nibr", action="store_true")
    ap.add_argument("--lilly", action="store_true")
    ap.add_argument("--pains", action="store_true")
    ap.add_argument("--n-jobs", type=int, default=-1)
    args = ap.parse_args()

    df, mols = load(args.input)
    if args.rules:
        rules = [r.strip() for r in args.rules.split(",")]
        res = mc.rules.RuleFilters(rule_list=rules)(mols=mols, n_jobs=args.n_jobs, progress=True)
        for r in rules:
            df[f"passes_{r}"] = [row[r] for row in res]
    if args.nibr:
        df["passes_nibr"] = mc.structural.NIBRFilters()(mols=mols, n_jobs=args.n_jobs)
    if args.lilly:
        ll = mc.structural.LillyDemeritsFilters()(mols=mols, n_jobs=args.n_jobs)
        df["lilly_demerits"] = [r["demerits"] for r in ll]
        df["passes_lilly"]   = [r["passes"] for r in ll]
    if args.pains:
        df["passes_pains"] = [mc.rules.basic_rules.pains_filter(m) for m in mols]

    df.to_csv(args.output, index=False)
    for col in [c for c in df.columns if c.startswith("passes_")]:
        print(f"{col}: {df[col].sum()}/{len(df)} ({100*df[col].mean():.1f}%)")

if __name__ == "__main__":
    main()
```

Usage:
```bash
python filter_molecules.py library.csv --rules rule_of_five,rule_of_cns --nibr --output filtered.csv
```

Adjust the filter stack per discovery stage using the recommendations in
[rules-catalog.md](rules-catalog.md#recommended-filter-stacks-by-stage).
