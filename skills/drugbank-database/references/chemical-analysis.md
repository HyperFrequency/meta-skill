# Chemical Structure and Similarity

Structure-based analysis of DrugBank compounds: extracting structures and
properties, drug-likeness rules, RDKit similarity/fingerprints, substructure
search, ADMET heuristics, and chemical-space analysis. Assumes `ns = {"db":
"http://www.drugbank.ca"}`, a `root`, and `get_text_safe` from `drug-queries.md`.

For general cheminformatics on molecules that are **not** from DrugBank, use the
`rdkit`, `datamol`, `molfeat`, or `deepchem` skills instead.

## Structures and properties

Structures and calculated descriptors live under `<calculated-properties>`;
measured values under `<experimental-properties>`. Both are `<property>` lists
with `<kind>`/`<value>` children.

```python
CALC_STRUCT = {"SMILES", "InChI", "InChIKey", "Molecular Formula", "IUPAC Name"}

def get_structures(root, ns, drugbank_id):
    props = get_all_properties(root, ns, drugbank_id)["calculated"]
    return {k: v for k, v in props.items() if k in CALC_STRUCT}

def get_all_properties(root, ns, drugbank_id):
    for drug in root.findall("db:drug", ns):
        primary = drug.find('db:drugbank-id[@primary="true"]', ns)
        if primary is not None and primary.text == drugbank_id:
            out = {"calculated": {}, "experimental": {}}
            for block, key in [("calculated-properties", "calculated"),
                               ("experimental-properties", "experimental")]:
                parent = drug.find(f"db:{block}", ns)
                if parent is not None:
                    for p in parent.findall("db:property", ns):
                        kind = get_text_safe(p.find("db:kind", ns))
                        value = get_text_safe(p.find("db:value", ns))
                        if kind:
                            out[key][kind] = value
            return out
    return {"calculated": {}, "experimental": {}}
```

Common calculated kinds: `Molecular Weight`, `logP`, `logS`, `Polar Surface Area
(PSA)`, `H Bond Donor Count`, `H Bond Acceptor Count`, `Rotatable Bond Count`,
`Refractivity`, `Polarizability`. Values are strings — cast before arithmetic and
guard against missing keys.

## Drug-likeness rules

Lipinski's Rule of Five (oral bioavailability; one violation tolerated) and
Veber's rules. These are **guidelines, not hard cutoffs**.

```python
def _num(props, kind, cast=float, default=0):
    try:
        return cast(props.get(kind, default))
    except (ValueError, TypeError):
        return default

def lipinski_ro5(root, ns, drugbank_id):
    c = get_all_properties(root, ns, drugbank_id)["calculated"]
    checks = {
        "molecular_weight": _num(c, "Molecular Weight") <= 500,
        "logP": _num(c, "logP") <= 5,
        "h_bond_donors": _num(c, "H Bond Donor Count", int) <= 5,
        "h_bond_acceptors": _num(c, "H Bond Acceptor Count", int) <= 10,
    }
    violations = sum(1 for ok in checks.values() if not ok)
    return {"passes": violations <= 1, "violations": violations, "rules": checks}

def veber(root, ns, drugbank_id):
    c = get_all_properties(root, ns, drugbank_id)["calculated"]
    checks = {
        "polar_surface_area": _num(c, "Polar Surface Area (PSA)") <= 140,
        "rotatable_bonds": _num(c, "Rotatable Bond Count", int) <= 10,
    }
    return {"passes": all(checks.values()), "rules": checks}
```

## Similarity (RDKit)

DrugBank stores SMILES but not fingerprints — compute those with RDKit. Use the
current `rdFingerprintGenerator` API (the older `AllChem.GetMorganFingerprintAsBitVect`
still works but is deprecated).

```python
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator, DataStructs

_MORGAN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)  # ECFP4

def tanimoto(smiles1, smiles2):
    m1, m2 = Chem.MolFromSmiles(smiles1 or ""), Chem.MolFromSmiles(smiles2 or "")
    if m1 is None or m2 is None:      # invalid/absent SMILES
        return None
    fp1, fp2 = _MORGAN.GetFingerprint(m1), _MORGAN.GetFingerprint(m2)
    return DataStructs.TanimotoSimilarity(fp1, fp2)
```

### Find similar drugs

