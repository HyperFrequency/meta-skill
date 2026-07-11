# RDKit Workflows

Extended, runnable patterns for the capabilities routed from `SKILL.md`. Each
block is self-contained given `from rdkit import Chem, DataStructs` and the
imports shown.

## 1. I/O and batch processing

```python
from rdkit import Chem

# Single molecule — guard the None
mol = Chem.MolFromSmiles("Cc1ccccc1")
if mol is None:
    raise ValueError("bad SMILES")

# Stream a large SDF without loading it all (low memory, thread-unsafe to share)
import gzip
with gzip.open("library.sdf.gz") as fh:
    for mol in Chem.ForwardSDMolSupplier(fh):
        if mol is None:      # a failed record yields None, not an exception
            continue
        ...  # process one at a time

# Write results
writer = Chem.SDWriter("out.sdf")
for mol in keepers:
    writer.write(mol)
writer.close()
```

Cache parsed molecules by pickling — re-parsing SMILES/SDF dominates runtime on
repeated loads:

```python
import pickle
pickle.dump(mols, open("mols.pkl", "wb"))
mols = pickle.load(open("mols.pkl", "rb"))
```

## 2. Sanitization and debugging bad structures

```python
from rdkit import Chem

# Parse without sanitizing so you can inspect problems
mol = Chem.MolFromSmiles("c1ccc1", sanitize=False)   # invalid aromatic ring
for problem in Chem.DetectChemistryProblems(mol):
    print(problem.GetType(), problem.Message())

# Sanitize but skip one step (e.g. keep computed props off)
Chem.SanitizeMol(mol, sanitizeOps=Chem.SANITIZE_ALL ^ Chem.SANITIZE_PROPERTIES)

# Kekulize for a writer that needs explicit single/double bonds
Chem.Kekulize(mol, clearAromaticFlags=True)
```

## 3. Descriptors and drug-likeness scan

```python
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

def profile(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    row = {
        "SMILES": Chem.MolToSmiles(mol),
        "Formula": rdMolDescriptors.CalcMolFormula(mol),
        "MW": Descriptors.MolWt(mol),
        "LogP": Descriptors.MolLogP(mol),
        "TPSA": Descriptors.TPSA(mol),
        "HBD": Descriptors.NumHDonors(mol),
        "HBA": Descriptors.NumHAcceptors(mol),
        "RotBonds": Descriptors.NumRotatableBonds(mol),
        "QED": Descriptors.qed(mol),
    }
    row["Lipinski"] = (row["MW"] <= 500 and row["LogP"] <= 5
                       and row["HBD"] <= 5 and row["HBA"] <= 10)
    return row
```

See `descriptors-reference.md` for the full descriptor catalogue and the batch
`Descriptors.CalcMolDescriptors(mol)` call.

## 4. Fingerprints, similarity, and screening

```python
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator

gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

def similarity_screen(query_smiles, library_smiles, threshold=0.7):
    q = Chem.MolFromSmiles(query_smiles)
    qfp = gen.GetFingerprint(q)
    mols = [(s, Chem.MolFromSmiles(s)) for s in library_smiles]
    fps = [(s, gen.GetFingerprint(m)) for s, m in mols if m is not None]
    sims = DataStructs.BulkTanimotoSimilarity(qfp, [fp for _s, fp in fps])
    hits = [(s, sim) for (s, _fp), sim in zip(fps, sims) if sim >= threshold]
    return sorted(hits, key=lambda t: t[1], reverse=True)
```

Other fingerprints: `GetRDKitFPGenerator`, `GetAtomPairGenerator`,
`GetTopologicalTorsionGenerator`, and `MACCSkeys.GenMACCSKeys(mol)`. Swap the
metric with `DataStructs.DiceSimilarity` / `CosineSimilarity`.

## 5. Clustering a library (Butina)

```python
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator
from rdkit.ML.Cluster import Butina

gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
fps = [gen.GetFingerprint(m) for m in mols]

# Condensed lower-triangle distance list
dists = []
for i in range(len(fps)):
    sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
    dists.extend(1.0 - s for s in sims)

clusters = Butina.ClusterData(dists, len(fps), distThresh=0.3, isDistData=True)
# Each cluster is a tuple of molecule indices; index [0] is the centroid.
```

## 6. Substructure / PAINS filtering

