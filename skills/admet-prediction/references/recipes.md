# ADMET Recipes

Copy-paste implementations for each tier of the panel. All RDKit calls below are
real APIs; the PyTDC and ADMET-AI blocks require the optional installs. Endpoint
meanings and thresholds are in [endpoints.md](endpoints.md).

- [Tier 1 — descriptor panel](#tier-1--physicochemical-descriptor-panel)
- [ESOL solubility](#esol-aqueous-solubility)
- [QED and synthetic accessibility](#qed-and-synthetic-accessibility)
- [Tier 2 — structural alerts](#tier-2--structural-alerts)
- [PAINS / Brenk via FilterCatalog](#pains--brenk-via-filtercatalog)
- [Tier 3 — ML models](#tier-3--ml-models)
- [Batch scoring from CSV](#batch-scoring-from-csv)
- [Traffic-light thresholds](#traffic-light-thresholds)

---

## Tier 1 — physicochemical descriptor panel

```python
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors

def descriptor_panel(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None                       # unparseable — skip / flag upstream
    return {
        "MW":        Descriptors.MolWt(mol),
        "cLogP":     Crippen.MolLogP(mol),          # Wildman-Crippen
        "TPSA":      rdMolDescriptors.CalcTPSA(mol),
        "HBD":       rdMolDescriptors.CalcNumHBD(mol),
        "HBA":       rdMolDescriptors.CalcNumHBA(mol),
        "RotBonds":  rdMolDescriptors.CalcNumRotatableBonds(mol),
        "Fsp3":      rdMolDescriptors.CalcFractionCSP3(mol),
        "AromRings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "HeavyAtoms": mol.GetNumHeavyAtoms(),
    }
```

Lipinski violations follow directly:

```python
def lipinski_violations(p):
    return sum([p["MW"] > 500, p["cLogP"] > 5, p["HBD"] > 5, p["HBA"] > 10])
```

The rule-based PK surrogates (Caco-2, HIA, P-gp, BBB, clearance) are threshold
combinations of these descriptors — see the thresholds table below and the per
endpoint rules in [endpoints.md](endpoints.md).

## ESOL aqueous solubility

Delaney's ESOL, using cLogP as the lipophilicity term:

```python
def esol_logs(mol):
    logp = Crippen.MolLogP(mol)
    mw   = Descriptors.MolWt(mol)
    rb   = rdMolDescriptors.CalcNumRotatableBonds(mol)
    heavy = mol.GetNumHeavyAtoms()
    aromatic_atoms = sum(a.GetIsAromatic() for a in mol.GetAtoms())
    aromatic_proportion = aromatic_atoms / heavy if heavy else 0.0
    return (0.16 - 0.63 * logp - 0.0062 * mw
            + 0.066 * rb - 0.74 * aromatic_proportion)   # log10(mol/L)
```

RMSE ≈ 0.7 log units. For a learned solubility model use ADMET-AI or `pytdc`
(`Solubility_AqSolDB`).

## QED and synthetic accessibility

```python
from rdkit.Chem import QED

qed = QED.qed(mol)                     # 0..1, weighted drug-likeness
props = QED.properties(mol)            # namedtuple: MW, ALOGP, HBA, HBD, PSA, ...
```

SA score ships in RDKit's Contrib directory (not the main namespace):

```python
import os, sys
from rdkit.Chem import RDConfig
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer                        # provided by RDKit Contrib
sa = sascorer.calculateScore(mol)      # 1 (easy) .. 10 (hard)
```

## Tier 2 — structural alerts

Any SMARTS-based liability library is applied the same way — compile the pattern
once, match per molecule. Store your alert set as `(name, smarts, severity)`
tuples so the catalog is auditable and extendable.

```python
# Illustrative alerts. Curate the full hERG / AMES / DILI sets for production use;
# medchem and public alert collections (Brenk, SureChEMBL) are good sources.
ALERTS = [
    ("aromatic_nitro",   "[$([NX3](=O)=O),$([NX3+](=O)[O-])][c]"),  # AMES
    ("aromatic_amine",   "[NX3;H2,H1;!$(NC=O)][c]"),                # AMES
    ("michael_acceptor", "[CX3]=[CX3][CX3]=[OX1]"),                 # reactive
    ("epoxide",          "C1OC1"),                                  # sensitizer
    ("thiourea",         "[NX3][CX3](=[SX1])[NX3]"),               # DILI
]

def match_alerts(mol, alerts=ALERTS):
    hits = []
    for name, smarts in alerts:
        patt = Chem.MolFromSmarts(smarts)
        if patt is not None and mol.HasSubstructMatch(patt):
            n = len(mol.GetSubstructMatches(patt))
            hits.append((name, n))
    return hits                        # [] means no alert -> GREEN for that panel
```

Traffic-light rule per toxicity panel: 0 hits → GREEN, 1 → YELLOW, 2+ → RED
(AMES/skin-sensitizer high-severity alerts go straight to RED — see
[endpoints.md](endpoints.md#toxicity)).

## PAINS / Brenk via FilterCatalog

RDKit ships curated PAINS (A/B/C), Brenk, NIH, and ChEMBL filter catalogs — prefer
these over hand-rolled SMARTS for assay-interference and unwanted-chemistry checks:

```python
from rdkit.Chem import FilterCatalog
from rdkit.Chem.FilterCatalog import FilterCatalogParams

params = FilterCatalogParams()
params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)   # or PAINS_A/_B/_C
params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
catalog = FilterCatalog.FilterCatalog(params)

if catalog.HasMatch(mol):
    for entry in catalog.GetMatches(mol):
        print(entry.GetDescription())     # human-readable alert name
```

## Tier 3 — ML models

For endpoints where descriptors are weak (Caco-2, CYP inhibition, clearance,
hERG IC50), use trained predictors.

**ADMET-AI** — fast Chemprop-RDKit predictions across the TDC ADMET panel from a
single SMILES or a list:

```python
from admet_ai import ADMETModel

model = ADMETModel()
preds = model.predict(smiles="CC(=O)Oc1ccccc1C(=O)O")   # dict of endpoint -> value
# list input returns a pandas DataFrame, one row per molecule
```

**PyTDC** — load benchmark datasets to train/evaluate your own model, or pull the
canonical splits for a leaderboard-comparable evaluation:

```python
from tdc.single_pred import ADME, Tox

caco2 = ADME(name="Caco2_Wang").get_split()     # train / valid / test DataFrames
herg  = Tox(name="hERG").get_split()

# Leaderboard-comparable benchmark harness:
from tdc.benchmark_group import admet_group
group = admet_group(path="data/")
benchmark = group.get("Caco2_Wang")             # {'train_val', 'test', 'name'}
```

Endpoint→dataset names on TDC include `Caco2_Wang`, `HIA_Hou`, `Pgp_Broccatelli`,
`BBB_Martins`, `PPBR_AZ`, `VDss_Lombardo`, `CYP3A4_Veith`, `CYP2D6_Veith`,
`CYP2C9_Veith`, `Clearance_Hepatocyte_AZ`, `hERG`, `AMES`, `DILI`,
`Solubility_AqSolDB`.

## Batch scoring from CSV

```python
import pandas as pd

df = pd.read_csv("candidates.csv")     # expects 'name','smiles' columns
rows = []
for _, r in df.iterrows():
    p = descriptor_panel(r["smiles"])
    if p is None:
        rows.append({"name": r["name"], "error": "unparseable_smiles"})
        continue
    p["name"] = r["name"]
    p["lipinski_violations"] = lipinski_violations(p)
    rows.append(p)
pd.DataFrame(rows).to_csv("admet_results.csv", index=False)
```

Always keep the `unparseable_smiles` branch — a single bad row should not abort a
library-scale run.

## Traffic-light thresholds

| Endpoint | GREEN | YELLOW | RED |
|----------|-------|--------|-----|
| QED | > 0.67 | 0.49–0.67 | < 0.49 |
| cLogP | −0.4 to 3.5 | 3.5 to 5.0 | > 5.0 or < −0.4 |
| MW (Da) | 150–500 | 500–700 | > 700 |
| TPSA (Å²) | < 90 | 90–140 | > 140 |
| HBD | 0–5 | 6–7 | > 7 |
| HBA | 0–10 | 11–12 | > 12 |
| RotBonds | 0–10 | 11–13 | > 13 |
| Fsp3 | ≥ 0.25 | 0.1–0.25 | < 0.1 |
| LogS (ESOL) | > −4 | −4 to −6 | < −6 |
| Caco-2 class | high | medium | low |
| HIA | likely high | uncertain | likely low |
| BBB penetration | likely | uncertain | unlikely |
| hERG liability | no alerts | 1 alert | 2+ alerts |
| AMES alerts | none | — | 1+ present |
| DILI alerts | none | 1 alert | 2+ alerts |
| PAINS alerts | 0 | 1 | 2+ |
| Lipinski violations | 0 | 1 | 2+ |
| SA score | 1–4 | 4–6 | > 6 |
