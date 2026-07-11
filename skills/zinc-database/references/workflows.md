# ZINC22 — Workflows and Integration

End-to-end recipes for common ZINC22 tasks, plus reusable Python helpers and wiring into
RDKit, OpenBabel, DOCK6, and AutoDock Vina. Endpoint grammar and parameters live in
`api_reference.md`; read the grammar caveat there before scripting at scale.

## Python helpers

Thin wrappers around `curl`, returning raw text you can parse into a DataFrame.

```python
import subprocess
import pandas as pd
from io import StringIO

BASE = "https://cartblanche22.docking.org"

def _get(url):
    return subprocess.run(["curl", "-s", url], capture_output=True, text=True).stdout

def query_by_id(zinc_ids, output_fields="zinc_id,smiles,catalogs"):
    ids = ",".join(zinc_ids) if isinstance(zinc_ids, (list, tuple)) else zinc_ids
    return _get(f"{BASE}/substances.txt:zinc_id={ids}&output_fields={output_fields}")

def search_by_smiles(smiles, dist=0, adist=0, output_fields="zinc_id,smiles"):
    return _get(f"{BASE}/smiles.txt:smiles={smiles}&dist={dist}&adist={adist}"
                f"&output_fields={output_fields}")

def random_compounds(count=100, subset=None, output_fields="zinc_id,smiles,tranche"):
    url = f"{BASE}/substance/random.txt:count={count}&output_fields={output_fields}"
    if subset:
        url += f"&subset={subset}"
    return _get(url)

def to_df(tsv_text):
    return pd.read_csv(StringIO(tsv_text), sep="\t")
```

## Workflow 1 — Prepare a docking library

1. Decide the property window (subset + tranche bounds) for your target.
2. Pull candidates:

   ```python
   df = to_df(random_compounds(count=10000, subset="drug-like",
                               output_fields="zinc_id,smiles,tranche"))
   ```
3. Filter by parsed tranche properties (`parse_tranche` in `api_reference.md`), or by
   RDKit-computed descriptors (below) if you need exact values rather than binned ones.
4. Download matching 3D tranche files from the repository (`wget`/`aria2c`, see
   `api_reference.md`) and feed them to your docking engine.

## Workflow 2 — Find purchasable analogs of a hit

```python
hit = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"          # ibuprofen
analogs = to_df(search_by_smiles(hit, dist=5,
                                 output_fields="zinc_id,smiles,catalogs"))
print(f"{len(analogs)} analogs")
print(analogs[["zinc_id", "smiles", "catalogs"]].head(10))
```

Start tight (`dist=1–3`) for near-neighbors; widen (`dist=5–10`) for scaffold hops. Keep
only rows with a non-empty `catalogs` list to guarantee purchasability, then pull 3D
structures for the survivors.

## Workflow 3 — Batch ID resolution

```python
zinc_ids = ["ZINC000000000001", "ZINC000000000002", "ZINC000000000003"]
df = to_df(query_by_id(zinc_ids, output_fields="zinc_id,smiles,supplier_code,catalogs"))
```

For thousands of IDs, POST a file instead of a long URL (see `api_reference.md`), and chunk
requests to stay polite.

## Workflow 4 — Sample chemical space

```python
frag = to_df(random_compounds(count=5000, subset="fragment"))
lead = to_df(random_compounds(count=5000, subset="lead-like"))
```

Use these draws for decoy sets, diversity benchmarking, or as a baseline distribution when
evaluating an enrichment metric.

## Property filtering with parsed tranches

```python
from api_reference import parse_tranche  # or paste the function inline

def filter_by_properties(df, mw_range=None, logp_range=None, max_hbd=None, phase=0):
    """Filter a results DataFrame using binned tranche properties.
    For exact descriptor values, prefer RDKit (below) over tranche bins."""
    props = df["tranche"].apply(parse_tranche)
    df = df.assign(
        mw=props.apply(lambda p: p["mw"] if p else None),
        logp=props.apply(lambda p: p["logp"] if p else None),
        hbd=props.apply(lambda p: p["h_donors"] if p else None),
        phase=props.apply(lambda p: p["phase"] if p else None),
    )
    mask = pd.Series(True, index=df.index)
    if mw_range:   mask &= df["mw"].between(*mw_range)
    if logp_range: mask &= df["logp"].between(*logp_range)
    if max_hbd is not None: mask &= df["hbd"] <= max_hbd
    if phase is not None:   mask &= df["phase"] == phase
    return df[mask]
```

## RDKit post-processing

Canonicalize SMILES, compute exact descriptors, embed 3D conformers, and write SDF:

```python
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors

def enrich_with_rdkit(df):
    df = df.copy()
    df["mol"] = df["smiles"].apply(Chem.MolFromSmiles)
    df = df[df["mol"].notna()]                         # drop unparseable SMILES
    df["mw"]        = df["mol"].apply(Descriptors.MolWt)
    df["logp"]      = df["mol"].apply(Descriptors.MolLogP)
    df["hbd"]       = df["mol"].apply(Descriptors.NumHDonors)
    df["hba"]       = df["mol"].apply(Descriptors.NumHAcceptors)
    df["tpsa"]      = df["mol"].apply(Descriptors.TPSA)
    df["rotatable"] = df["mol"].apply(Descriptors.NumRotatableBonds)
    return df

def save_sdf(df, path):
    writer = Chem.SDWriter(path)
    for _, row in df.iterrows():
        mol = row["mol"]
        if mol is None:
            continue
        mol = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol, randomSeed=42)
        AllChem.MMFFOptimizeMolecule(mol)
        mol.SetProp("ZINC_ID", row["zinc_id"])
        writer.write(mol)
    writer.close()
```

## OpenBabel format conversion

```bash
gunzip H05P035M400-0.db2.gz
obabel H05P035M400-0.db2 -O output.sdf
obabel H05P035M400-0.db2 -O output.mol2
```

## Docking-engine wiring

**DOCK6** — use the `.db2` directly:

```bash
wget https://files.docking.org/zinc22/H05/H05P035M400-0.db2.gz
gunzip H05P035M400-0.db2.gz
dock6 -i dock.in -o dock.out       # ligand DB referenced from dock.in
```

**AutoDock Vina** — convert MOL2 → PDBQT, then dock:

```bash
wget https://files.docking.org/zinc22/H05/H05P035M400-0.mol2.gz
gunzip H05P035M400-0.mol2.gz
prepare_ligand4.py -l H05P035M400-0.mol2 -o ligand.pdbqt -A hydrogens
vina --receptor protein.pdbqt --ligand ligand.pdbqt \
     --center_x 25 --center_y 25 --center_z 25 \
     --size_x 20 --size_y 20 --size_z 20
```

Command names (`dock6`, `prepare_ligand4.py`, `vina`, `obabel`) depend on your local
install — adjust paths to match your environment.