```python
def find_similar_drugs(root, ns, ref_id, threshold=0.7):
    ref_smiles = get_structures(root, ns, ref_id).get("SMILES")
    if not ref_smiles:
        return []
    ref_mol = Chem.MolFromSmiles(ref_smiles)
    if ref_mol is None:
        return []
    ref_fp = _MORGAN.GetFingerprint(ref_mol)
    hits = []
    for drug in root.findall("db:drug", ns):
        drug_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        if drug_id == ref_id:
            continue
        smiles = get_structures(root, ns, drug_id).get("SMILES")
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is None:
            continue
        sim = DataStructs.TanimotoSimilarity(ref_fp, _MORGAN.GetFingerprint(mol))
        if sim >= threshold:
            hits.append({
                "drug_id": drug_id,
                "drug_name": get_text_safe(drug.find("db:name", ns)),
                "similarity": sim,
                "indication": get_text_safe(drug.find("db:indication", ns)),
            })
    return sorted(hits, key=lambda x: x["similarity"], reverse=True)
```

A full-corpus scan recomputes SMILES/fingerprints per call. For repeated
searches, precompute a `{drug_id: fingerprint}` cache once and reuse it. Rough
Tanimoto guide: `>0.85` very similar, `0.7-0.85` similar, `<0.7` different.

## Fingerprints and substructure

```python
from rdkit.Chem import MACCSkeys, rdMolDescriptors

def fingerprints(smiles):
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return None
    return {
        "morgan": _MORGAN.GetFingerprint(mol),
        "maccs": MACCSkeys.GenMACCSKeys(mol),
        "rdkit": Chem.RDKFingerprint(mol),
    }

def search_substructure(root, ns, smarts):
    pattern = Chem.MolFromSmarts(smarts)
    if pattern is None:
        raise ValueError(f"Invalid SMARTS: {smarts}")
    hits = []
    for drug in root.findall("db:drug", ns):
        drug_id = drug.find('db:drugbank-id[@primary="true"]', ns).text
        smiles = get_structures(root, ns, drug_id).get("SMILES")
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is not None and mol.HasSubstructMatch(pattern):
            hits.append({"drug_id": drug_id,
                         "drug_name": get_text_safe(drug.find("db:name", ns))})
    return hits

benzene = search_substructure(root, ns, "c1ccccc1")   # aromatic benzene ring
```

## ADMET heuristics

Rule-based screens over physicochemical properties — coarse triage, not
predictive models. For trained ADMET models use the `admet-prediction` skill.

```python
def predict_absorption(root, ns, drugbank_id):
    c = get_all_properties(root, ns, drugbank_id)["calculated"]
    mw, logp = _num(c, "Molecular Weight"), _num(c, "logP")
    psa, hbd = _num(c, "Polar Surface Area (PSA)"), _num(c, "H Bond Donor Count", int)
    score = sum(25 for ok in [mw <= 500, -0.5 <= logp <= 5.0, psa <= 140, hbd <= 5] if ok)
    return {"absorption_score": score, "predicted": "good" if score == 100 else "poor"}

def predict_bbb(root, ns, drugbank_id):
    c = get_all_properties(root, ns, drugbank_id)["calculated"]
    return {"bbb_permeable": (_num(c, "Molecular Weight") <= 450
                              and _num(c, "logP") <= 5.0
                              and _num(c, "Polar Surface Area (PSA)") <= 90
                              and _num(c, "H Bond Donor Count", int) <= 3)}
```

## Chemical space

Project drugs into 2D by physicochemical descriptors for visualization or
clustering.

```python
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

DESCRIPTORS = ["Molecular Weight", "logP", "Polar Surface Area (PSA)",
               "H Bond Donor Count", "H Bond Acceptor Count", "Rotatable Bond Count"]

def descriptor_matrix(root, ns, drug_ids):
    rows, valid = [], []
    for drug_id in drug_ids:
        c = get_all_properties(root, ns, drug_id)["calculated"]
        vec = [_num(c, d) for d in DESCRIPTORS]
        if any(vec):          # skip drugs with no computed descriptors
            rows.append(vec)
            valid.append(drug_id)
    return np.array(rows), valid

def chemical_space_pca(root, ns, drug_ids):
    X, ids = descriptor_matrix(root, ns, drug_ids)
    Xs = StandardScaler().fit_transform(X)
    pcs = PCA(n_components=2).fit_transform(Xs)
    return pd.DataFrame({"drug_id": ids, "PC1": pcs[:, 0], "PC2": pcs[:, 1]})

def cluster_drugs(root, ns, drug_ids, n_clusters=10):
    X, ids = descriptor_matrix(root, ns, drug_ids)
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto").fit_predict(
        StandardScaler().fit_transform(X))
    return pd.DataFrame({"drug_id": ids, "cluster": labels})
```

## Best practices

1. Validate every SMILES (`Chem.MolFromSmiles` returns `None` on failure) before use.
2. Cache fingerprints for large-scale similarity — recomputation dominates cost.
3. Standardize molecules (neutralize charges, strip salts) before comparison.
4. Use multiple fingerprint types when a single one under-discriminates.
5. Treat Lipinski/Veber and the ADMET rules as screens, not verdicts.
6. Cast property strings to numbers defensively; many entries lack computed values.