```python
from rdkit import Chem

def filter_library(smiles_list, include=None, exclude=None):
    inc = [Chem.MolFromSmarts(p) for p in (include or [])]
    exc = [Chem.MolFromSmarts(p) for p in (exclude or [])]
    keep = []
    for s in smiles_list:
        mol = Chem.MolFromSmiles(s)
        if mol is None:
            continue
        if any(mol.HasSubstructMatch(q) for q in exc):     # drop reactive/PAINS
            continue
        if inc and not all(mol.HasSubstructMatch(q) for q in inc):
            continue
        keep.append(s)
    return keep

# e.g. keep aromatics, drop acyl chlorides + Michael acceptors
filter_library(lib, include=["c1ccccc1"], exclude=["C(=O)Cl", "C=CC(=O)[C,N]"])
```

Pattern strings: `smarts-patterns.md`.

## 7. Reactions (reaction SMARTS)

```python
from rdkit import Chem
from rdkit.Chem import AllChem

rxn = AllChem.ReactionFromSmarts("[C:1](=[O:2])[OH]>>[C:1](=[O:2])OC")  # esterify
products = rxn.RunReactants((Chem.MolFromSmiles("CC(=O)O"),))
for product_set in products:
    for p in product_set:
        Chem.SanitizeMol(p)          # products come back unsanitized
        print(Chem.MolToSmiles(p))
```

Atom maps (`:1`, `:2`) carry atoms from reactants to products. `RunReactants`
returns a tuple of product-set tuples — one per way the reactants matched.

## 8. 2D depiction and 3D conformers

```python
from rdkit import Chem
from rdkit.Chem import AllChem

mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")   # aspirin

# 2D coordinates for drawing
AllChem.Compute2DCoords(mol)

# 3D: add hydrogens FIRST, embed, then relax geometry
mh = Chem.AddHs(mol)
AllChem.EmbedMolecule(mh, randomSeed=0xf00d)         # ETKDG
AllChem.MMFFOptimizeMolecule(mh)                     # or UFFOptimizeMolecule

# Conformer ensemble + per-conformer optimization
cids = AllChem.EmbedMultipleConfs(mh, numConfs=20, randomSeed=1)
energies = AllChem.MMFFOptimizeMoleculeConfs(mh)     # [(notConverged, energy), ...]
```

## 9. Drawing and highlighting

```python
from rdkit.Chem import Draw
from rdkit.Chem.Draw import rdMolDraw2D

# Quick grid
img = Draw.MolsToGridImage(mols, molsPerRow=4, subImgSize=(200, 200),
                           legends=[Chem.MolToSmiles(m) for m in mols])
img.save("grid.png")

# Highlight a substructure match with a customized drawer
patt = Chem.MolFromSmarts("c1ccccc1")
match = mol.GetSubstructMatch(patt)
drawer = rdMolDraw2D.MolDraw2DCairo(350, 350)
drawer.drawOptions().addStereoAnnotation = True
drawer.DrawMolecule(mol, highlightAtoms=list(match))
drawer.FinishDrawing()
open("highlight.png", "wb").write(drawer.GetDrawingText())
```

Use `MolDraw2DSVG` instead of `MolDraw2DCairo` for scalable SVG output.

## 10. Standardization and neutralization

```python
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize

mol = Chem.MolFromSmiles("[NH3+]CC(=O)[O-].Cl")   # zwitterion + counter-ion

mol = rdMolStandardize.Cleanup(mol)               # normalize + reionize + fragments
parent = rdMolStandardize.FragmentParent(mol)     # keep the largest fragment
neutral = rdMolStandardize.Uncharger().uncharge(parent)

# Canonical tautomer (deduplicating a database on tautomer identity)
canon = rdMolStandardize.TautomerEnumerator().Canonicalize(neutral)
print(Chem.MolToSmiles(canon))
```

## 11. Scaffolds and hashing

```python
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.Chem import rdMolHash

scaffold = MurckoScaffold.GetScaffoldForMol(mol)          # ring system + linkers
generic = MurckoScaffold.MakeScaffoldGeneric(scaffold)    # atoms→C, bonds→single
key = rdMolHash.MolHash(mol, rdMolHash.HashFunction.MurckoScaffold)
```

Scaffold and hash functions are the usual primitives for grouping a library by
core or deduplicating on a chosen equivalence (canonical SMILES, regioisomer,
tautomer, net charge — see `api-reference.md`).
