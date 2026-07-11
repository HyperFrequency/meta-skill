# RDKit API Reference

Module-by-module signatures for the calls you reach for most. Parameters shown
are the commonly used ones, not exhaustive; consult `help(fn)` in a session for
the full list. Return `None` on failure is noted where it applies.

## `rdkit.Chem` — core

### Reading structures (return `Mol` or `None`)

| Call | Parses |
|---|---|
| `Chem.MolFromSmiles(smiles, sanitize=True)` | SMILES |
| `Chem.MolFromSmarts(smarts)` | SMARTS query |
| `Chem.MolFromMolFile(path, sanitize=True, removeHs=True)` | MOL file |
| `Chem.MolFromMolBlock(block, sanitize=True, removeHs=True)` | MOL block string |
| `Chem.MolFromMol2File(path, ...)` / `MolFromMol2Block(block, ...)` | Tripos MOL2 |
| `Chem.MolFromPDBFile(path, ...)` / `MolFromPDBBlock(block, ...)` | PDB |
| `Chem.MolFromInchi(inchi, sanitize=True, removeHs=True)` | InChI |
| `Chem.MolFromSequence(seq, sanitize=True)` | peptide sequence |

### Writing structures

| Call | Produces |
|---|---|
| `Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)` | canonical SMILES |
| `Chem.MolToSmiles(mol, canonical=False, doRandom=True)` | randomized SMILES (augmentation) |
| `Chem.MolToSmarts(mol)` | SMARTS |
| `Chem.MolToMolBlock(mol, includeStereo=True, confId=-1)` | MOL block |
| `Chem.MolToMolFile(mol, path, ...)` | MOL file |
| `Chem.MolToPDBBlock(mol, confId=-1)` / `MolToPDBFile(mol, path)` | PDB |
| `Chem.MolToInchi(mol)` / `Chem.MolToInchiKey(mol)` | InChI / InChIKey |

### Batch I/O

- `Chem.SDMolSupplier(path, sanitize=True, removeHs=True)` — random-access SDF reader (indexable; **not** thread-safe to share)
- `Chem.ForwardSDMolSupplier(fileobj, sanitize=True)` — forward-only, streaming (low memory; works on gzip file objects)
- `Chem.MultithreadedSDMolSupplier(path)` — parallel SDF parsing (order not guaranteed)
- `Chem.SmilesMolSupplier(path, delimiter=' ', titleLine=True)` — SMILES file reader
- `Chem.SDWriter(path)` / `Chem.SmilesWriter(path)` — writers; `.write(mol)` then `.close()`

### Sanitization & validation

- `Chem.SanitizeMol(mol, sanitizeOps=Chem.SANITIZE_ALL, catchErrors=False)` — run the full 13-step clean-up (valence, aromaticity, ring perception, chirality)
- `Chem.DetectChemistryProblems(mol)` — list of problem objects; each has `.GetType()` and `.Message()`
- Skip specific steps with XOR, e.g. `sanitizeOps=Chem.SANITIZE_ALL ^ Chem.SANITIZE_PROPERTIES`
- `Chem.AssignStereochemistry(mol, cleanIt=True, force=False)`
- `Chem.AssignStereochemistryFrom3D(mol, confId=-1)` — perceive stereo from coordinates
- `Chem.FindMolChiralCenters(mol, includeUnassigned=False)` → `[(atom_idx, 'R'|'S'|'?'), ...]`

### Hydrogens, aromaticity, fragments

- `Chem.AddHs(mol, addCoords=False)` / `Chem.RemoveHs(mol)` / `Chem.RemoveAllHs(mol)`
- `Chem.Kekulize(mol, clearAromaticFlags=False)` / `Chem.SetAromaticity(mol, model=Chem.AROMATICITY_RDKIT)`
- `Chem.GetMolFrags(mol, asMols=False)` — disconnected fragments (atom-index tuples, or `Mol`s if `asMols=True`)
- `Chem.FragmentOnBonds(mol, bondIndices, addDummies=True)`
- `Chem.ReplaceSubstructs(mol, query, replacement, replaceAll=False)` → tuple of `Mol`
- `Chem.DeleteSubstructs(mol, query)`

