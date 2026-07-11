# Target and Ligand Preparation

Docking quality is dominated by input preparation. A pose from a dirty receptor
or a badly protonated ligand is meaningless regardless of the scoring function.

## Target (receptor) preparation

### 1. Clean the structure with Biopython

Drop waters and non-cofactor heteroatoms, optionally isolate one chain, and write
a clean PDB.

```python
from Bio.PDB import PDBParser, PDBIO, Select

class ReceptorSelect(Select):
    def __init__(self, chain=None, keep_hetero=()):
        self.chain = chain
        self.keep_hetero = set(keep_hetero)   # e.g. {"ZN", "MG"} to keep cofactors

    def accept_chain(self, chain):
        return self.chain is None or chain.id == self.chain

    def accept_residue(self, residue):
        hetflag, _, _ = residue.id
        if hetflag == " ":                    # standard amino acid
            return True
        if residue.resname == "HOH":          # water
            return False
        return residue.resname in self.keep_hetero

parser = PDBParser(QUIET=True)
structure = parser.get_structure("rec", "protein.pdb")
io = PDBIO()
io.set_structure(structure)
io.save("clean.pdb", ReceptorSelect(chain="A"))
```

Decide deliberately whether to keep a **co-crystallized ligand** (useful to
define the pocket — see `references/pocket-detection.md`) and **structural
cofactors / metal ions** (often essential for binding; keep them).

### 2. Add hydrogens and repair the structure

Biopython does not add hydrogens or fix missing atoms. Options:

- **PDBFixer** (OpenMM) — adds missing heavy atoms and residues, then hydrogens
  at a target pH. Best when the crystal structure has gaps.
  ```python
  from pdbfixer import PDBFixer
  from openmm.app import PDBFile
  fixer = PDBFixer(filename="clean.pdb")
  fixer.findMissingResidues(); fixer.findMissingAtoms(); fixer.addMissingAtoms()
  fixer.addMissingHydrogens(pH=7.4)
  PDBFile.writeFile(fixer.topology, fixer.positions, open("prepared.pdb", "w"))
  ```
- **reduce** — fast, adds and optimizes hydrogens, flips Asn/Gln/His.
  `reduce clean.pdb > prepared.pdb`
- **Open Babel** — `obabel clean.pdb -O prepared.pdb -h -p 7.4`

Explicit protein hydrogens are **required** for ProLIF hydrogen-bond detection
later, so do not skip this step.

### 3. Convert to receptor PDBQT

Vina reads PDBQT (adds atom types and Gasteiger charges, marks the receptor rigid):

- **Meeko** (recommended): `mk_prepare_receptor.py --read_pdb prepared.pdb -o receptor -p`
  writes `receptor.pdbqt`. Meeko's receptor CLI options vary across versions —
  check `mk_prepare_receptor.py --help`. Use `-f <resnums>` to make selected side
  chains flexible.
- **AutoDockTools**: `prepare_receptor4.py -r prepared.pdb -o receptor.pdbqt`
- **Open Babel** (last resort): `obabel prepared.pdb -xr -O receptor.pdbqt`
  (`-xr` = rigid). Charge quality is lower than Meeko/ADT.

## Ligand preparation

### 1. Standardize the input

Strip counter-ions and keep the largest organic fragment before embedding.

```python
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.MolStandardize import rdMolStandardize

mol = Chem.MolFromSmiles(smiles)
if mol is None:
    raise ValueError("invalid SMILES")            # validate first (see smiles-validation)
mol = rdMolStandardize.FragmentParent(mol)         # drop salts / keep parent
mol = rdMolStandardize.Uncharger().uncharge(mol)   # neutralize, then re-protonate at pH
```

### 2. Protonate at the target pH

RDKit does not assign pH-dependent protonation. Use one of:

- **Open Babel**: `obabel lig.smi -O lig.sdf --gen3d -p 7.4`
- **Dimorphite-DL**: enumerates dominant microstates in a pH range.

Getting the ligand charge state right (e.g. a basic amine protonated at pH 7.4)
often matters more to the pose than the docking method.

### 3. Embed 3D conformers and minimize

```python
mol = Chem.AddHs(mol)
params = AllChem.ETKDGv3()
params.randomSeed = 0xf00d
AllChem.EmbedMolecule(mol, params)                 # single conformer
# or, for flexible ligands, sample several:
# AllChem.EmbedMultipleConfs(mol, numConfs=10, params=params)
AllChem.MMFFOptimizeMolecule(mol)                  # UFFOptimizeMolecule if MMFF fails
Chem.SDWriter("ligand.sdf").write(mol)
```

Vina samples ligand torsions itself, so a single good conformer is usually
enough; multiple conformers matter more for DiffDock inputs or ring flexibility.

### 4. Assign charges and convert to PDBQT

- **Gasteiger charges**: `AllChem.ComputeGasteigerCharges(mol)` or via Open Babel
  `--partialcharge gasteiger`.
- **Ligand PDBQT** (recommended, Meeko): `mk_prepare_ligand.py -i ligand.sdf -o ligand.pdbqt`
  — assigns rotatable-bond torsions and merges non-polar hydrogens. Meeko can also
  be driven in-process (`MoleculePreparation().prepare(mol)` then
  `PDBQTWriterLegacy.write_string(setup)`); the exact call differs across Meeko
  0.4/0.5/0.6, so prefer the CLI for stability or pin a version.
- Open Babel fallback: `obabel ligand.sdf -O ligand.pdbqt`.

### 5. Batch a library for screening

Read a CSV with `name,smiles` columns, run steps 1–4 per row, and either write one
multi-molecule SDF or one PDBQT per compound (Vina docks one ligand PDBQT at a
time). Log and skip rows that fail embedding rather than aborting the run.

## Common preparation failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `EmbedMolecule` returns -1 | Macrocycle / dense stereochemistry | `params.useRandomCoords = True`, raise `maxIterations`, try `EmbedMultipleConfs` |
| Vina "atom type not found" | Exotic element or bad PDBQT | Re-prepare receptor; drop unusual heteroatoms |
| No H-bonds detected downstream | Receptor or ligand missing hydrogens | Add H (PDBFixer/reduce/obabel) before PDBQT |
| Wrong ligand charge / pose | Protonation ignored | Protonate at target pH before embedding |
| Salt/counter-ion docked | Fragment not stripped | `FragmentParent` / `SaltRemover` first |
| MMFF minimization fails | Unparameterized atom | Fall back to `UFFOptimizeMolecule` |
