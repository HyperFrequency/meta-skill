# I/O and File Formats (`pymatgen.io.*`)

Pymatgen reads and writes 100+ formats through one convenience layer plus dedicated
parser/writer classes for each electronic-structure code. Reach for the convenience methods
first; drop to a specific class when you need fine control or code-specific output fields.

## Convenience layer

```python
from pymatgen.core import Structure, Molecule

struct = Structure.from_file("POSCAR")          # auto-detect from name/contents
struct = Structure.from_file("file.txt", fmt="cif")  # force a format
mol    = Molecule.from_file("molecule.xyz")

struct.to(filename="out.cif")                   # writer chosen by extension
poscar_text = struct.to(fmt="poscar")           # return string, don't write
```

### Convert one file to another format

```python
Structure.from_file("input.cif").to(filename="POSCAR")
```

### Batch convert a directory

```python
from pathlib import Path
from pymatgen.core import Structure

out_dir = Path("./cif_files"); out_dir.mkdir(exist_ok=True)
for src in Path(".").glob("*.vasp"):
    Structure.from_file(src).to(filename=out_dir / f"{src.stem}.cif")
```

Wrap file reads in `try/except` — malformed CIFs and truncated output files are common.

## Structure formats

| Format | Notes |
| --- | --- |
| CIF | Crystallographic standard; symmetry, partial occupancy, may hold multiple structures |
| POSCAR / CONTCAR | VASP; selective dynamics, high precision |
| XYZ | Cartesian; molecules and (non-periodic) coordinate dumps |
| PDB | Biomolecule-style records |
| JSON / YAML | Via `as_dict()` / `from_dict()` — version-safe persistence |
| XSF, CSSR, Res, PWmat | Additional crystal formats |

### CIF, explicit parser/writer

```python
from pymatgen.io.cif import CifParser, CifWriter

structures = CifParser("structure.cif").get_structures()  # returns a LIST
struct = structures[0]
CifWriter(struct).write_file("out.cif")
```

### POSCAR, explicit

```python
from pymatgen.io.vasp import Poscar

struct = Poscar.from_file("POSCAR").structure
Poscar(struct).write_file("POSCAR")
```

## VASP (the deepest integration)

### Inputs

```python
from pymatgen.io.vasp.inputs import Incar, Kpoints, Potcar, VaspInput, Poscar

incar = Incar({"ENCUT": 520, "ISMEAR": 0, "SIGMA": 0.05})
kpoints = Kpoints.automatic_density(struct, 1000)   # by reciprocal density
potcar = Potcar(["Fe_pv", "O"])                     # functional variants
VaspInput(incar, kpoints, Poscar(struct), potcar).write_input("./calc")
```

### Outputs

```python
from pymatgen.io.vasp.outputs import Vasprun, Outcar, Oszicar

vr = Vasprun("vasprun.xml")
vr.final_structure          # relaxed geometry
vr.final_energy             # total energy (eV)
vr.get_band_structure()     # BandStructure object
vr.complete_dos             # CompleteDos object

oc = Outcar("OUTCAR")
oc.total_mag                # total magnetization
oc.elastic_tensor           # if computed

Oszicar("OSZICAR")          # SCF/ionic convergence trace
```

### Input sets — pre-tuned parameter bundles

Encode Materials Project's converged INCAR/KPOINTS/POTCAR choices so you rarely hand-write an
INCAR. Customize via `user_incar_settings`.

```python
from pymatgen.io.vasp.sets import (
    MPRelaxSet, MPStaticSet, MPNonSCFSet, MPSOCSet, MPHSERelaxSet,
)

MPRelaxSet(struct).write_input("./relax")
MPStaticSet(struct, user_incar_settings={"ENCUT": 600}).write_input("./static")
MPNonSCFSet(struct, mode="line").write_input("./bands")   # line mode for band structure
```

## Other electronic-structure codes

```python
# Gaussian
from pymatgen.io.gaussian import GaussianInput, GaussianOutput
GaussianInput(mol, functional="B3LYP", basis_set="6-31G(d)",
              route_parameters={"Opt": None}).write_file("in.gjf")
out = GaussianOutput("out.log"); out.final_energy; out.frequencies

# Quantum ESPRESSO
from pymatgen.io.pwscf import PWInput, PWOutput
PWInput(struct, control={"calculation": "scf"},
        system={"ecutwfc": 50, "ecutrho": 400}).write_file("pw.in")

# LAMMPS
from pymatgen.io.lammps.data import LammpsData
LammpsData.from_structure(struct).write_file("data.lammps")

# Q-Chem, ABINIT, CP2K, FEFF (XAS), Exciting, NWChem, ATAT, LMTO also supported
from pymatgen.io.qchem.inputs import QCInput
QCInput(mol, rem={"method": "B3LYP", "basis": "6-31G*", "job_type": "opt"}).write_file("mol.qin")
```

## Interop adapters

```python
# ASE (Atomic Simulation Environment)
from pymatgen.io.ase import AseAtomsAdaptor
atoms  = AseAtomsAdaptor.get_atoms(struct)      # pymatgen -> ASE
struct = AseAtomsAdaptor.get_structure(atoms)   # ASE -> pymatgen

# Phonopy
from pymatgen.io.phonopy import get_phonopy_structure, get_pmg_structure

# OpenBabel (many molecular formats, 3D coord generation)
from pymatgen.io.babel import BabelMolAdaptor
```

## Provenance-tracking I/O

`TransformedStructure` records the chain of transformations applied to a structure and can write
a full VASP input directory with history attached. Transmuters apply a shared transformation list
across many files:

```python
from pymatgen.alchemy.materials import TransformedStructure
from pymatgen.transformations.standard_transformations import SupercellTransformation

ts = TransformedStructure(struct, [])
ts.append_transformation(SupercellTransformation([[2, 0, 0], [0, 2, 0], [0, 0, 2]]))
ts.write_vasp_input("./calc_dir")

from pymatgen.alchemy.transmuters import CifTransmuter, PoscarTransmuter
```

See [transformations-and-workflows.md](transformations-and-workflows.md) for the full
transformation catalog.

## Guidance

1. Prefer `from_file()` / `to()`; fall back to explicit parsers for detailed output fields.
2. Wrap file I/O in `try/except`.
3. Use `Vasprun` (not manual XML parsing) for VASP output.
4. Prefer input sets over hand-written INCAR files.
5. Use JSON/YAML (`as_dict`) for long-term, version-safe storage.