### Substructure search (methods on `Mol`)

- `mol.HasSubstructMatch(query, useChirality=False)` → `bool`
- `mol.GetSubstructMatch(query)` → first match (tuple of atom indices)
- `mol.GetSubstructMatches(query, uniquify=True, maxMatches=1000)` → tuple of tuples

### Atoms, bonds, rings

Atom (`mol.GetAtomWithIdx(i)` / iterate `mol.GetAtoms()`): `GetSymbol()`,
`GetAtomicNum()`, `GetDegree()`, `GetTotalDegree()`, `GetFormalCharge()`,
`GetNumRadicalElectrons()`, `GetIsAromatic()`, `GetHybridization()`, `GetIdx()`,
`IsInRing()`, `IsInRingSize(n)`, `GetChiralTag()`.

Bond (`mol.GetBondWithIdx(i)` / iterate `mol.GetBonds()`): `GetBondType()`,
`GetBeginAtomIdx()`, `GetEndAtomIdx()`, `GetIsConjugated()`, `GetIsAromatic()`,
`IsInRing()`, `GetStereo()`.

Molecule: `GetNumAtoms()`, `GetNumHeavyAtoms()`, `GetNumBonds()`,
`GetRingInfo()`. Ring info: `.NumRings()`, `.AtomRings()`, `.BondRings()`.
`Chem.GetSymmSSSR(mol)` returns the smallest set of smallest rings.

## `rdkit.Chem.AllChem` — extended chemistry

### Coordinates & conformers

- `AllChem.Compute2DCoords(mol)` — 2D depiction coordinates
- `AllChem.GenerateDepictionMatching2DStructure(mol, reference)` — align depiction to a template
- `AllChem.EmbedMolecule(mol, randomSeed=-1, useRandomCoords=False)` — one 3D conformer (ETKDG)
- `AllChem.EmbedMultipleConfs(mol, numConfs=10, randomSeed=-1)` → list of conformer ids
- `AllChem.ConstrainedEmbed(mol, core)` — embed with a substructure pinned to reference coordinates

### Force fields

- `AllChem.UFFOptimizeMolecule(mol, maxIters=200, confId=-1)`
- `AllChem.MMFFOptimizeMolecule(mol, maxIters=200, confId=-1, mmffVariant='MMFF94')`
- `AllChem.MMFFOptimizeMoleculeConfs(mol)` — optimize all conformers, returns `[(notConverged, energy), ...]`
- `AllChem.GetConformerRMS(mol, confId1, confId2, prealigned=False)` / `AllChem.AlignMol(prbMol, refMol)`

### Reactions

- `AllChem.ReactionFromSmarts('reactants>>products')` → `ChemicalReaction`
- `rxn.RunReactants((mol1, mol2, ...))` → tuple of product-set tuples; sanitize each product yourself
- `AllChem.CreateDifferenceFingerprintForReaction(rxn)` — reaction fingerprint for similarity

## `rdkit.Chem.rdFingerprintGenerator` — modern fingerprints (preferred)

Construct a generator once, reuse across a library:

- `GetMorganGenerator(radius=2, fpSize=2048)` — circular / ECFP-like
- `GetRDKitFPGenerator(minPath=1, maxPath=7, fpSize=2048)` — topological
- `GetAtomPairGenerator(minDistance=1, maxDistance=30)`
- `GetTopologicalTorsionGenerator()`

On any generator: `gen.GetFingerprint(mol)` (bit vector),
`gen.GetCountFingerprint(mol)` (counts). MACCS keys live separately:
`from rdkit.Chem import MACCSkeys; MACCSkeys.GenMACCSKeys(mol)` (166 bits).

> Legacy helpers such as `AllChem.GetMorganFingerprintAsBitVect(mol, radius,
> nBits)` still function but are deprecated — use the generators for new code.

