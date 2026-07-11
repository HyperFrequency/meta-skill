---
name: pymatgen
version: 0.1.0
description: >-
  Python Materials Genomics (pymatgen) for computational materials science: build and
  manipulate crystal structures and molecules, convert among 100+ structure formats (CIF,
  POSCAR, XYZ), analyze symmetry, space groups and coordination environments, compute phase
  diagrams and thermodynamic stability (energy above hull), read DFT output (VASP, Quantum
  ESPRESSO, Gaussian), analyze band structures and DOS, generate slabs/surfaces/interfaces,
  and query the Materials Project database via mp-api. Use when you work with crystal or
  molecular structures, convert structure files, check phase stability, generate DFT inputs,
  or pull computed materials data. NOT for running the DFT/MD calculation itself (use VASP,
  Quantum ESPRESSO, or LAMMPS directly), general plotting (use `matplotlib` or
  `scientific-visualization`), classical MD trajectory setup for biomolecules, or
  cheminformatics/drug design (use RDKit).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT"
---

# Pymatgen

## Overview

Pymatgen (Python Materials Genomics) is the analysis library that underpins the Materials
Project. It represents elements, compositions, crystal structures, and molecules as objects,
then layers on symmetry analysis, thermodynamics, electronic structure, surfaces, diffraction,
and I/O adapters for most electronic-structure codes. This skill routes you to the right API
for a task and hands deep reference material off to `references/`.

Everything centers on two mutable containers plus their immutable twins:

- `Structure` / `IStructure` — a periodic crystal (a `Lattice` plus a list of `PeriodicSite`s).
- `Molecule` / `IMolecule` — a non-periodic collection of `Site`s.

Read either from a file with automatic format detection, transform it, analyze it, and write it
back out or feed it to a DFT input set.

## When to Use This Skill

Use this skill when you:

- Read, build, edit, or convert crystal-structure or molecule files (CIF, POSCAR/CONTCAR, XYZ, PDB, JSON).
- Determine space group, crystal system, primitive/conventional cell, or coordination number.
- Build a phase diagram and check thermodynamic stability (energy above hull, decomposition products).
- Parse DFT output — band gap, DOS, total energy, magnetization — from `vasprun.xml`, `OUTCAR`, or a Gaussian/QE log.
- Generate surface slabs, Wulff shapes, adsorption sites, or coherent interfaces.
- Enumerate supercells, substitutions, doping, or magnetic orderings via the transformations framework.
- Generate VASP (or QE/Gaussian) inputs with pre-tuned Materials Project input sets.
- Query the Materials Project database programmatically with `mp-api`.

## When NOT to Use This Skill

- **Running the actual DFT/MD engine.** Pymatgen writes inputs and parses outputs; it does not run VASP, Quantum ESPRESSO, or LAMMPS. Launch those separately.
- **General-purpose plotting.** Pymatgen's built-in plotters are fine for quick checks; for publication figures, extract the arrays and use `matplotlib` or `scientific-visualization`.
- **Biomolecular MD / protein modeling / docking.** Use domain tools (OpenMM, GROMACS) — pymatgen's molecule support is thin.
- **Cheminformatics and drug-like small-molecule work** (SMILES, fingerprints, reactions). Use RDKit.
- **Generic atomistic simulation glue** where ASE is the native currency — pymatgen interoperates with ASE via `AseAtomsAdaptor`, but if the whole pipeline is ASE-based, stay there.

## Installation

```bash
uv pip install pymatgen                     # core library (MIT-licensed)
uv pip install mp-api                       # Materials Project database client (separate package)
uv pip install pymatgen-analysis-diffusion  # only for DiffusionAnalyzer (pymatgen.analysis.diffusion)
```

The diffusion analyzer (`pymatgen.analysis.diffusion`) is an add-on package, not part of core —
without it the AIMD/diffusion recipes raise `ModuleNotFoundError`.

`mp-api` requires an API key from https://next-gen.materialsproject.org/. Store it as an
environment variable — never hardcode it:

```bash
export MP_API_KEY="your_key_here"
```

## Quick Start

```python
from pymatgen.core import Structure, Lattice

# Read (format auto-detected from name/contents)
struct = Structure.from_file("POSCAR")

# Or build from scratch
struct = Structure(Lattice.cubic(5.43), ["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]])

print(struct.composition.reduced_formula)   # "Si"
print(struct.get_space_group_info())         # ("Fd-3m", 227)
print(f"{struct.density:.2f} g/cm^3")

struct.to(filename="structure.cif")          # write, format inferred from extension
```

## Capability Map

Each row is a task; open the linked reference for full APIs, parameters, and worked examples.

