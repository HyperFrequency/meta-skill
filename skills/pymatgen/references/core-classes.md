# Core Classes (`pymatgen.core`)

The object model that every other module builds on. Elements, compositions, lattices, sites,
structures, and molecules are all first-class objects with rich properties and JSON-safe
serialization. Units are atomic throughout — angstroms, electronvolts, degrees.

## Element, Species, Ion

```python
from pymatgen.core import Element, Species, DummySpecies, Ion

fe = Element("Fe")              # by symbol
si = Element.from_Z(14)         # by atomic number
c  = Element.from_name("carbon")

fe2 = Species("Fe", 2)          # Fe(2+) — Element plus an oxidation state
vac = DummySpecies("X")         # placeholder (e.g., a vacancy marker)
ion = Ion.from_formula("Fe2+")  # charged aqueous/ionic species
```

Useful `Element` properties: `atomic_mass`, `atomic_radius`, `X` (Pauling electronegativity),
`common_oxidation_states`, and boolean checks like `is_metal`, `is_halogen`, `is_noble_gas`.

## Composition

A multiset of elements with amounts; the vehicle for all chemistry-level reasoning.

```python
from pymatgen.core import Composition

comp = Composition("Fe2O3")            # or Composition({"Fe": 2, "O": 3})
comp.reduced_formula                    # "Fe2O3"
comp.hill_formula                       # Hill notation (C, H, then alphabetical)
comp.weight                             # molar mass (amu)
comp.num_atoms                          # 5.0
comp.chemical_system                    # "Fe-O" (sorted elements)
comp.get_reduced_formula_and_factor()  # ("Fe2O3", 1)
comp.oxi_state_guesses()               # infer plausible oxidation states
comp.replace({"Fe": "Mn"})             # element substitution -> new Composition
```

## Lattice

The unit-cell geometry underlying every periodic structure.

```python
from pymatgen.core import Lattice

lat = Lattice.cubic(3.84)
lat = Lattice.hexagonal(a=2.95, c=4.68)
lat = Lattice.from_parameters(a=3.84, b=3.84, c=3.84, alpha=90, beta=90, gamma=120)
lat = Lattice([[3.84, 0, 0], [0, 3.84, 0], [0, 0, 3.84]])  # row vectors
```

Properties: `volume`, `abc` (a, b, c tuple), `angles` (α, β, γ), `matrix`,
`reciprocal_lattice`, `is_orthogonal`. Methods include
`get_niggli_reduced_lattice()`, `get_distance_and_image(fc1, fc2)` (minimum-image distance),
and `get_all_distances(fc1, fc2)`.

## Sites

- `Site(species, cartesian_coords)` — a position in a non-periodic system.
- `PeriodicSite(species, frac_coords, lattice)` — a position in a periodic cell.

`PeriodicSite` carries both `coords` (Cartesian) and `frac_coords` (fractional), plus `x`, `y`,
`z`, `species`, `distance(other)`, and `is_periodic_image(other)`. Always confirm whether an API
wants fractional or Cartesian input.

## Structure / IStructure

A `Lattice` plus a list of `PeriodicSite`s. `Structure` is mutable; `IStructure` is immutable and
hashable (use it as a dict key or when a structure must not change).

### Creating

```python
from pymatgen.core import Structure, Lattice

coords = [[0, 0, 0], [0.25, 0.25, 0.25]]
struct = Structure(Lattice.cubic(5.43), ["Si", "Si"], coords)

struct = Structure.from_file("POSCAR")        # auto-detect format
struct = Structure.from_spacegroup(           # symmetry-aware build
    "Fm-3m", Lattice.cubic(3.5), ["Si"], [[0, 0, 0]]
)
```

### File I/O

```python
struct.to(filename="out.cif")                 # extension picks the writer
cif_text = struct.to(fmt="cif")               # return a string instead of writing
```

### Mutating (mutable `Structure` only)

`append(species, coords)`, `insert(i, species, coords)`, `remove_sites(indices)`,
`replace(i, species)`, `apply_strain(strain)`, `perturb(distance)`,
`make_supercell(scaling_matrix)`, `get_primitive_structure()`.

### Analyzing

`get_distance(i, j)`, `get_neighbors(site, r)`, `get_all_neighbors(r)`,
`get_space_group_info()`, `matches(other)`, `interpolate(end_structure, nimages)` (build an
image chain between two endpoints, e.g. for NEB).

### Properties

`lattice`, `species`, `sites`, `num_sites`, `volume`, `density` (g/cm³), `composition`,
`formula`, `distance_matrix`.

## Molecule / IMolecule

A non-periodic set of `Site`s.

```python
from pymatgen.core import Molecule

mol = Molecule(["C", "O"], [[0, 0, 0], [0, 0, 1.08]])
mol = Molecule.from_file("molecule.xyz")

mol.get_covalent_bonds()        # bonds inferred from covalent radii
mol.get_zmatrix()               # Z-matrix representation
mol.get_centered_molecule()     # translate center of mass to origin
mol.center_of_mass              # property
mol.charge, mol.spin_multiplicity
```

## Serialization

Every core object implements `as_dict()` / `from_dict()` for version-tolerant JSON/YAML storage —
prefer this over `pickle`, which breaks across pymatgen versions.

```python
import json
from pymatgen.core import Structure

with open("structure.json", "w") as f:
    json.dump(struct.as_dict(), f)

with open("structure.json") as f:
    struct = Structure.from_dict(json.load(f))
```

## Other core types

- `CovalentBond` — a molecular bond; `length`, `get_bond_order()`.
- `Interface` — a substrate/film heterojunction container.
- `GrainBoundary` — a crystallographic grain boundary.
- `Spectrum` — spectroscopic data with `normalize(mode="max")` and `smear(sigma)`.

## Guidance

1. Use immutable `IStructure` / `IMolecule` when a structure must stay fixed or serve as a key.
2. Persist with `as_dict()`/`from_dict()`, not `pickle`.
3. Stay in atomic units (Å, eV); reach for `pymatgen.core.units` to convert.
4. Prefer `from_file()` for reading — it detects the format for you.
5. Track whether a method expects fractional or Cartesian coordinates.