## `rdkit.DataStructs` — similarity

- Pairwise: `TanimotoSimilarity`, `DiceSimilarity`, `CosineSimilarity`,
  `SokalSimilarity`, `KulczynskiSimilarity`, `McConnaugheySimilarity`
- Bulk (one fp vs many): `BulkTanimotoSimilarity(fp, fps)`, `BulkDiceSimilarity`, `BulkCosineSimilarity`
- Distance: `TanimotoDistance`, `DiceDistance` (= 1 − similarity)

## `rdkit.ML.Cluster.Butina`

- `Butina.ClusterData(distances, nPts, distThresh, isDistData=True)` → tuple of
  clusters (each a tuple of point indices; first element of each cluster is its
  centroid). Feed a condensed lower-triangle distance list.

## `rdkit.Chem.Draw` — visualization

- `Draw.MolToImage(mol, size=(300,300), highlightAtoms=None)` → PIL image
- `Draw.MolToFile(mol, path, size=(300,300))`
- `Draw.MolsToGridImage(mols, molsPerRow=3, subImgSize=(200,200), legends=None)`
- `Draw.ReactionToImage(rxn)`
- `Draw.DrawMorganBit(mol, bitId, bitInfo)` — visualize what a fingerprint bit encodes
- `from rdkit.Chem.Draw import rdMolDraw2D` → `MolDraw2DCairo(w, h)` (PNG) or
  `MolDraw2DSVG(w, h)` (SVG); set `drawer.drawOptions().addAtomIndices` etc., then
  `drawer.DrawMolecule(mol); drawer.FinishDrawing(); drawer.GetDrawingText()`
- Jupyter inline: `from rdkit.Chem.Draw import IPythonConsole`

## `rdkit.Chem.MolStandardize.rdMolStandardize`

- `rdMolStandardize.Cleanup(mol)` — normalize + reionize + strip small fragments
- `rdMolStandardize.Normalize(mol)` / `Reionize(mol)` / `RemoveFragments(mol)`
- `rdMolStandardize.Uncharger().uncharge(mol)` — neutralize formal charges
- `rdMolStandardize.TautomerEnumerator()` → `.Enumerate(mol)`, `.Canonicalize(mol)`

## `rdkit.Chem.rdMolHash` & scaffolds

- `rdMolHash.MolHash(mol, rdMolHash.HashFunction.<F>)` where `<F>` ∈
  `CanonicalSmiles`, `MurckoScaffold`, `AnonymousGraph`, `ElementGraph`,
  `Regioisomer`, `NetCharge`, `HetAtomTautomer`, ...
- `from rdkit.Chem.Scaffolds import MurckoScaffold` →
  `MurckoScaffold.GetScaffoldForMol(mol)`, `MakeScaffoldGeneric(mol)`

## `rdkit.Chem.ChemicalFeatures` — pharmacophores

```python
import os
from rdkit import RDConfig
from rdkit.Chem import ChemicalFeatures
factory = ChemicalFeatures.BuildFeatureFactory(
    os.path.join(RDConfig.RDDataDir, 'BaseFeatures.fdef'))
for feat in factory.GetFeaturesForMol(mol):
    feat.GetFamily(), feat.GetType(), feat.GetAtomIds()
```

## Common enums

- **Sanitize ops:** `SANITIZE_NONE`, `SANITIZE_ALL`, `SANITIZE_KEKULIZE`,
  `SANITIZE_SETAROMATICITY`, `SANITIZE_PROPERTIES`, `SANITIZE_CLEANUPCHIRALITY`, ...
- **Bond types:** `BondType.SINGLE|DOUBLE|TRIPLE|AROMATIC|DATIVE|UNSPECIFIED`
- **Hybridization:** `HybridizationType.S|SP|SP2|SP3|SP3D|SP3D2`
- **Chirality:** `ChiralType.CHI_UNSPECIFIED|CHI_TETRAHEDRAL_CW|CHI_TETRAHEDRAL_CCW`