| Task | Entry point | Reference |
| --- | --- | --- |
| Elements, compositions, lattices, sites, structures, molecules, serialization | `pymatgen.core` | [core-classes.md](references/core-classes.md) |
| Read/write files, convert formats, DFT input sets, code adapters (ASE, phonopy) | `Structure.from_file` / `.to`, `pymatgen.io.*` | [io-and-formats.md](references/io-and-formats.md) |
| Symmetry, coordination, phase/Pourbaix diagrams, band structure, DOS, surfaces, diffraction, elasticity, magnetism, diffusion | `pymatgen.analysis.*`, `pymatgen.symmetry.*`, `pymatgen.electronic_structure.*` | [characterization.md](references/characterization.md) |
| Query Materials Project (structures, entries, properties) | `mp_api.client.MPRester` | [materials-project-api.md](references/materials-project-api.md) |
| Supercells, substitution, doping, enumeration; multi-step recipes | `pymatgen.transformations.*`, `pymatgen.alchemy.*` | [transformations-and-workflows.md](references/transformations-and-workflows.md) |

## Core Workflows at a Glance

**Convert a structure file.** `from_file` reads, `to` writes; the format follows the filename
(or pass `fmt=`):

```python
Structure.from_file("input.cif").to(filename="POSCAR")
```

For batch conversion, loop over paths with `pathlib.Glob` and call `.to()` per file. See
[io-and-formats.md](references/io-and-formats.md) for the format table and per-code parsers.

**Check thermodynamic stability.** Pull computed entries for a chemical system, build the hull,
and measure how far a phase sits above it:

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram

with MPRester() as mpr:
    entries = mpr.get_entries_in_chemsys("Li-Fe-O")
pd = PhaseDiagram(entries)
for entry in entries:
    e_hull = pd.get_e_above_hull(entry)   # eV/atom; 0 == on the hull (stable)
```

Details and Pourbaix/chemical-potential diagrams live in [characterization.md](references/characterization.md).

**Parse a finished DFT run.** `Vasprun` is the workhorse output parser:

```python
from pymatgen.io.vasp import Vasprun

vr = Vasprun("vasprun.xml")
bs = vr.get_band_structure()
gap = bs.get_band_gap()                    # {"energy": float, "direct": bool, "transition": str}
dos = vr.complete_dos                       # element/orbital-projected DOS
energy = vr.final_energy                     # total energy, eV
```

**Set up a DFT calculation.** Materials Project input sets encode converged, community-vetted
INCAR/KPOINTS/POTCAR choices:

```python
from pymatgen.io.vasp.sets import MPRelaxSet
MPRelaxSet(struct, user_incar_settings={"ENCUT": 600}).write_input("./relax")
```

## Units and Conventions

Pymatgen works in atomic/DFT-native units throughout:

- Lengths: angstroms (Å) · Energies: electronvolts (eV) · Angles: degrees
- Magnetic moments: Bohr magnetons (μB) · Time (MD): femtoseconds (fs)
- Elastic moduli: GPa · Surface energy plotting: convert eV/Å² → J/m² by ×16.0218

Convert with `pymatgen.core.units`. Coordinates are fractional for `PeriodicSite` and Cartesian
for `Site` — check which a method expects before passing raw arrays.

## Common Failure Modes

- **`from_file` raises on an ambiguous or extension-less file.** Pass the format explicitly: `Structure.from_file("file.txt", fmt="cif")`.
- **`SpacegroupAnalyzer` reports P1 or a wrong group** on a slightly distorted/noisy structure. Loosen the tolerance: `SpacegroupAnalyzer(struct, symprec=0.1)`. Tighten it if a near-symmetric structure is over-symmetrized.
- **`MPRester` raises about a missing key.** Set `MP_API_KEY`; do not paste keys into code or notebooks.
- **Legacy vs. current MP API.** Use the standalone `mp-api` package (`from mp_api.client import MPRester`) and always wrap it in `with MPRester() as mpr:`. The old `pymatgen.ext.matproj.MPRester` targets a retired endpoint.
- **`CifParser.get_structures()` returns a list**, not one structure — index `[0]` when a CIF holds a single phase.
- **Neighbor searches are slow on large cells.** Reduce to the primitive cell first (`SpacegroupAnalyzer(struct).get_primitive_standard_structure()`) and use a bounded cutoff.
- **Occupancy-disordered structures** (partial site occupancies) fail many analyses that assume ordered sites. Order them first — see the enumeration workflows in [transformations-and-workflows.md](references/transformations-and-workflows.md).

## External Resources

- Docs: https://pymatgen.org/ · Source: https://github.com/materialsproject/pymatgen
- Materials Project: https://next-gen.materialsproject.org/ · Forum: https://matsci.org/
- Example notebooks: https://matgenb.materialsvirtuallab.org/

Targets pymatgen 2024.x+ on Python 3.10+, with `mp-api` for Materials Project access.
